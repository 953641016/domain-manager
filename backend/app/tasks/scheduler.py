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
                from app.services.feishu_service import FeishuService
                from app.models.user import User
                from app.config import Config

                feishu = FeishuService()

                # 预查超管，用于无主域名或紧急场景的兜底通知
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
                    if sa_feishu_id and (not notified or expire_days <= 7):
                        try:
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
        from app.services.dns_service import DnsService
        from app.services.audit_service import AuditService
        from app.adapters.registrar_factory import RegistrarFactory

        domain_service = DomainService(self.db)
        dns_service = DnsService(self.db)
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
                        api_key=dns_account.api_key
                    )

                    # 获取远程DNS记录
                    remote_records = adapter.get_records(domain.name)

                    # TODO: 合并本地和远程记录
                    # 目前只记录同步结果
                    synced_count += 1

                except Exception as e:
                    logger.error(f"同步域名 {domain.name} DNS记录失败: {str(e)}")
                    failed_count += 1

            # 记录审计日志
            audit_service.log(
                action="sync_dns",
                resource_type="dns_record",
                after_state={"synced": synced_count, "failed": failed_count},
                status="success" if failed_count == 0 else "failed"
            )

            logger.info(f"DNS记录同步完成: 成功 {synced_count}, 失败 {failed_count}")

            return {"synced": synced_count, "failed": failed_count}

        except Exception as e:
            logger.error(f"同步DNS记录失败: {str(e)}")
            audit_service.log(
                action="sync_dns",
                resource_type="dns_record",
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
