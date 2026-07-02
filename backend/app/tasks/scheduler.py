"""
定时任务调度器
处理域名到期检查、定时同步等任务
"""
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器类"""

    def __init__(self, db=None):
        self.db = db
        self._running = False

    def start(self):
        """启动调度器"""
        self._running = True
        logger.info("任务调度器已启动")

    def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("任务调度器已停止")

    @staticmethod
    def _normalize_dns_host(host: Optional[str]) -> str:
        if not host or host == "":
            return "@"
        return str(host).strip()

    @staticmethod
    def _normalize_remote_dns_record(record: dict) -> Optional[dict]:
        record_type = (record.get("type") or record.get("record_type") or "").upper()
        host = TaskScheduler._normalize_dns_host(record.get("host") or record.get("name"))
        value = record.get("value") or record.get("content")

        if not record_type or value in (None, ""):
            return None

        ttl = record.get("ttl", 300)
        try:
            ttl = int(ttl)
        except (TypeError, ValueError):
            ttl = 300

        priority = record.get("priority")
        if priority in ("", None):
            priority = None
        else:
            try:
                priority = int(priority)
            except (TypeError, ValueError):
                priority = None

        remote_status = record.get("status")
        status_value = "active" if remote_status in (None, "", "ENABLE", "active") else str(remote_status)

        return {
            "external_id": str(record.get("id")) if record.get("id") not in (None, "") else None,
            "record_type": record_type,
            "host": host,
            "value": str(value),
            "ttl": ttl,
            "priority": priority,
            "status": status_value,
        }

    @staticmethod
    def _natural_dns_key(record_type: str, host: str, value: str, priority: Optional[int]):
        return (record_type, host, value, priority)

    def _merge_remote_dns_records(self, domain, remote_records: list[dict]) -> dict:
        from app.models.dns import DnsRecord

        now = datetime.now()
        local_records = self.db.query(DnsRecord).filter(
            DnsRecord.domain_id == domain.id,
            DnsRecord.status != "deleted",
        ).all()
        local_by_external = {
            record.external_id: record
            for record in local_records
            if record.external_id
        }
        local_by_natural = {
            self._natural_dns_key(record.record_type, record.host, record.value, record.priority): record
            for record in local_records
        }

        created_count = 0
        updated_count = 0
        unchanged_count = 0
        deleted_count = 0
        seen_local_ids = set()

        for raw_record in remote_records or []:
            remote = self._normalize_remote_dns_record(raw_record)
            if not remote:
                continue

            natural_key = self._natural_dns_key(
                remote["record_type"],
                remote["host"],
                remote["value"],
                remote["priority"],
            )
            local_record = (
                local_by_external.get(remote["external_id"])
                if remote["external_id"]
                else None
            ) or local_by_natural.get(natural_key)

            if not local_record:
                local_record = DnsRecord(
                    domain_id=domain.id,
                    record_type=remote["record_type"],
                    host=remote["host"],
                    value=remote["value"],
                    ttl=remote["ttl"],
                    priority=remote["priority"],
                    status=remote["status"],
                    sync_status="synced",
                    external_id=remote["external_id"],
                    last_synced_at=now,
                    remark="由远程DNS同步创建",
                )
                self.db.add(local_record)
                self.db.flush()
                if local_record.external_id:
                    local_by_external[local_record.external_id] = local_record
                local_by_natural[natural_key] = local_record
                created_count += 1
            else:
                changed = False
                for field in ["record_type", "host", "value", "ttl", "priority", "status", "external_id"]:
                    if getattr(local_record, field) != remote[field]:
                        setattr(local_record, field, remote[field])
                        changed = True
                if local_record.sync_status != "synced":
                    local_record.sync_status = "synced"
                    changed = True
                local_record.last_synced_at = now
                if changed:
                    updated_count += 1
                else:
                    unchanged_count += 1

            seen_local_ids.add(local_record.id)

        for local_record in local_records:
            if local_record.id in seen_local_ids:
                continue
            if not local_record.external_id and local_record.sync_status != "synced":
                continue
            local_record.status = "deleted"
            local_record.sync_status = "synced"
            local_record.last_synced_at = now
            deleted_count += 1

        self.db.commit()
        return {
            "created": created_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
            "deleted": deleted_count,
            "processed": created_count + updated_count + unchanged_count + deleted_count,
        }

    def check_expiring_domains(self, days: int = 30):
        """
        检查即将到期的域名

        Args:
            days: 到期天数阈值
        """
        if not self.db:
            logger.error("数据库未初始化")
            return

        from app.services.domain_service import DomainService
        from app.services.audit_service import AuditService

        service = DomainService(self.db)
        audit_service = AuditService(self.db)

        try:
            expiring_domains = service.get_expiring_domains(days)

            if expiring_domains:
                logger.info(f"发现 {len(expiring_domains)} 个即将到期的域名")

                # 记录审计日志
                audit_service.log(
                    action="check_expiring",
                    resource_type="domain",
                    after_state={"expiring_count": len(expiring_domains), "days": days},
                    status="success"
                )

                # 发送飞书到期提醒
                from app.services.feishu_app_service import get_feishu_service_for_user
                from app.models.user import User
                from app.config import Config

                # 预查超管，用于无主域名或紧急场景的兜底通知
                sa = None
                sa_feishu_id = None
                sa_feishu_type = "user_id"
                if Config.SUPER_ADMIN_FEISHU_USER_ID:
                    sa = self.db.query(User).filter(
                        User.feishu_user_id == Config.SUPER_ADMIN_FEISHU_USER_ID
                    ).first()
                    if sa:
                        sa_feishu_id = getattr(sa, "feishu_open_id", None) or getattr(sa, "feishu_user_id", None)
                        sa_feishu_type = "open_id" if getattr(sa, "feishu_open_id", None) else "user_id"

                for domain in expiring_domains:
                    expire_dt = domain.expiration_date
                    # 兼容有无时区的 datetime
                    expire_days = max(0, (expire_dt.replace(tzinfo=None) - datetime.now()).days)
                    exp_str = expire_dt.strftime("%Y-%m-%d") if expire_dt else ""
                    logger.info(f"域名 {domain.name} 将在 {domain.expiration_date} 到期（剩余 {expire_days} 天）")

                    notified = False
                    # 优先通知域名归属专员
                    if domain.owner_id:
                        owner = self.db.query(User).filter(User.id == domain.owner_id).first()
                        if owner:
                            receive_id = getattr(owner, "feishu_open_id", None) or getattr(owner, "feishu_user_id", None)
                            if receive_id:
                                receive_type = "open_id" if getattr(owner, "feishu_open_id", None) else "user_id"
                                try:
                                    feishu = get_feishu_service_for_user(self.db, owner)
                                    feishu.send_domain_alert_card(
                                        receive_id=receive_id,
                                        domain_name=domain.name,
                                        expire_days=expire_days,
                                        expiration_date=exp_str,
                                        registrar=domain.registrar_code or "",
                                        receive_id_type=receive_type,
                                    )
                                    notified = True
                                    logger.info(f"已向专员 {owner.name} 发送域名 {domain.name} 到期提醒")
                                except Exception as notify_err:
                                    logger.warning(f"向专员发送到期提醒失败 ({domain.name}): {notify_err}")

                    # 兜底：无主域名或专员无飞书ID时通知超管；紧急（≤7天）时也同步通知超管
                    if sa and sa_feishu_id and (not notified or expire_days <= 7):
                        try:
                            feishu = get_feishu_service_for_user(self.db, sa)
                            feishu.send_domain_alert_card(
                                receive_id=sa_feishu_id,
                                domain_name=domain.name,
                                expire_days=expire_days,
                                expiration_date=exp_str,
                                registrar=domain.registrar_code or "",
                                receive_id_type=sa_feishu_type,
                            )
                        except Exception as notify_err:
                            logger.warning(f"向超管发送到期提醒失败 ({domain.name}): {notify_err}")

            return expiring_domains

        except Exception as e:
            logger.error(f"检查到期域名失败: {str(e)}")
            audit_service.log(
                action="check_expiring",
                resource_type="domain",
                status="failed",
                error_message=str(e)
            )
            return []

    def sync_domain_status(self):
        """
        同步域名状态

        从注册商API获取最新的域名状态
        """
        if not self.db:
            logger.error("数据库未初始化")
            return

        from app.services.domain_service import DomainService
        from app.services.audit_service import AuditService
        from app.adapters.registrar_factory import RegistrarFactory

        service = DomainService(self.db)
        audit_service = AuditService(self.db)

        try:
            # 获取所有有注册商配置的域名
            domains = service.get_domains(limit=1000)

            synced_count = 0
            failed_count = 0
            created_count = 0
            updated_count = 0
            unchanged_count = 0
            deleted_count = 0

            for domain in domains:
                if not domain.registrar_code or not domain.reg_account_id:
                    continue

                try:
                    # 获取注册账号信息
                    reg_account = service.get_reg_account(domain.reg_account_id)
                    if not reg_account or not reg_account.api_key:
                        continue

                    # 创建适配器
                    adapter = RegistrarFactory.create_registrar(
                        code=domain.registrar_code,
                        api_key=reg_account.api_key,
                        api_secret=reg_account.api_secret
                    )

                    # 获取域名信息
                    domain_info = adapter.get_domain_info(domain.name)
                    if domain_info:
                        # 更新域名状态
                        domain.status = domain_info.get("status", domain.status)
                        if domain_info.get("expiration_date"):
                            domain.expiration_date = domain_info["expiration_date"]
                        if domain_info.get("nameservers"):
                            domain.nameservers = domain_info["nameservers"]
                        
                        service.db.commit()
                        synced_count += 1

                except Exception as e:
                    logger.error(f"同步域名 {domain.name} 失败: {str(e)}")
                    failed_count += 1

            # 记录审计日志
            audit_service.log(
                action="sync_domains",
                resource_type="domain",
                resource_name=f"域名状态同步: 成功 {synced_count} / 失败 {failed_count}",
                after_state={"synced": synced_count, "failed": failed_count},
                status="success" if failed_count == 0 else "failed"
            )

            logger.info(f"域名同步完成: 成功 {synced_count}, 失败 {failed_count}")

            return {"synced": synced_count, "failed": failed_count}

        except Exception as e:
            logger.error(f"同步域名状态失败: {str(e)}")
            audit_service.log(
                action="sync_domains",
                resource_type="domain",
                resource_name="域名状态同步: 成功 0 / 失败 1",
                status="failed",
                error_message=str(e)
            )
            return {"synced": 0, "failed": 0}

    def sync_dns_records(self):
        """
        同步DNS记录

        从DNS服务商同步记录到本地
        """
        if not self.db:
            logger.error("数据库未初始化")
            return

        from app.services.domain_service import DomainService
        from app.services.audit_service import AuditService
        from app.adapters.registrar_factory import RegistrarFactory

        domain_service = DomainService(self.db)
        audit_service = AuditService(self.db)

        try:
            # 获取所有有DNS配置的域名
            domains = domain_service.get_domains(limit=1000)

            synced_count = 0
            failed_count = 0

            for domain in domains:
                if not domain.dns_provider_code or not domain.dns_account_id:
                    continue

                try:
                    # 获取DNS账号信息
                    dns_account = domain_service.get_dns_account(domain.dns_account_id)
                    if not dns_account or not dns_account.api_key:
                        continue

                    # 创建适配器
                    adapter = RegistrarFactory.create_dns_provider(
                        code=domain.dns_provider_code,
                        api_key=dns_account.api_key,
                        api_secret=dns_account.api_secret,
                    )

                    # 获取远程DNS记录
                    remote_records = adapter.get_records(domain.name)

                    merge_result = self._merge_remote_dns_records(domain, remote_records)
                    synced_count += merge_result["processed"]
                    created_count += merge_result["created"]
                    updated_count += merge_result["updated"]
                    unchanged_count += merge_result["unchanged"]
                    deleted_count += merge_result["deleted"]

                except Exception as e:
                    logger.error(f"同步域名 {domain.name} DNS记录失败: {str(e)}")
                    failed_count += 1

            # 记录审计日志
            audit_service.log(
                action="sync_dns",
                resource_type="dns_record",
                resource_name=(
                    f"DNS记录同步: 成功 {synced_count} / 失败 {failed_count}"
                    f"（新增 {created_count} / 更新 {updated_count} / 删除 {deleted_count}）"
                ),
                after_state={
                    "synced": synced_count,
                    "failed": failed_count,
                    "created": created_count,
                    "updated": updated_count,
                    "unchanged": unchanged_count,
                    "deleted": deleted_count,
                },
                status="success" if failed_count == 0 else "failed"
            )

            logger.info(f"DNS记录同步完成: 成功 {synced_count}, 失败 {failed_count}")

            return {"synced": synced_count, "failed": failed_count}

        except Exception as e:
            logger.error(f"同步DNS记录失败: {str(e)}")
            audit_service.log(
                action="sync_dns",
                resource_type="dns_record",
                resource_name="DNS记录同步: 成功 0 / 失败 1",
                status="failed",
                error_message=str(e)
            )
            return {"synced": 0, "failed": 0}

    def cleanup_audit_logs(self, days: int = 90):
        """
        清理旧的审计日志

        Args:
            days: 保留天数
        """
        if not self.db:
            logger.error("数据库未初始化")
            return

        from app.services.audit_service import AuditService

        service = AuditService(self.db)

        try:
            deleted = service.cleanup_old_logs(days)
            logger.info(f"已清理 {deleted} 条审计日志")
            return deleted

        except Exception as e:
            logger.error(f"清理审计日志失败: {str(e)}")
            return 0


# 全局调度器实例
scheduler = TaskScheduler()


def run_scheduled_tasks(db):
    """
    运行所有定时任务

    可以通过cron或APScheduler调用此函数
    """
    scheduler.db = db

    logger.info("开始执行定时任务...")

    # 1. 检查即将到期的域名（30天内）
    scheduler.check_expiring_domains(30)

    # 2. 同步域名状态
    scheduler.sync_domain_status()

    # 3. 同步DNS记录
    scheduler.sync_dns_records()

    # 4. 检查和自动续期SSL证书
    check_ssl_certificates()

    logger.info("定时任务执行完成")


def check_ssl_certificates():
    """
    检查SSL证书并自动续期
    """
    from app.services.ssl_service import ssl_service

    try:
        logger.info("开始检查SSL证书...")

        # 检查即将到期的证书（30天警告，7天紧急）
        check_result = ssl_service.check_and_alert_expiring_certificates(30, 7)

        if check_result["warning_certs"]:
            logger.warning(f"发现 {len(check_result['warning_certs'])} 个即将到期的SSL证书")
            for cert in check_result["warning_certs"]:
                logger.warning(f"  - {cert['domain']}: 剩余 {cert['days_remaining']} 天")

        if check_result["critical_certs"]:
            logger.critical(f"发现 {len(check_result['critical_certs'])} 个紧急到期的SSL证书")
            for cert in check_result["critical_certs"]:
                logger.critical(f"  - {cert['domain']}: 剩余 {cert['days_remaining']} 天")

        # 自动续期剩余3天内的证书
        if check_result["critical_certs"] or check_result["warning_certs"]:
            renew_result = ssl_service.auto_renew_expiring_certificates(3)

            if renew_result["renewed"] > 0:
                logger.info(f"成功续期 {renew_result['renewed']} 个SSL证书")

            if renew_result["failed"] > 0:
                logger.error(f"续期失败 {renew_result['failed']} 个SSL证书")

        return check_result

    except Exception as e:
        logger.error(f"检查SSL证书失败: {str(e)}")
        return None
