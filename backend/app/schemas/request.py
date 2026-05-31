"""
申请相关数据验证Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class RequestCreate(BaseModel):
    """申请创建请求"""
    type: str = Field(..., description="申请类型: domain_register/dns_record")
    domain_name: str = Field(..., description="域名", max_length=255)
    request_data: Optional[Any] = Field(None, description="申请数据")
    selected_registrar_code: Optional[str] = Field(None, description="选择的注册商代码")
    selected_reg_account_id: Optional[int] = Field(None, description="选择的注册账号ID")
    selected_dns_provider_code: Optional[str] = Field(None, description="选择的DNS解析商代码")
    selected_dns_account_id: Optional[int] = Field(None, description="选择的DNS账号ID")
    source: Optional[str] = Field(None, description="来源: feishu_bot/feishu_table/web")
    conversation_id: Optional[str] = Field(None, description="飞书会话ID")


class RequestUpdate(BaseModel):
    """申请更新请求"""
    selected_registrar_code: Optional[str] = Field(None, description="选择的注册商代码")
    selected_reg_account_id: Optional[int] = Field(None, description="选择的注册账号ID")
    selected_dns_provider_code: Optional[str] = Field(None, description="选择的DNS解析商代码")
    selected_dns_account_id: Optional[int] = Field(None, description="选择的DNS账号ID")
    status: Optional[str] = Field(None, description="状态")


class RequestApprove(BaseModel):
    """申请审批请求"""
    comment: Optional[str] = Field(None, description="审批意见")
    # 审批时可选地指定/覆盖注册商与账号（PRD：专员可在审批时修改）
    selected_registrar_code: Optional[str] = Field(None, description="覆盖注册商代码")
    selected_reg_account_id: Optional[int] = Field(None, description="覆盖注册账号ID")
    selected_dns_provider_code: Optional[str] = Field(None, description="覆盖DNS解析商代码")
    selected_dns_account_id: Optional[int] = Field(None, description="覆盖DNS账号ID")
    # 是否在审批通过后自动执行（默认true，打通自动化主线）
    auto_execute: bool = Field(True, description="审批通过后是否自动执行")


class RequestReject(BaseModel):
    """申请拒绝请求"""
    reason: str = Field(..., description="拒绝原因")


class RequestResponse(BaseModel):
    """申请响应"""
    id: str
    type: str
    requester_id: int
    requester_name: str
    domain_name: str
    request_data: Optional[Any] = None
    selected_registrar_code: Optional[str] = None
    selected_reg_account_id: Optional[int] = None
    selected_dns_provider_code: Optional[str] = None
    selected_dns_account_id: Optional[int] = None
    status: str
    approver_id: Optional[int] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    execution_result: Optional[Any] = None
    error_message: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RequestListResponse(BaseModel):
    """申请列表响应"""
    total: int
    items: list[RequestResponse]


class RequestStatsResponse(BaseModel):
    """申请统计响应"""
    total: int
    pending: int
    approved: int
    rejected: int
    completed: int
    failed: int
