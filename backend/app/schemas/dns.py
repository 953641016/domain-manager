"""
DNS记录相关数据验证Schema
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DnsRecordCreate(BaseModel):
    """DNS记录创建请求"""
    domain_id: int = Field(..., description="域名ID")
    record_type: str = Field(..., description="记录类型: A/AAAA/CNAME/MX/TXT/SRV/NS")
    host: str = Field(..., description="主机记录", max_length=255)
    value: str = Field(..., description="记录值", max_length=1000)
    ttl: int = Field(300, ge=1, le=86400, description="TTL（秒）")
    priority: Optional[int] = Field(None, ge=0, le=65535, description="优先级（MX/SRV）")
    weight: Optional[int] = Field(None, ge=0, le=65535, description="权重（SRV）")
    port: Optional[int] = Field(None, ge=0, le=65535, description="端口（SRV）")
    remark: Optional[str] = Field(None, description="备注")


class DnsRecordUpdate(BaseModel):
    """DNS记录更新请求"""
    record_type: Optional[str] = Field(None, description="记录类型")
    host: Optional[str] = Field(None, description="主机记录")
    value: Optional[str] = Field(None, description="记录值")
    ttl: Optional[int] = Field(None, ge=1, le=86400, description="TTL（秒）")
    priority: Optional[int] = Field(None, ge=0, le=65535, description="优先级")
    weight: Optional[int] = Field(None, ge=0, le=65535, description="权重")
    port: Optional[int] = Field(None, ge=0, le=65535, description="端口")
    status: Optional[str] = Field(None, description="状态")
    remark: Optional[str] = Field(None, description="备注")


class DnsRecordResponse(BaseModel):
    """DNS记录响应"""
    id: int
    domain_id: int
    record_type: str
    host: str
    value: str
    ttl: int
    priority: Optional[int] = None
    weight: Optional[int] = None
    port: Optional[int] = None
    status: str
    sync_status: Optional[str] = None
    external_id: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DnsRecordListResponse(BaseModel):
    """DNS记录列表响应"""
    total: int
    items: list[DnsRecordResponse]


class DnsRecordSyncRequest(BaseModel):
    """DNS记录同步请求"""
    domain_id: int = Field(..., description="域名ID")
    dns_account_id: Optional[int] = Field(None, description="DNS账号ID")


class DnsRecordSyncResponse(BaseModel):
    """DNS记录同步响应"""
    success: bool
    message: str
    synced_count: int = 0
    failed_count: int = 0
    details: Optional[list] = None
