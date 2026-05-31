"""
依赖注入模块 - 认证、权限等
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.permission import ROLE_PERMISSIONS

# HTTP Bearer Token 认证
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    获取当前登录用户

    Returns:
        当前用户对象，如果未认证则返回 None
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == int(user_id)).first()
    return user


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户（必须已认证且有Web端访问权限）

    Raises:
        HTTPException: 401 如果未认证
        HTTPException: 403 如果没有Web访问权限
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    # 检查Web访问权限
    from app.models.permission import ROLE_PERMISSIONS
    role_perms = ROLE_PERMISSIONS.get(current_user.role, {})
    if not role_perms.get("web_access", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"您的角色（{role_perms.get('name', current_user.role)}）没有Web端访问权限，请通过飞书客户端提交申请"
        )
    return current_user


class PermissionChecker:
    """权限检查装饰器工厂"""

    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(
        self, current_user: User = Depends(get_current_active_user)
    ) -> User:
        """检查用户权限"""
        role_perms = ROLE_PERMISSIONS.get(current_user.role, {})

        # 超级管理员拥有所有权限
        if current_user.role == "super_admin":
            return current_user

        # 检查权限
        if not role_perms.get(self.required_permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要 {self.required_permission} 权限"
            )
        return current_user


class RoleChecker:
    """角色检查装饰器工厂"""

    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, current_user: User = Depends(get_current_active_user)
    ) -> User:
        """检查用户角色"""
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要以下角色之一: {', '.join(self.allowed_roles)}"
            )
        return current_user


# 预定义的权限检查器（对应 permission.py 中的 can_xxx 键名）
require_manage_users     = PermissionChecker("can_manage_users")
require_manage_accounts  = PermissionChecker("can_manage_accounts")
require_view_accounts    = PermissionChecker("can_view_accounts")
require_manage_providers = PermissionChecker("can_manage_providers")
require_view_providers   = PermissionChecker("can_view_providers")
require_manage_defaults  = PermissionChecker("can_manage_defaults")
require_approve_request  = PermissionChecker("can_approve_request")
require_view_domains     = PermissionChecker("can_view_domains")
require_submit_request   = PermissionChecker("can_submit_request")
require_direct_register  = PermissionChecker("can_direct_register")
require_view_users       = PermissionChecker("can_view_users")
require_view_all_requests = PermissionChecker("can_view_all_requests")

# 向后兼容别名（旧代码引用，逐步替换）
require_manage_users_compat = require_manage_users
require_config_accounts = require_manage_accounts   # 旧名，已废弃
require_approve = require_approve_request            # 旧名，已废弃

# 预定义的角色检查器（尽量用 PermissionChecker 替代，此处保留作兜底）
require_admin       = RoleChecker(["admin", "super_admin"])
require_super_admin = RoleChecker(["super_admin"])
require_domain_spec = RoleChecker(["domain_spec", "super_admin"])

