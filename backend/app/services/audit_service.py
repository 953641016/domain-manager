"""
审计日志服务模块
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.audit import AuditLog


class AuditService:
    """审计日志服务类"""

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
        """
        记录审计日志
        """
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

    def get_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """获取审计日志列表"""
        query = self.db.query(AuditLog)

        if user_id:
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

        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    def get_log_count(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """获取审计日志总数"""
        query = self.db.query(AuditLog)

        if user_id:
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

        return query.count()

    def get_log(self, log_id: int) -> Optional[AuditLog]:
        """获取审计日志详情"""
        return self.db.query(AuditLog).filter(AuditLog.id == log_id).first()

    def get_stats(self) -> dict:
        """获取审计日志统计"""
        total = self.db.query(AuditLog).count()
        success = self.db.query(AuditLog).filter(AuditLog.status == "success").count()
        failed = self.db.query(AuditLog).filter(AuditLog.status == "failed").count()
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self.db.query(AuditLog).filter(AuditLog.created_at >= today).count()

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "today": today_count
        }

    def get_recent_logs(self, limit: int = 10) -> List[AuditLog]:
        """获取最近的审计日志"""
        return self.db.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()

    def get_user_action_summary(self, days: int = 30) -> List[dict]:
        """获取用户操作统计"""
        start_date = datetime.now() - timedelta(days=days)
        
        results = self.db.query(
            AuditLog.user_id,
            AuditLog.user_name,
            func.count(AuditLog.id).label("count")
        ).filter(
            AuditLog.created_at >= start_date
        ).group_by(
            AuditLog.user_id,
            AuditLog.user_name
        ).order_by(
            func.count(AuditLog.id).desc()
        ).limit(10).all()

        return [
            {"user_id": r.user_id, "user_name": r.user_name, "count": r.count}
            for r in results
        ]

    def cleanup_old_logs(self, days: int = 90) -> int:
        """清理旧的审计日志"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted = self.db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).delete()
        
        self.db.commit()
        return deleted
