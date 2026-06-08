"""
申请执行服务
打通「审批通过 → 自动执行（注册/DNS配置）→ 差异化通知」主线。

设计原则：
- 防御式：任何一步出错都不会抛到调用方，统一落到 failed 状态并通知。
- 差异化通知：业务同事只收到简化结果；域名专员/审批人收到完整信息（含失败原因）。
"""
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.request import Request
from app.models.domain import Domain
from app.services.domain_service import DomainService
from app.services.audit_service import AuditService
from app.services.feishu_service import FeishuService
from app.adapters.registrar_factory import RegistrarFactory

logger = logging.getLogger(__name__)

TYPE_LABELS = {
    "domain_register": "域名注册",
    "dns_record": "DNS解析",
}


class ExecutionService:
    """申请执行与通知服务"""

    def __init__(self, db: Session):
        self.db = db
        self.domain_service = DomainService(db)
        self.audit_service = AuditService(db)
        self.feishu = FeishuService()

    # ==================== 对外主入口 ====================

    def execute_and_notify(self, request: Request) -> Dict[str, Any]:
        """
        执行已审批通过的申请，并发送差异化通知。
        返回执行结果字典。
        """
        try:
            if request.type == "dns_record":
                result = self._execute_dns(request)
            elif request.type == "domain_register":
                result = self._execute_register(request)
            else:
                result = {"success": False, "error": f"未知的申请类型: {request.type}"}
        except Exception as e:  # 兜底，绝不让执行异常冒泡到审批接口
            logger.exception("执行申请异常")
            result = {"success": False, "error": f"执行异常: {str(e)}"}

        # 更新申请状态
        success = bool(result.get("success"))
        error_message = None if success else self._summarize_failure(result)
        if error_message and not result.get("error"):
            result["error"] = error_message
        is_async_register = (
            request.type == "domain_register"
            and success
            and bool(result.get("registration_pending"))
        )
        request.status = "approved" if is_async_register else ("completed" if success else "failed")
        request.execution_result = result
        request.error_message = error_message
        try:
            self.db.commit()
            self.db.refresh(request)
        except Exception:
            self.db.rollback()
            logger.exception("更新申请执行结果失败")

        # 审计 + 通知（均不影响主流程）
        self._safe_audit(request, result)
        self._notify(request, result)
        if is_async_register:
            self._start_registration_finalizer(request.id, result)
        return result

    # ==================== DNS 解析执行 ====================

    def _execute_dns(self, request: Request) -> Dict[str, Any]:
        account = (
            self.domain_service.get_dns_account_decrypted(request.selected_dns_account_id)
            if request.selected_dns_account_id else None
        )
        provider_code = request.selected_dns_provider_code or (account.provider_code if account else None)
        if not account or not provider_code:
            return {"success": False, "error": "未配置DNS解析账号或解析商", "records": []}

        try:
            adapter = RegistrarFactory.create_dns_provider(
                provider_code, account.api_key, account.api_secret
            )
        except Exception as e:
            return {"success": False, "error": f"创建解析适配器失败: {str(e)}", "records": []}

        records = self._normalize_records(request.request_data)
        if not records:
            return {"success": False, "error": "申请数据中未找到有效的解析记录", "records": []}

        # 一次性拉取该域名现有记录，用于幂等判断
        try:
            existing_records = adapter.get_records(request.domain_name)
        except Exception:
            existing_records = []

        def _find_existing(host: str, rtype: str):
            for er in existing_records:
                er_host = str(er.get("host") or er.get("name") or er.get("hostname") or "").lower().rstrip(".")
                er_type = str(er.get("type") or er.get("record_type") or "").upper()
                if er_host == host.lower() and er_type == rtype.upper():
                    return er
            return None

        results: List[Dict[str, Any]] = []
        supported_types = {"A", "AAAA", "CNAME", "MX", "TXT", "NS", "SRV"}
        redirect_types = {"REDIRECT_301": 301, "REDIRECT_302": 302}
        for rec in records:
            rtype = str(rec.get("record_type") or rec.get("type") or "").upper()
            host  = str(rec.get("host") or rec.get("name") or rec.get("hostname") or "@")
            value = str(rec.get("value") or rec.get("content") or rec.get("target") or "")
            ttl      = self._to_int(rec.get("ttl"), 300)
            priority = self._to_int(rec.get("priority"), None)

            label = {"domain": request.domain_name, "type": rtype, "host": host, "value": value}

            if not rtype or not value:
                results.append({"record": label, "status": "failed", "message": "记录类型或记录值缺失"})
                continue
            if rtype in redirect_types:
                if provider_code != "cloudflare" or not hasattr(adapter, "create_redirect_rule"):
                    results.append({"record": label, "status": "failed", "message": f"{provider_code} 暂不支持自动创建重定向规则"})
                    continue
                try:
                    r = adapter.create_redirect_rule(
                        request.domain_name,
                        host,
                        value,
                        status_code=redirect_types[rtype],
                    )
                except Exception as e:
                    r = {"success": False, "message": f"创建重定向规则异常: {str(e)}"}
                results.append({
                    "record": label,
                    "operation": "redirect_rule",
                    "status": "success" if r.get("success") else "failed",
                    "message": r.get("message", ""),
                    "record_id": r.get("record_id"),
                })
                continue
            if rtype not in supported_types:
                results.append({"record": label, "status": "failed", "message": f"暂不支持的 DNS 记录类型: {rtype}"})
                continue

            existing = _find_existing(host, rtype)

            if existing:
                ex_value = str(existing.get("value") or existing.get("content") or existing.get("target") or "")
                if ex_value == value:
                    results.append({"record": label, "status": "skipped", "message": "记录已存在且值一致，跳过"})
                    continue
                # 值不同 → 修改
                record_id = str(existing.get("record_id") or existing.get("id") or "")
                try:
                    r = adapter.update_record(request.domain_name, record_id, rtype, host, value, ttl, priority)
                except Exception as e:
                    r = {"success": False, "message": f"修改记录异常: {str(e)}"}
                results.append({
                    "record": label, "operation": "update",
                    "status": "success" if r.get("success") else "failed",
                    "message": r.get("message", ""),
                })
            else:
                # 不存在 → 新增
                try:
                    r = adapter.create_record(request.domain_name, rtype, host, value, ttl, priority)
                except Exception as e:
                    r = {"success": False, "message": f"新增记录异常: {str(e)}"}
                results.append({
                    "record": label, "operation": "create",
                    "status": "success" if r.get("success") else "failed",
                    "message": r.get("message", ""),
                    "record_id": r.get("record_id"),
                })

        ok = sum(1 for x in results if x["status"] in ("success", "skipped"))
        total = len(results)
        success = ok == total and total > 0
        if success:
            self._upsert_domain_dns_mapping(request, account, provider_code)
        failure_message = None if success else self._summarize_failure({"records": results})
        return {
            "success": success,
            "total": total,
            "success_count": ok,
            "failed_count": total - ok,
            "records": results,
            "dns_account_name": account.name,
            "provider_code": provider_code,
            **({"error": failure_message} if failure_message else {}),
        }

    def _upsert_domain_dns_mapping(self, request: Request, account, provider_code: str) -> None:
        """DNS 执行成功后回填本地域名 → DNS账号映射，供后台审批自动匹配。"""
        try:
            from app.models.domain import Domain

            domain = self.db.query(Domain).filter(Domain.name == request.domain_name).first()
            if not domain:
                domain = Domain(
                    name=request.domain_name,
                    status="active",
                    owner_id=getattr(account, "owner_id", None) or request.requester_id,
                )
                self.db.add(domain)
            domain.dns_provider_code = provider_code
            domain.dns_account_id = account.id
            if not domain.owner_id:
                domain.owner_id = getattr(account, "owner_id", None) or request.requester_id
            self.db.commit()
        except Exception:
            import logging
            self.db.rollback()
            logging.getLogger(__name__).warning("回填域名 DNS 账号映射失败: %s", request.domain_name)

    # ==================== 域名注册执行 ====================

    def _execute_register(self, request: Request) -> Dict[str, Any]:
        account = (
            self.domain_service.get_reg_account_decrypted(request.selected_reg_account_id)
            if request.selected_reg_account_id else None
        )
        registrar_code = request.selected_registrar_code or (account.registrar_code if account else None)
        if not account or not registrar_code:
            return {"success": False, "error": "未配置注册账号或注册商"}

        try:
            adapter = RegistrarFactory.create_registrar(
                registrar_code,
                account.api_key,
                account.api_secret,
                account_id=account.api_secret if registrar_code == "cloudflare" else None,
            )
        except Exception as e:
            return {"success": False, "error": f"创建注册适配器失败: {str(e)}"}

        domain = request.domain_name

        # 1. 注册前再次校验可用性
        avail = {}
        try:
            avail = adapter.check_domain_availability(domain) or {}
        except Exception as e:
            logger.warning("注册前可用性检查异常: %s", e)
        if not avail.get("check_successful"):
            return {
                "success": False,
                "error": f"注册前可用性检查失败: {avail.get('message') or '检查失败'}",
                "reg_account_name": account.name,
            }
        if avail.get("check_successful") and avail.get("available") is False:
            reason = avail.get("message") or "不可注册"
            return {
                "success": False,
                "error": f"域名当前不可注册: {reason}",
                "price": avail.get("price"),
                "currency": avail.get("currency"),
                "reg_account_name": account.name,
            }

        # 2. 执行注册
        registrant = {}
        register_years = 1
        if isinstance(request.request_data, dict):
            registrant = request.request_data.get("registrant") or request.request_data.get("registrant_info") or {}
            try:
                register_years = int(request.request_data.get("register_years") or 1)
            except (TypeError, ValueError):
                register_years = 1
        try:
            reg = adapter.register_domain(domain, registrant, nameservers=None, years=register_years)
        except Exception as e:
            return {"success": False, "error": f"调用注册API异常: {str(e)}"}

        if not reg.get("success"):
            return {
                "success": False,
                "error": reg.get("message", "注册失败"),
                "price": avail.get("price"),
                "currency": avail.get("currency"),
                "reg_account_name": account.name,
            }

        # 3. 落库域名记录（失败不影响注册成功结论）
        try:
            self._create_domain_record(request, account, reg)
        except Exception:
            logger.exception("注册成功但写入域名表失败")

        return {
            "success": True,
            "domain": domain,
            "order_id": reg.get("order_id"),
            "registration_date": reg.get("registration_date"),
            "expiration_date": reg.get("expiration_date"),
            "registration_pending": bool(reg.get("registration_pending")),
            "registration_unknown": bool(reg.get("registration_unknown")),
            "message": reg.get("message"),
            "workflow_state": reg.get("workflow_state"),
            "price": avail.get("price"),
            "currency": avail.get("currency"),
            "registrar_code": registrar_code,
            "reg_account_name": account.name,
        }

    def _create_domain_record(self, request: Request, account, reg: Dict[str, Any]) -> None:
        existing = self.db.query(Domain).filter(Domain.name == request.domain_name).first()
        domain_status = "pending" if reg.get("registration_pending") else "active"
        if existing:
            existing.registrar_code = account.registrar_code
            existing.reg_account_id = account.id
            existing.status = domain_status
            existing.registration_date = self._parse_date(reg.get("registration_date")) or existing.registration_date
            existing.expiration_date = self._parse_date(reg.get("expiration_date")) or existing.expiration_date
            existing.owner_id = account.owner_id or existing.owner_id
        else:
            self.db.add(Domain(
                name=request.domain_name,
                registrar_code=account.registrar_code,
                reg_account_id=account.id,
                dns_provider_code=request.selected_dns_provider_code,
                dns_account_id=request.selected_dns_account_id,
                status=domain_status,
                registration_date=self._parse_date(reg.get("registration_date")),
                expiration_date=self._parse_date(reg.get("expiration_date")),
                owner_id=account.owner_id,
            ))
        self.db.commit()

    def _start_registration_finalizer(self, request_id: str, initial_result: Dict[str, Any]) -> None:
        """后台轮询注册最终结果，避免飞书卡片交互或审批执行线程长时间等待。"""
        worker = threading.Thread(
            target=self._finalize_registration_async,
            args=(request_id, dict(initial_result or {})),
            daemon=True,
        )
        worker.start()

    @classmethod
    def _finalize_registration_async(cls, request_id: str, initial_result: Dict[str, Any]) -> None:
        db = SessionLocal()
        service = cls(db)
        try:
            request = db.query(Request).filter(Request.id == request_id).first()
            if not request or request.type != "domain_register":
                return
            if request.status not in ("approved", "completed"):
                return

            account = (
                service.domain_service.get_reg_account_decrypted(request.selected_reg_account_id)
                if request.selected_reg_account_id else None
            )
            registrar_code = request.selected_registrar_code or (account.registrar_code if account else None)
            if not account or not registrar_code:
                final_result = {
                    **initial_result,
                    "success": False,
                    "registration_pending": False,
                    "error": "未配置注册账号或注册商，无法查询最终注册结果",
                }
            else:
                try:
                    adapter = RegistrarFactory.create_registrar(
                        registrar_code,
                        account.api_key,
                        account.api_secret,
                        account_id=account.api_secret if registrar_code == "cloudflare" else None,
                    )
                    if hasattr(adapter, "wait_for_registration_result"):
                        final_reg = adapter.wait_for_registration_result(
                            request.domain_name,
                            initial_result,
                            timeout=600,
                        )
                    else:
                        final_reg = {"success": False, "message": f"{registrar_code} 不支持异步注册结果查询"}
                except Exception as e:
                    final_reg = {"success": False, "message": f"查询最终注册结果异常: {str(e)}"}

                final_result = service._merge_register_final_result(request, account, registrar_code, initial_result, final_reg)

            final_success = bool(final_result.get("success")) and not final_result.get("registration_pending")
            if final_success:
                request.status = "completed"
                request.error_message = None
            elif final_result.get("registration_pending"):
                request.status = "approved"
                request.error_message = None
            else:
                request.status = "failed"
                request.error_message = service._summarize_failure(final_result)
                if request.error_message and not final_result.get("error"):
                    final_result["error"] = request.error_message

            request.execution_result = final_result
            db.commit()
            db.refresh(request)
            service._safe_audit(request, final_result)
            service._notify(request, final_result)
        except Exception:
            db.rollback()
            logger.exception("后台查询域名注册最终结果失败: %s", request_id)
        finally:
            db.close()

    def _merge_register_final_result(
        self,
        request: Request,
        account,
        registrar_code: str,
        initial_result: Dict[str, Any],
        final_reg: Dict[str, Any],
    ) -> Dict[str, Any]:
        final_result = {
            **(initial_result or {}),
            "success": bool(final_reg.get("success")),
            "domain": request.domain_name,
            "order_id": final_reg.get("order_id") or (initial_result or {}).get("order_id"),
            "registration_date": final_reg.get("registration_date") or (initial_result or {}).get("registration_date"),
            "expiration_date": final_reg.get("expiration_date") or (initial_result or {}).get("expiration_date"),
            "registration_pending": bool(final_reg.get("registration_pending")),
            "registration_unknown": bool(final_reg.get("registration_unknown")),
            "message": final_reg.get("message") or (initial_result or {}).get("message"),
            "workflow_state": final_reg.get("workflow_state") or (initial_result or {}).get("workflow_state"),
            "registrar_code": registrar_code,
            "reg_account_name": account.name if account else (initial_result or {}).get("reg_account_name"),
        }
        if not final_result["success"]:
            final_result["error"] = final_reg.get("message") or final_reg.get("error") or "注册失败"

        if final_result["success"] and not final_result["registration_pending"]:
            try:
                self._create_domain_record(request, account, final_result)
            except Exception:
                logger.exception("注册最终成功但写入域名表失败")

        return final_result

    # ==================== 差异化通知 ====================

    def _notify(self, request: Request, result: Dict[str, Any]) -> None:
        type_label = TYPE_LABELS.get(request.type, request.type)
        success = bool(result.get("success"))
        requester = request.requester
        approver = request.approver
        processed_time = self._format_notify_time(getattr(request, "approved_at", None))

        # 业务同事：简化通知（不含技术细节）
        if requester:
            if success:
                is_register_pending = request.type == "domain_register" and result.get("registration_pending")
                title = (
                    f"⏳ 您的{type_label}申请已提交"
                    if is_register_pending else
                    f"✅ 您的{type_label}申请已完成"
                )
                color = "orange" if is_register_pending else "green"
                body = (
                    f"**域名**：{request.domain_name}\n"
                    f"**处理时间**：{processed_time}"
                )
                if is_register_pending and result.get("message"):
                    body += f"\n**状态**：{result['message']}"
            else:
                failure_reason = self._summarize_failure(result)
                title = f"❌ 您的{type_label}申请未能完成"
                color = "red"
                body = (
                    f"**域名**：{request.domain_name}\n"
                    f"**处理时间**：{processed_time}\n"
                    f"**失败原因**：{failure_reason}\n"
                    "请联系域名专员了解详情并重新提交。"
                )
            self._send_card(requester, title, color, body)

        # 域名专员/审批人：完整信息（含失败原因）
        if approver and (not requester or approver.id != requester.id):
            title, color, detail = self._build_specialist_card(request, result, type_label, success)
            self._send_card(approver, title, color, detail)

    def _build_specialist_card(self, request: Request, result: Dict[str, Any],
                               type_label: str, success: bool) -> tuple[str, str, str]:
        # DNS 可能部分成功，单独标注
        if request.type != "domain_register":
            total = result.get("total")
            sc = result.get("success_count", 0)
            is_partial = total is not None and sc is not None and 0 < sc < total
        else:
            is_partial = False
        if is_partial:
            icon, label, color = "⚠️", "部分成功", "orange"
        elif request.type == "domain_register" and success and result.get("registration_pending"):
            icon, label, color = "⏳", "已提交", "orange"
        elif success:
            icon, label, color = "✅", "成功", "green"
        else:
            icon, label, color = "❌", "失败", "red"
        head = f"{icon} {type_label}{label}"
        lines = [f"**域名**：{request.domain_name}",
                 f"**申请人**：{request.requester_name}",
                 f"**处理时间**：{self._format_notify_time(getattr(request, 'approved_at', None))}"]

        if request.type == "domain_register":
            if result.get("reg_account_name"):
                lines.append(f"**注册账号**：{result['reg_account_name']}")
            if result.get("price") is not None:
                lines.append(f"**价格**：{result.get('price')} {result.get('currency', '')}".strip())
            if success:
                if result.get("message"):
                    lines.append(f"**状态**：{result['message']}")
                if result.get("workflow_state"):
                    lines.append(f"**工作流状态**：{result['workflow_state']}")
                if result.get("expiration_date"):
                    lines.append(f"**到期时间**：{result['expiration_date']}")
                if result.get("order_id"):
                    lines.append(f"**订单号**：{result['order_id']}")
            else:
                lines.append(f"**失败原因**：{self._summarize_failure(result)}")
        else:  # dns_record
            if result.get("dns_account_name"):
                lines.append(f"**解析账号**：{result['dns_account_name']}")
            total = result.get("total")
            if total is not None:
                lines.append(f"**记录数**：成功 {result.get('success_count', 0)} / 共 {total}")
            for item in (result.get("records") or []):
                rec = item.get("record", {})
                flag = "✓" if item.get("status") == "success" else "✗"
                line = f"  {flag} {rec.get('type','')} {rec.get('host','')} → {rec.get('value','')}"
                if item.get("status") != "success" and item.get("message"):
                    line += f"（{item['message']}）"
                lines.append(line)
            if not success and result.get("error"):
                lines.append(f"**失败原因**：{result['error']}")

        return head, color, "\n".join(lines)

    def _send_card(self, user, title: str, color: str, content: str) -> None:
        receive_id = None
        receive_type = "open_id"
        if getattr(user, "feishu_open_id", None):
            receive_id, receive_type = user.feishu_open_id, "open_id"
        elif getattr(user, "feishu_user_id", None):
            receive_id, receive_type = user.feishu_user_id, "user_id"
        if not receive_id:
            logger.info("用户 %s 无飞书ID，跳过通知", getattr(user, "name", "?"))
            return
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color,
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}},
            ],
        }
        try:
            self.feishu.send_card_message(receive_id, card, receive_type)
        except Exception:
            logger.exception("发送飞书卡片通知失败")

    def _send(self, user, content: str) -> None:
        """向用户发送飞书文本消息，失败不影响主流程"""
        receive_id = None
        receive_type = "open_id"
        if getattr(user, "feishu_open_id", None):
            receive_id, receive_type = user.feishu_open_id, "open_id"
        elif getattr(user, "feishu_user_id", None):
            receive_id, receive_type = user.feishu_user_id, "user_id"
        if not receive_id:
            logger.info("用户 %s 无飞书ID，跳过通知", getattr(user, "name", "?"))
            return
        try:
            self.feishu.send_text_message(receive_id, content, receive_type)
        except Exception:
            logger.exception("发送飞书通知失败")

    @staticmethod
    def _format_notify_time(value) -> str:
        if not value:
            value = datetime.now(timezone.utc)
        try:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            value = value.astimezone(timezone(timedelta(hours=8)))
            return value.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(value)

    # ==================== 工具方法 ====================

    def _safe_audit(self, request: Request, result: Dict[str, Any]) -> None:
        try:
            self.audit_service.log(
                action=f"execute_{request.type}",
                resource_type="request",
                resource_id=request.id,
                resource_name=request.domain_name,
                user_id=request.approver_id,
                user_name=request.approver_name,
                after_state=result if isinstance(result, dict) else None,
                status="success" if result.get("success") else "failed",
                error_message=None if result.get("success") else self._summarize_failure(result),
            )
        except Exception:
            logger.exception("写入执行审计日志失败")

    @staticmethod
    def _summarize_failure(result: Dict[str, Any]) -> str:
        """从执行结果中提取适合列表/详情页展示的失败摘要。"""
        if result.get("error"):
            return str(result["error"])
        if result.get("message"):
            return str(result["message"])

        failed_records = []
        for item in result.get("records") or []:
            if item.get("status") not in ("failed", "error"):
                continue
            rec = item.get("record") or {}
            record_type = rec.get("type") or rec.get("record_type") or ""
            host = rec.get("host") or rec.get("name") or rec.get("hostname") or "@"
            message = item.get("message") or "执行失败"
            failed_records.append(f"{record_type} {host}: {message}".strip())

        if failed_records:
            summary = "；".join(failed_records[:3])
            if len(failed_records) > 3:
                summary += f"；另有 {len(failed_records) - 3} 条失败"
            return summary

        return "执行失败"

    @staticmethod
    def _normalize_records(request_data: Any) -> List[Dict[str, Any]]:
        """从松散的 request_data 中提取解析记录列表"""
        data = request_data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return []
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        if isinstance(data, dict):
            for key in ("records", "dns_records", "items"):
                if isinstance(data.get(key), list):
                    return [r for r in data[key] if isinstance(r, dict)]
            # 单条记录形式
            if data.get("record_type") or data.get("type"):
                return [data]
        return []

    @staticmethod
    def _to_int(value: Any, default: Optional[int]) -> Optional[int]:
        try:
            if value is None or value == "":
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        if not value or not isinstance(value, str):
            return None
        for fmt in (None, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                if fmt is None:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                return datetime.strptime(value, fmt)
            except (ValueError, TypeError):
                continue
        return None
