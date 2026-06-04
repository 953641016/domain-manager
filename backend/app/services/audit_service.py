"""
审计日志服务模块
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.audit import AuditLog


class AuditService:
    """审计日志服务"""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> AuditLog:
        log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            user_id=user_id,
            user_name=user_name,
            method=method,
            path=path,
            ip_address=ip_address,
            user_agent=user_agent,
            before_state=before_state,
            after_state=after_state,
            status=status,
            error_message=error_message
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def _apply_filters(
        self,
        query,
        user_id: Optional[int] = None,
        user_ids: Optional[List[int]] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        if user_ids is not None:
            if not user_ids:
                return None
            query = query.filter(AuditLog.user_id.in_(user_ids))
        elif user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if status:
            query = query.filter(AuditLog.status == status)
        if start_time:
            query = query.filter(AuditLog.created_at >= start_time)
        if end_time:
            query = query.filter(AuditLog.created_at <= end_time)
        return query

    def get_logs(
        self,
        user_id: Optional[int] = None,
        user_ids: Optional[List[int]] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        query = self._apply_filters(
            self.db.query(AuditLog),
            user_id=user_id,
            user_ids=user_ids,
            action=action,
            resource_type=resource_type,
            status=status,
            start_time=start_time,
            end_time=end_time,
        )
        if query is None:
            return []
        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    def get_log_count(
        self,
        user_id: Optional[int] = None,
        user_ids: Optional[List[int]] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        query = self._apply_filters(
            self.db.query(AuditLog),
            user_id=user_id,
            user_ids=user_ids,
            action=action,
            resource_type=resource_type,
            status=status,
            start_time=start_time,
            end_time=end_time,
        )
        return 0 if query is None else query.count()

    def get_log(self, log_id: int) -> Optional[AuditLog]:
        return self.db.query(AuditLog).filter(AuditLog.id == log_id).first()

    def get_stats(self, user_ids: Optional[List[int]] = None) -> dict:
        query = self._apply_filters(self.db.query(AuditLog), user_ids=user_ids)
        if query is None:
            return {"total": 0, "success": 0, "failed": 0, "today": 0}

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            "total": query.count(),
            "success": query.filter(AuditLog.status == "success").count(),
            "failed": query.filter(AuditLog.status == "failed").count(),
            "today": query.filter(AuditLog.created_at >= today).count(),
        }

    def get_recent_logs(self, limit: int = 10, user_ids: Optional[List[int]] = None) -> List[AuditLog]:
        query = self._apply_filters(self.db.query(AuditLog), user_ids=user_ids)
        if query is None:
            return []
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    def get_user_action_summary(self, days: int = 30, user_ids: Optional[List[int]] = None) -> List[dict]:
        start_date = datetime.now() - timedelta(days=days)
        query = self.db.query(
            AuditLog.user_id,
            AuditLog.user_name,
            func.count(AuditLog.id).label("count")
        ).filter(AuditLog.created_at >= start_date)

        if user_ids is not None:
            if not user_ids:
                return []
            query = query.filter(AuditLog.user_id.in_(user_ids))

        results = query.group_by(
            AuditLog.user_id,
            AuditLog.user_name
        ).order_by(
            func.count(AuditLog.id).desc()
        ).limit(10).all()

        return [
            {"user_id": row.user_id, "user_name": row.user_name, "count": row.count}
            for row in results
        ]

    def cleanup_old_logs(self, days: int = 90) -> int:
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted = self.db.query(AuditLog).filter(AuditLog.created_at < cutoff_date).delete()
        self.db.commit()
        return deleted
