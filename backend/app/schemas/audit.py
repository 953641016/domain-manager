"""
审计日志相关数据验证Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class AuditLogResponse(BaseModel):
    """审计日志响应"""
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    before_state: Optional[Any] = None
    after_state: Optional[Any] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""
    total: int
    items: list[AuditLogResponse]


class AuditLogStatsResponse(BaseModel):
    """审计日志统计响应"""
    total: int
    success: int
    failed: int
    today: int
