"""
域名相关数据验证Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DomainCreate(BaseModel):
    """域名创建请求"""
    name: str = Field(..., description="域名名称", max_length=255)
    registrar_code: Optional[str] = Field(None, description="注册商代码")
    reg_account_id: Optional[int] = Field(None, description="注册账号ID")
    dns_provider_code: Optional[str] = Field(None, description="DNS解析商代码")
    dns_account_id: Optional[int] = Field(None, description="DNS账号ID")
    registration_date: Optional[datetime] = Field(None, description="注册日期")
    expiration_date: Optional[datetime] = Field(None, description="过期日期")
    auto_renew: bool = Field(False, description="是否自动续费")
    registrant_name: Optional[str] = Field(None, description="注册人姓名")
    registrant_email: Optional[str] = Field(None, description="注册人邮箱")
    registrant_phone: Optional[str] = Field(None, description="注册人电话")
    nameservers: Optional[List[str]] = Field([], description="NS服务器列表")
    tags: Optional[List[str]] = Field([], description="标签")
    remark: Optional[str] = Field(None, description="备注")


class DomainUpdate(BaseModel):
    """域名更新请求"""
    registrar_code: Optional[str] = Field(None, description="注册商代码")
    reg_account_id: Optional[int] = Field(None, description="注册账号ID")
    dns_provider_code: Optional[str] = Field(None, description="DNS解析商代码")
    dns_account_id: Optional[int] = Field(None, description="DNS账号ID")
    status: Optional[str] = Field(None, description="状态")
    auto_renew: Optional[bool] = Field(None, description="是否自动续费")
    registrant_name: Optional[str] = Field(None, description="注册人姓名")
    registrant_email: Optional[str] = Field(None, description="注册人邮箱")
    registrant_phone: Optional[str] = Field(None, description="注册人电话")
    nameservers: Optional[List[str]] = Field(None, description="NS服务器列表")
    tags: Optional[List[str]] = Field(None, description="标签")
    remark: Optional[str] = Field(None, description="备注")


class DomainResponse(BaseModel):
    """域名响应"""
    id: int
    name: str
    registrar_code: Optional[str] = None
    reg_account_id: Optional[int] = None
    dns_provider_code: Optional[str] = None
    dns_account_id: Optional[int] = None
    status: str
    registration_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    auto_renew: bool
    registrant_name: Optional[str] = None
    registrant_email: Optional[str] = None
    registrant_phone: Optional[str] = None
    nameservers: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    remark: Optional[str] = None
    owner_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DomainListResponse(BaseModel):
    """域名列表响应"""
    total: int
    items: List[DomainResponse]


class RegAccountCreate(BaseModel):
    """注册账号创建请求"""
    name: str = Field(..., description="账号名称", max_length=100)
    registrar_code: str = Field(..., description="注册商代码")
    api_key: Optional[str] = Field(None, description="API Key")
    api_secret: Optional[str] = Field(None, description="API Secret")
    remark: Optional[str] = Field(None, description="备注")
    target_owner_id: Optional[int] = Field(None, description="归属专员 ID（super_admin 创建时指定；domain_spec 忽略此字段）")
    set_as_default: bool = Field(False, description="审批通过创建账号后，将该账号设为归属专员默认注册账号")


class RegAccountUpdate(BaseModel):
    """注册账号更新请求"""
    name: Optional[str] = Field(None, description="账号名称")
    api_key: Optional[str] = Field(None, description="API Key")
    api_secret: Optional[str] = Field(None, description="API Secret")
    is_active: Optional[bool] = Field(None, description="是否启用")
    remark: Optional[str] = Field(None, description="备注")


class RegAccountResponse(BaseModel):
    """注册账号响应"""
    id: int
    name: str
    registrar_code: str
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None   # 归属专员姓名（API 层填充）
    is_active: bool
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DnsAccountCreate(BaseModel):
    """DNS账号创建请求"""
    name: str = Field(..., description="账号名称", max_length=100)
    provider_code: str = Field(..., description="解析商代码")
    api_key: Optional[str] = Field(None, description="API Key")
    api_secret: Optional[str] = Field(None, description="API Secret")
    remark: Optional[str] = Field(None, description="备注")
    target_owner_id: Optional[int] = Field(None, description="归属专员 ID（super_admin 创建时指定；domain_spec 忽略此字段）")


class DnsAccountUpdate(BaseModel):
    """DNS账号更新请求"""
    name: Optional[str] = Field(None, description="账号名称")
    api_key: Optional[str] = Field(None, description="API Key")
    api_secret: Optional[str] = Field(None, description="API Secret")
    is_active: Optional[bool] = Field(None, description="是否启用")
    remark: Optional[str] = Field(None, description="备注")


class DnsAccountResponse(BaseModel):
    """DNS账号响应"""
    id: int
    name: str
    provider_code: str
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None   # 归属专员姓名（API 层填充）
    is_active: bool
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 注册商 ==========

class RegistrarCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50, description="小写字母+下划线，如 cloudflare")
    description: Optional[str] = Field(None, max_length=500)
    api_endpoint: Optional[str] = Field(None, max_length=255)
    is_enabled: bool = True


class RegistrarUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    api_endpoint: Optional[str] = Field(None, max_length=255)
    is_enabled: Optional[bool] = None


class RegistrarResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    api_endpoint: Optional[str] = None
    is_enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== DNS解析商 ==========

class DnsProviderCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50, description="小写字母+下划线，如 cloudflare/dnspod")
    description: Optional[str] = Field(None, max_length=500)
    api_endpoint: Optional[str] = Field(None, max_length=255)
    is_enabled: bool = True


class DnsProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    api_endpoint: Optional[str] = Field(None, max_length=255)
    is_enabled: Optional[bool] = None


class DnsProviderResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    api_endpoint: Optional[str] = None
    is_enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
