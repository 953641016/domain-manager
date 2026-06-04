"""
角色权限定义 —— 单一事实源。

对照 docs/权限与流程设计.md：
- business 只能通过飞书提交申请，不允许登录 Web。
- domain_spec 管自己的账号、域名、申请、统计和审计，不管人。
- admin 管人员和系统查询，不碰账号、服务商、域名业务数据。
- super_admin 拥有全部权限，敏感写操作仍需飞书确认。
"""
from typing import List, Dict, Any
from app.config import Config


ROLE_PERMISSIONS: Dict[str, Dict[str, Any]] = {
    "business": {
        "name": "业务人员",
        "description": "通过飞书发起域名/DNS申请；必须归属唯一专员",
        "role_level": 0,
        "web_access": False,
        "can_submit_request": True,
        "can_direct_register": False,
        "can_approve_request": False,
        "can_view_own_requests": True,
        "can_view_all_requests": False,
        "can_view_domains": False,
        "can_view_audit": False,
        "can_view_statistics": False,
        "can_view_accounts": False,
        "can_manage_accounts": False,
        "can_view_providers": False,
        "can_manage_providers": False,
        "can_manage_defaults": False,
        "can_view_users": False,
        "can_manage_users": False,
    },
    "domain_spec": {
        "name": "域名专员",
        "description": "管理自己的域名账号、做业务（注册/解析/审批）；不管人",
        "role_level": 1,
        "web_access": True,
        "can_submit_request": True,
        "can_direct_register": True,
        "can_approve_request": True,
        "can_view_own_requests": True,
        "can_view_all_requests": False,
        "can_view_domains": True,
        "can_view_audit": True,
        "can_view_statistics": True,
        "can_view_accounts": True,
        "can_manage_accounts": True,
        "can_view_providers": True,
        "can_manage_providers": True,
        "can_manage_defaults": True,
        "can_view_users": False,
        "can_manage_users": False,
    },
    "admin": {
        "name": "系统管理员",
        "description": "技术运维/迭代岗：管人、管系统；无业务侧和账号权限",
        "role_level": 2,
        "web_access": True,
        "can_submit_request": False,
        "can_direct_register": False,
        "can_approve_request": False,
        "can_view_own_requests": True,
        "can_view_all_requests": True,
        "can_view_domains": False,
        "can_view_audit": True,
        "can_view_statistics": True,
        "can_view_accounts": False,
        "can_manage_accounts": False,
        "can_view_providers": False,
        "can_manage_providers": False,
        "can_manage_defaults": False,
        "can_view_users": True,
        "can_manage_users": True,
    },
    "super_admin": {
        "name": "超级管理员",
        "description": "技术岗 + 业务岗双重身份；唯一的飞书确认闸门",
        "role_level": 3,
        "web_access": True,
        "can_submit_request": True,
        "can_direct_register": True,
        "can_approve_request": True,
        "can_view_own_requests": True,
        "can_view_all_requests": True,
        "can_view_domains": True,
        "can_view_audit": True,
        "can_view_statistics": True,
        "can_view_accounts": True,
        "can_manage_accounts": True,
        "can_view_providers": True,
        "can_manage_providers": True,
        "can_manage_defaults": True,
        "can_view_users": True,
        "can_manage_users": True,
    },
}


REQUIRES_SUPER_ADMIN_CONFIRMATION = {
    "can_manage_accounts",
    "can_manage_providers",
    "can_manage_defaults",
    "can_manage_users",
}

SUPER_ADMIN_FEISHU_USERID = Config.SUPER_ADMIN_FEISHU_USER_ID

NEEDS_SUPER_ADMIN_CONFIRM = {
    ("business", "domain_spec"), ("business", "admin"), ("business", "super_admin"),
    ("domain_spec", "admin"), ("domain_spec", "super_admin"), ("domain_spec", "business"),
    ("admin", "domain_spec"), ("admin", "super_admin"), ("admin", "business"),
    ("super_admin", "admin"), ("super_admin", "domain_spec"), ("super_admin", "business"),
}


def has_permission(role: str, permission: str) -> bool:
    role_info = ROLE_PERMISSIONS.get(role, {})
    return bool(role_info.get(permission, False))


def needs_confirmation(permission: str) -> bool:
    return permission in REQUIRES_SUPER_ADMIN_CONFIRMATION


def needs_super_admin_confirmation(old_role: str, new_role: str) -> bool:
    return (old_role, new_role) in NEEDS_SUPER_ADMIN_CONFIRM


def get_all_roles() -> List[Dict[str, Any]]:
    return [
        {
            "code": role,
            "name": info["name"],
            "description": info["description"],
            "role_level": info["role_level"],
            "web_access": info.get("web_access", False),
            "permissions": [
                key for key, value in info.items()
                if isinstance(value, bool) and key.startswith("can_")
            ],
        }
        for role, info in ROLE_PERMISSIONS.items()
    ]
