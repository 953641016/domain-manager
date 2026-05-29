"""
用户确认操作相关Schema
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class UserOperationConfirmationBase(BaseModel):
    """基础Schema"""
    pass


class UserOperationConfirmationCreate(BaseModel):
    """创建确认请求"""
    operation_type: str = Field(..., description="操作类型")
    target_user_data: Dict[str, Any] = Field(..., description="目标用户数据")
    operation_details: Dict[str, Any] = Field(..., description="操作详情")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class UserOperationConfirmationReject(BaseModel):
    """拒绝请求"""
    reject_reason: Optional[str] = Field(None, max_length=500, description="拒绝原因")


class UserOperationConfirmationResponse(BaseModel):
    """确认操作响应"""
    id: int
    operation_type: str
    initiator_user_id: int
    initiator_name: str
    initiator_feishu_userid: str
    target_user_data: Dict[str, Any]
    operation_details: Dict[str, Any]
    status: str
    approver_user_id: Optional[int] = None
    approver_name: Optional[str] = None
    approver_feishu_userid: Optional[str] = None
    feishu_message_id: Optional[str] = None
    feishu_chat_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    remark: Optional[str] = None
    operation_description: Optional[str] = None

    class Config:
        from_attributes = True


class UserOperationConfirmationListResponse(BaseModel):
    """确认操作列表响应"""
    total: int
    items: List[UserOperationConfirmationResponse]
