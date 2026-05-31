"""
申请执行服务
打通「审批通过 → 自动执行（注册/DNS配置）→ 差异化通知」主线。

设计原则：
- 防御式：任何一步出错都不会抛到调用方，统一落到 failed 状态并通知。
- 差异化通知：业务同事只收到简化结果；域名专员/审批人收到完整信息（含失败原因）。
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

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
        request.status = "completed" if success else "failed"
        request.execution_result = result
        request.error_message = None if success else (result.get("error") or result.get("message"))
        try:
            self.db.commit()
            self.db.refresh(request)
        except Exception:
            self.db.rollback()
            logger.exception("更新申请执行结果失败")

        # 审计 + 通知（均不影响主流程）
        self._safe_audit(request, result)
        self._notify(request, result)
        return result

    # ==================== DNS 解析执行 ====================

    def _execute_dns(self, request: Request) -> Dict[str, Any]:
        account = (
            self.domain_service.get_dns_account(request.selected_dns_account_id)
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

        results: List[Dict[str, Any]] = []
        for rec in records:
            op = str(rec.get("operation_type") or rec.get("operation") or "add").lower()
            rtype = rec.get("record_type") or rec.get("type")
            host = rec.get("host") or rec.get("name") or "@"
            value = rec.get("value") or rec.get("content")
            ttl = self._to_int(rec.get("ttl"), 300)
            priority = self._to_int(rec.get("priority"), None)
            record_id = rec.get("record_id") or rec.get("id")

            label = {"domain": request.domain_name, "type": rtype, "host": host, "value": value, "operation": op}

            if not rtype or value is None:
                results.append({"record": label, "status": "failed", "message": "记录类型或记录值缺失"})
                continue

            try:
                if op in ("update", "modify", "edit") and record_id:
                    r = adapter.update_record(request.domain_name, str(record_id), rtype, host, value, ttl, priority)
                else:
                    r = adapter.create_record(request.domain_name, rtype, host, value, ttl, priority)
            except Exception as e:
                r = {"success": False, "message": f"调用解析API异常: {str(e)}"}

            results.append({
                "record": label,
                "status": "success" if r.get("success") else "failed",
                "message": r.get("message", ""),
                "record_id": r.get("record_id"),
            })

        ok = sum(1 for x in results if x["status"] == "success")
        total = len(results)
        return {
            "success": ok == total and total > 0,
            "total": total,
            "success_count": ok,
            "failed_count": total - ok,
            "records": results,
            "dns_account_name": account.name,
            "provider_code": provider_code,
        }

    # ==================== 域名注册执行 ====================

    def _execute_register(self, request: Request) -> Dict[str, Any]:
        account = (
            self.domain_service.get_reg_account(request.selected_reg_account_id)
            if request.selected_reg_account_id else None
        )
        registrar_code = request.selected_registrar_code or (account.registrar_code if account else None)
        if not account or not registrar_code:
            return {"success": False, "error": "未配置注册账号或注册商"}

        try:
            adapter = RegistrarFactory.create_registrar(
                registrar_code, account.api_key, account.api_secret
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
        if avail.get("check_successful") and avail.get("available") is False:
            return {
                "success": False,
                "error": "域名当前已被注册，无法继续注册",
                "price": avail.get("price"),
                "currency": avail.get("currency"),
            }

        # 2. 执行注册
        registrant = {}
        if isinstance(request.request_data, dict):
            registrant = request.request_data.get("registrant") or request.request_data.get("registrant_info") or {}
        try:
            reg = adapter.register_domain(domain, registrant, nameservers=None)
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
            "price": avail.get("price"),
            "currency": avail.get("currency"),
            "registrar_code": registrar_code,
            "reg_account_name": account.name,
        }

    def _create_domain_record(self, request: Request, account, reg: Dict[str, Any]) -> None:
        existing = self.db.query(Domain).filter(Domain.name == request.domain_name).first()
        if existing:
            existing.registrar_code = account.registrar_code
            existing.reg_account_id = account.id
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
                status="active",
                registration_date=self._parse_date(reg.get("registration_date")),
                expiration_date=self._parse_date(reg.get("expiration_date")),
                owner_id=account.owner_id,
            ))
        self.db.commit()

    # ==================== 差异化通知 ====================

    def _notify(self, request: Request, result: Dict[str, Any]) -> None:
        type_label = TYPE_LABELS.get(request.type, request.type)
        success = bool(result.get("success"))
        requester = request.requester
        approver = request.approver

        # 业务同事：简化通知（不含失败原因）
        if requester:
            if success:
                msg = (f"✅ 您的{type_label}申请已完成\n"
                       f"域名：{request.domain_name}\n"
                       f"结果：成功")
            else:
                msg = (f"❌ 您的{type_label}申请未能完成\n"
                       f"域名：{request.domain_name}\n"
                       f"如需了解详情，请联系域名专员。")
            self._send(requester, msg)

        # 域名专员/审批人：完整信息（含失败原因）
        if approver and (not requester or approver.id != requester.id):
            detail = self._build_specialist_message(request, result, type_label, success)
            self._send(approver, detail)

    def _build_specialist_message(self, request: Request, result: Dict[str, Any],
                                  type_label: str, success: bool) -> str:
        head = f"{'✅' if success else '❌'} {type_label}{'成功' if success else '失败'}"
        lines = [head,
                 f"域名：{request.domain_name}",
                 f"申请人：{request.requester_name}"]

        if request.type == "domain_register":
            if result.get("reg_account_name"):
                lines.append(f"注册账号：{result['reg_account_name']}")
            if result.get("price") is not None:
                lines.append(f"价格：{result.get('price')} {result.get('currency', '')}".strip())
            if success:
                if result.get("expiration_date"):
                    lines.append(f"到期时间：{result['expiration_date']}")
                if result.get("order_id"):
                    lines.append(f"订单号：{result['order_id']}")
            else:
                lines.append(f"失败原因：{result.get('error') or result.get('message') or '未知错误'}")
        else:  # dns_record
            if result.get("dns_account_name"):
                lines.append(f"解析账号：{result['dns_account_name']}")
            total = result.get("total")
            if total is not None:
                lines.append(f"记录数：成功 {result.get('success_count', 0)} / 共 {total}")
            for item in (result.get("records") or []):
                rec = item.get("record", {})
                flag = "✓" if item.get("status") == "success" else "✗"
                line = f"  {flag} {rec.get('type','')} {rec.get('host','')} → {rec.get('value','')}"
                if item.get("status") != "success" and item.get("message"):
                    line += f"（{item['message']}）"
                lines.append(line)
            if not success and result.get("error"):
                lines.append(f"失败原因：{result['error']}")

        return "\n".join(lines)

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
                error_message=None if result.get("success") else (result.get("error") or result.get("message")),
            )
        except Exception:
            logger.exception("写入执行审计日志失败")

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
