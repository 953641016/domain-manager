"""
角色权限定义
"""
from typing import List, Dict, Any
from app.config import Config

ROLE_PERMISSIONS = {
    "business": {
        "name": "业务人员",
        "description": "普通业务人员，可提交域名申请",
        "role_level": 0,
        "can_submit_register": True,
        "can_submit_dns": True,
        "can_direct_register": False,
        "can_renew": False,
        "can_approve": False,
        "can_query_availability": False,
        "can_query_info": False,
        "can_config_accounts": False,
        "can_manage_users": False,
        "can_manage_permissions": False,
        "web_access": False,
    },
    "domain_spec": {
        "name": "域名专员",
        "description": "负责域名管理的高级用户",
        "role_level": 1,
        "can_submit_register": True,
        "can_submit_dns": True,
        "can_direct_register": True,
        "can_renew": True,
        "can_approve": True,
        "can_query_availability": True,
        "can_query_info": True,
        "can_config_accounts": False,
        "can_manage_users": False,
        "can_manage_permissions": False,
        "web_access": True,
    },
    "admin": {
        "name": "系统管理员",
        "description": "系统管理员，可管理系统配置和用户",
        "role_level": 2,
        "can_submit_register": True,
        "can_submit_dns": True,
        "can_direct_register": True,
        "can_renew": True,
        "can_approve": True,
        "can_query_availability": True,
        "can_query_info": True,
        "can_config_accounts": True,
        "can_manage_users": True,
        "can_manage_permissions": False,
        "web_access": True,
    },
    "super_admin": {
        "name": "超级管理员",
        "description": "唯一超级管理员，拥有所有权限",
        "role_level": 3,
        "can_submit_register": True,
        "can_submit_dns": True,
        "can_direct_register": True,
        "can_renew": True,
        "can_approve": True,
        "can_query_availability": True,
        "can_query_info": True,
        "can_config_accounts": True,
        "can_manage_users": True,
        "can_manage_permissions": True,
        "web_access": True,
    }
}

# 需要超级管理员确认的关键操作类型
CRITICAL_OPERATIONS = {
    "add_domain_spec", "update_domain_spec", "update_user_role",
    "add_admin", "remove_admin", "config_accounts"
}

# 超级管理员飞书ID（从配置读取）
SUPER_ADMIN_FEISHU_USERID = Config.SUPER_ADMIN_FEISHU_USER_ID

# 关键角色变更需要确认的映射
ROLE_CONFIRMATION_REQUIRED = {
    "domain_spec", "admin", "super_admin"
}

# 需要超级管理员确认的角色变更
NEEDS_SUPER_ADMIN_CONFIRM = {
    ("business", "admin"), ("business", "super_admin"),
    ("domain_spec", "admin"), ("domain_spec", "super_admin"),
    ("admin", "super_admin"),
    ("super_admin", "admin"), ("super_admin", "domain_spec"),
    ("admin", "business"), ("admin", "domain_spec"),
}


def needs_confirmation(old_role: str, new_role: str) -> bool:
    """判断角色变更是否需要确认"""
    return (old_role, new_role) in NEEDS_SUPER_ADMIN_CONFIRM


def needs_super_admin_confirmation(old_role: str, new_role: str) -> bool:
    """判断角色变更是否需要超级管理员确认"""
    if new_role in ["super_admin"]:
        return True
    if old_role in ["super_admin"]:
        return True
    return (old_role, new_role) in NEEDS_SUPER_ADMIN_CONFIRM


def get_all_roles() -> List[Dict[str, Any]]:
    """获取所有角色信息列表"""
    return [
        {
            "code": role,
            "name": info["name"],
            "description": info["description"],
            "role_level": info["role_level"],
            "web_access": info.get("web_access", False),
            "permissions": [k for k, v in info.items() if isinstance(v, bool) and k.startswith("can_")]
        }
        for role, info in ROLE_PERMISSIONS.items()
    ]
