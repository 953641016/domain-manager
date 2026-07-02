"""
用户数据验证模式
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# 基础用户模式
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="用户姓名")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="手机号")
    department: Optional[str] = Field(None, max_length=100, description="部门")
    role: str = Field(..., description="用户角色")
    feishu_app_id: Optional[int] = Field(None, description="归属飞书应用ID")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


# 创建用户模式
class UserCreate(UserBase):
    feishu_userid: str = Field(..., min_length=1, max_length=100, description="飞书用户ID", alias="feishu_user_id")
    feishu_unionid: Optional[str] = Field(None, max_length=100, description="飞书UnionID", alias="feishu_union_id")
    feishu_openid: Optional[str] = Field(None, max_length=100, description="飞书OpenID", alias="feishu_open_id")


# 更新用户模式
class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = None
    feishu_app_id: Optional[int] = Field(None, description="归属飞书应用ID")
    is_active: Optional[bool] = None
    remark: Optional[str] = Field(None, max_length=500)
    assigned_specialist_id: Optional[int] = Field(None, description="归属域名专员ID（业务同事专用）")


# 用户响应模式
class UserResponse(UserBase):
    id: int
    feishu_app_name: Optional[str] = None
    feishu_userid: str = Field(alias="feishu_user_id")
    feishu_unionid: Optional[str] = Field(None, alias="feishu_union_id")
    feishu_openid: Optional[str] = Field(None, alias="feishu_open_id")
    is_active: bool
    created_at: datetime
    updated_at: datetime
    permissions: List[str] = Field(default_factory=list)
    assigned_specialist_id: Optional[int] = None

    class Config:
        from_attributes = True
        populate_by_name = True


# 用户列表响应
class UserListResponse(BaseModel):
    total: int
    items: List[UserResponse]


# 角色信息
class RoleInfo(BaseModel):
    code: str
    name: str
    description: str
    web_access: bool
    permissions: List[str]
