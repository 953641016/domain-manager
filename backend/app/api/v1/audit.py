"""
审计日志 API 路由。

权限说明：
- 查询类路由需要 can_view_audit / can_view_statistics。
- domain_spec 仅返回本人及归属业务人员相关数据；admin/super_admin 返回全局数据。
- 清理日志是写操作，仅 admin/super_admin 可用。
- 返回格式：列表接口返回对象 {total, items}，统计接口返回对象。
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import require_admin, require_view_audit, require_view_statistics
from app.services.audit_service import AuditService
from app.schemas.audit import AuditLogResponse, AuditLogListResponse, AuditLogStatsResponse
from app.models.user import User

router = APIRouter(
    prefix="/audit",
    tags=["审计日志"],
)


def _get_specialist_scope_ids(db: Session, specialist_id: int) -> list[int]:
    rows = db.query(User.id).filter(User.assigned_specialist_id == specialist_id).all()
    ids = [row.id for row in rows]
    ids.append(specialist_id)
    return ids


def _get_audit_scope_user_ids(
    db: Session,
    current_user: User,
    user_id: Optional[int] = None,
) -> Optional[list[int]]:
    if current_user.role in ("admin", "super_admin"):
        return [user_id] if user_id else None
    if current_user.role == "domain_spec":
        scope_ids = _get_specialist_scope_ids(db, current_user.id)
        if user_id:
            return [user_id] if user_id in scope_ids else []
        return scope_ids
    return [current_user.id]


@router.get("/logs", response_model=AuditLogListResponse)
def get_audit_logs(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    action: Optional[str] = Query(None, description="操作类型"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    current_user: User = Depends(require_view_audit),
    db: Session = Depends(get_db),
):
    service = AuditService(db)
    user_ids = _get_audit_scope_user_ids(db, current_user, user_id)
    logs = service.get_logs(
        skip=skip,
        limit=limit,
        user_ids=user_ids,
        action=action,
        resource_type=resource_type,
        status=status_filter,
        start_time=start_time,
        end_time=end_time
    )
    total = service.get_log_count(
        user_ids=user_ids,
        action=action,
        resource_type=resource_type,
        status=status_filter,
        start_time=start_time,
        end_time=end_time
    )

    return AuditLogListResponse(
        total=total,
        items=[AuditLogResponse.model_validate(log) for log in logs]
    )


@router.get("/stats", response_model=AuditLogStatsResponse)
def get_audit_stats(
    current_user: User = Depends(require_view_statistics),
    db: Session = Depends(get_db),
):
    service = AuditService(db)
    stats = service.get_stats(user_ids=_get_audit_scope_user_ids(db, current_user))
    return AuditLogStatsResponse(**stats)


@router.get("/recent")
def get_recent_logs(
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    current_user: User = Depends(require_view_audit),
    db: Session = Depends(get_db),
):
    service = AuditService(db)
    logs = service.get_recent_logs(
        limit,
        user_ids=_get_audit_scope_user_ids(db, current_user),
    )
    return {
        "items": [AuditLogResponse.model_validate(log) for log in logs]
    }


@router.get("/user-summary")
def get_user_action_summary(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(require_view_audit),
    db: Session = Depends(get_db),
):
    service = AuditService(db)
    summary = service.get_user_action_summary(
        days,
        user_ids=_get_audit_scope_user_ids(db, current_user),
    )
    return {
        "days": days,
        "items": summary
    }


@router.delete("/cleanup")
def cleanup_old_logs(
    days: int = Query(90, ge=30, le=365, description="保留天数"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AuditService(db)
    deleted = service.cleanup_old_logs(days)
    return {
        "success": True,
        "deleted_count": deleted,
        "message": f"已清理 {deleted} 条超过 {days} 天的日志"
    }
