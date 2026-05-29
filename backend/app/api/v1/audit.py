"""
审计日志API路由
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import require_admin
from app.services.audit_service import AuditService
from app.schemas.audit import AuditLogResponse, AuditLogListResponse, AuditLogStatsResponse
from app.models.user import User

router = APIRouter(
    prefix="/audit",
    tags=["审计日志"],
)


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
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    获取审计日志列表

    需要管理员权限
    """
    service = AuditService(db)
    logs = service.get_logs(
        skip=skip,
        limit=limit,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        status=status_filter,
        start_time=start_time,
        end_time=end_time
    )
    total = service.get_log_count(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        status=status_filter,
        start_time=start_time,
        end_time=end_time
    )

    return AuditLogListResponse(
        total=total,
        items=[AuditLogResponse.model_validate(l) for l in logs]
    )


@router.get("/stats", response_model=AuditLogStatsResponse)
def get_audit_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    获取审计日志统计

    需要管理员权限
    """
    service = AuditService(db)
    stats = service.get_stats()
    return AuditLogStatsResponse(**stats)


@router.get("/recent")
def get_recent_logs(
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    获取最近的审计日志

    需要管理员权限
    """
    service = AuditService(db)
    logs = service.get_recent_logs(limit)

    return {
        "items": [AuditLogResponse.model_validate(l) for l in logs]
    }


@router.get("/user-summary")
def get_user_action_summary(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    获取用户操作统计

    需要管理员权限
    """
    service = AuditService(db)
    summary = service.get_user_action_summary(days)

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
    """
    清理旧的审计日志

    需要管理员权限
    """
    service = AuditService(db)
    deleted = service.cleanup_old_logs(days)

    return {
        "success": True,
        "deleted_count": deleted,
        "message": f"已清理 {deleted} 条超过 {days} 天的日志"
    }
