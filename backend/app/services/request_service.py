"""
申请管理服务模块
"""
import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.models.request import Request
from app.schemas.request import RequestCreate, RequestUpdate


class RequestService:
    """申请服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_requests(
        self,
        status: Optional[str] = None,
        request_type: Optional[str] = None,
        requester_id: Optional[int] = None,
        domain_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Request]:
        """获取申请列表"""
        query = self.db.query(Request)

        if status:
            query = query.filter(Request.status == status)
        if request_type:
            query = query.filter(Request.type == request_type)
        if requester_id:
            query = query.filter(Request.requester_id == requester_id)
        if domain_name:
            query = query.filter(Request.domain_name.contains(domain_name))

        return query.order_by(Request.created_at.desc()).offset(skip).limit(limit).all()

    def get_request_count(
        self,
        status: Optional[str] = None,
        request_type: Optional[str] = None,
        requester_id: Optional[int] = None,
        domain_name: Optional[str] = None
    ) -> int:
        """获取申请总数"""
        query = self.db.query(Request)

        if status:
            query = query.filter(Request.status == status)
        if request_type:
            query = query.filter(Request.type == request_type)
        if requester_id:
            query = query.filter(Request.requester_id == requester_id)
        if domain_name:
            query = query.filter(Request.domain_name.contains(domain_name))

        return query.count()

    def get_request(self, request_id: str) -> Optional[Request]:
        """获取申请详情"""
        return self.db.query(Request).filter(Request.id == request_id).first()

    def create_request(self, data: RequestCreate, requester_id: int, requester_name: str) -> Request:
        """创建申请"""
        # 生成UUID
        request_id = str(uuid.uuid4())

        request = Request(
            id=request_id,
            type=data.type,
            requester_id=requester_id,
            requester_name=requester_name,
            domain_name=data.domain_name,
            request_data=data.request_data,
            selected_registrar_code=data.selected_registrar_code,
            selected_reg_account_id=data.selected_reg_account_id,
            selected_dns_provider_code=data.selected_dns_provider_code,
            selected_dns_account_id=data.selected_dns_account_id,
            source=data.source,
            conversation_id=data.conversation_id,
            status="pending"
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def update_request(self, request_id: str, data: RequestUpdate) -> Optional[Request]:
        """更新申请"""
        request = self.get_request(request_id)
        if not request:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(request, key, value)

        self.db.commit()
        self.db.refresh(request)
        return request

    def approve_request(self, request_id: str, approver_id: int, approver_name: str, comment: Optional[str] = None) -> Optional[Request]:
        """审批通过申请"""
        request = self.get_request(request_id)
        if not request:
            return None

        if request.status != "pending":
            raise ValueError(f"申请状态不允许审批，当前状态: {request.status}")

        request.status = "approved"
        request.approver_id = approver_id
        request.approver_name = approver_name
        request.approved_at = datetime.now()
        if comment:
            request.request_data = request.request_data or {}
            request.request_data["approval_comment"] = comment

        self.db.commit()
        self.db.refresh(request)
        return request

    def reject_request(self, request_id: str, approver_id: int, approver_name: str, reason: str) -> Optional[Request]:
        """拒绝申请"""
        request = self.get_request(request_id)
        if not request:
            return None

        if request.status != "pending":
            raise ValueError(f"申请状态不允许拒绝，当前状态: {request.status}")

        request.status = "rejected"
        request.approver_id = approver_id
        request.approver_name = approver_name
        request.approved_at = datetime.now()
        request.reject_reason = reason

        self.db.commit()
        self.db.refresh(request)
        return request

    def complete_request(self, request_id: str, execution_result: dict = None) -> Optional[Request]:
        """标记申请为已完成"""
        request = self.get_request(request_id)
        if not request:
            return None

        request.status = "completed"
        request.execution_result = execution_result

        self.db.commit()
        self.db.refresh(request)
        return request

    def fail_request(self, request_id: str, error_message: str) -> Optional[Request]:
        """标记申请为失败"""
        request = self.get_request(request_id)
        if not request:
            return None

        request.status = "failed"
        request.error_message = error_message

        self.db.commit()
        self.db.refresh(request)
        return request

    def get_stats(self) -> dict:
        """获取申请统计"""
        total = self.db.query(Request).count()
        pending = self.db.query(Request).filter(Request.status == "pending").count()
        approved = self.db.query(Request).filter(Request.status == "approved").count()
        rejected = self.db.query(Request).filter(Request.status == "rejected").count()
        completed = self.db.query(Request).filter(Request.status == "completed").count()
        failed = self.db.query(Request).filter(Request.status == "failed").count()

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "completed": completed,
            "failed": failed
        }

    def get_pending_requests(self) -> List[Request]:
        """获取待审批的申请"""
        return self.db.query(Request).filter(
            Request.status == "pending"
        ).order_by(Request.created_at.asc()).all()

    def get_my_requests(self, requester_id: int, skip: int = 0, limit: int = 100) -> List[Request]:
        """获取我的申请"""
        return self.db.query(Request).filter(
            Request.requester_id == requester_id
        ).order_by(Request.created_at.desc()).offset(skip).limit(limit).all()
