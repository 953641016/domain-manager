from datetime import datetime
from typing import Optional, Dict, Any

from database import SessionLocal, Request
from bots.dingtalk import DingTalkBot


class WorkflowEngine:
    def __init__(self):
        self.db = SessionLocal()
        self.bot = DingTalkBot()

    def create_request(
        self,
        request_type: str,
        requester_id: str,
        requester_name: str,
        domain: str,
        dns_config: Optional[Dict] = None,
        conversation_id: Optional[str] = None
    ) -> Request:
        request = Request(
            type=request_type,
            requester_id=requester_id,
            requester_name=requester_name,
            domain=domain,
            dns_config=dns_config or {},
            status="pending_approval",
            conversation_id=conversation_id
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)

        self._notify_admins_new_request(request)
        return request

    def approve_request(self, request_id: str, admin_user_id: str, comment: Optional[str] = None) -> Optional[Request]:
        request = self.db.query(Request).filter(Request.id == request_id).first()
        if not request:
            return None

        request.status = "processing"
        request.approval_history.append({
            "action": "approve",
            "user_id": admin_user_id,
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.db.commit()

        self._notify_requester_approved(request)
        self._execute_request(request)
        return request

    def reject_request(self, request_id: str, admin_user_id: str, reason: str) -> Optional[Request]:
        request = self.db.query(Request).filter(Request.id == request_id).first()
        if not request:
            return None

        request.status = "rejected"
        request.approval_history.append({
            "action": "reject",
            "user_id": admin_user_id,
            "comment": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.db.commit()

        self._notify_requester_rejected(request, reason)
        return request

    def get_request(self, request_id: str) -> Optional[Request]:
        return self.db.query(Request).filter(Request.id == request_id).first()

    def get_pending_requests(self) -> list:
        return self.db.query(Request).filter(Request.status == "pending_approval").all()

    def get_user_requests(self, user_id: str) -> list:
        return self.db.query(Request).filter(Request.requester_id == user_id).order_by(Request.created_at.desc()).all()

    def get_all_requests(self) -> list:
        return self.db.query(Request).order_by(Request.created_at.desc()).all()

    def _execute_request(self, request: Request):
        try:
            if request.type == "domain_register":
                result = self._register_domain(request)
            elif request.type == "dns_record":
                result = self._update_dns(request)
            else:
                result = {"success": False, "error": "未知的申请类型"}

            request.execution_result = result
            if result.get("success"):
                request.status = "completed"
                self._notify_requester_completed(request)
            else:
                request.status = "failed"
                self._notify_requester_failed(request, result.get("error", "执行失败"))
            self.db.commit()
        except Exception as e:
            request.status = "failed"
            request.execution_result = {"success": False, "error": str(e)}
            self.db.commit()
            self._notify_requester_failed(request, str(e))

    def _register_domain(self, request: Request) -> Dict[str, Any]:
        return {"success": True, "message": "域名注册（演示模式）", "domain": request.domain}

    def _update_dns(self, request: Request) -> Dict[str, Any]:
        return {"success": True, "message": "DNS更新（演示模式）", "domain": request.domain, "records": request.dns_config}

    def _notify_admins_new_request(self, request: Request):
        msg = f"🔔 新申请待审批\n\n"
        msg += f"申请编号: {request.id}\n"
        msg += f"类型: {'域名注册' if request.type == 'domain_register' else 'DNS解析'}\n"
        msg += f"域名: {request.domain}\n"
        msg += f"申请人: {request.requester_name}\n"
        self.bot.notify_admins(msg)

    def _notify_requester_approved(self, request: Request):
        if request.conversation_id:
            msg = f"✅ 申请已批准，正在处理中...\n\n申请编号: {request.id}"
            self.bot.send_text_message(request.conversation_id, msg)

    def _notify_requester_rejected(self, request: Request, reason: str):
        if request.conversation_id:
            msg = f"❌ 申请已拒绝\n\n申请编号: {request.id}\n原因: {reason}"
            self.bot.send_text_message(request.conversation_id, msg)

    def _notify_requester_completed(self, request: Request):
        if request.conversation_id:
            msg = f"✅ 申请已完成！\n\n申请编号: {request.id}\n域名: {request.domain}"
            self.bot.send_text_message(request.conversation_id, msg)

    def _notify_requester_failed(self, request: Request, error: str):
        if request.conversation_id:
            msg = f"⚠️ 申请执行失败\n\n申请编号: {request.id}\n错误: {error}"
            self.bot.send_text_message(request.conversation_id, msg)
