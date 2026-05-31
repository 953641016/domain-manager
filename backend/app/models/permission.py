"""
角色权限定义 — 单一事实源
对照 docs/权限与流程设计.md 第 1-2 章
所有 API 端点应通过 require_permission() 依赖检查，不得硬编码角色字符串
"""
from typing import List, Dict, Any
from app.config import Config

# --------------------------------------------------------------------------
# 权限矩阵
# 每个布尔权限 can_xxx 对应设计文档中矩阵的一列
# 新增权限只在这里加，API 通过 require_permission("can_xxx") 引用
# --------------------------------------------------------------------------
ROLE_PERMISSIONS: Dict[str, Dict[str, Any]] = {

    "business": {
        "name": "业务人员",
        "description": "通过飞书发起域名/DNS申请；必须归属唯一专员",
        "role_level": 0,
        "web_access": False,
        # 业务侧（飞书驱动）
        "can_submit_request": True,       # 提交域名注册/DNS申请（飞书）
        "can_direct_register": False,     # 直接注册/解析（飞书，免审批）
        "can_approve_request": False,     # 审批申请
        # 查询
        "can_view_own_requests": True,    # 查看自己的申请记录
        "can_view_all_requests": False,
        "can_view_domains": False,
        # 账号/服务商/配置（Web配置层）
        "can_view_accounts": False,
        "can_manage_accounts": False,     # 需超管确认
        "can_view_providers": False,
        "can_manage_providers": False,    # 需超管确认
        "can_manage_defaults": False,     # 需超管确认
        # 人员管理（Web配置层）
        "can_view_users": False,
        "can_manage_users": False,        # 需超管确认
    },

    "domain_spec": {
        "name": "域名专员",
        "description": "管理自己的域名账号、做业务（注册/解析/审批）；不管人",
        "role_level": 1,
        "web_access": True,
        # 业务侧（飞书驱动）
        "can_submit_request": True,
        "can_direct_register": True,      # 可在飞书直接注册/解析（免审批）
        "can_approve_request": True,      # 审批归属自己的申请
        # 查询
        "can_view_own_requests": True,
        "can_view_all_requests": False,   # 仅归属自己的（在 Service 层过滤）
        "can_view_domains": True,         # 仅自己的（owner_id 过滤）
        # 账号/服务商/配置（Web配置层，操作需超管确认）
        "can_view_accounts": True,        # 仅自己的
        "can_manage_accounts": True,      # ⚠️ 需超管飞书确认
        "can_view_providers": True,
        "can_manage_providers": True,     # ⚠️ 需超管飞书确认
        "can_manage_defaults": True,      # ⚠️ 需超管飞书确认
        # 人员管理 — 硬边界：不予人员权限
        "can_view_users": False,
        "can_manage_users": False,
    },

    "admin": {
        "name": "系统管理员",
        "description": "技术运维/迭代岗：管人管系统；无业务侧权限，无账号/服务商权限",
        "role_level": 2,
        "web_access": True,
        # 业务侧 — 硬边界：不予任何业务权限
        "can_submit_request": False,
        "can_direct_register": False,
        "can_approve_request": False,
        # 查询（admin 可查全局申请记录/日志/统计，但看不到账号/域名业务数据）
        "can_view_own_requests": True,
        "can_view_all_requests": True,    # 全局申请记录（用于管理追踪）
        "can_view_domains": False,        # 不参与业务，看不到域名账号数据
        # 账号/服务商/配置 — 硬边界：不予任何账号/服务商权限
        "can_view_accounts": False,
        "can_manage_accounts": False,
        "can_view_providers": False,
        "can_manage_providers": False,
        "can_manage_defaults": False,
        # 人员管理（Web配置层，操作需超管确认）
        "can_view_users": True,
        "can_manage_users": True,         # ⚠️ 需超管飞书确认
    },

    "super_admin": {
        "name": "超级管理员",
        "description": "技术岗+业务岗双重身份；唯一的飞书确认闸门",
        "role_level": 3,
        "web_access": True,
        # 业务侧
        "can_submit_request": True,
        "can_direct_register": True,
        "can_approve_request": True,
        # 查询
        "can_view_own_requests": True,
        "can_view_all_requests": True,
        "can_view_domains": True,
        # 账号/服务商/配置（操作需超管飞书自确认）
        "can_view_accounts": True,
        "can_manage_accounts": True,      # ⚠️ 需超管飞书自确认
        "can_view_providers": True,
        "can_manage_providers": True,     # ⚠️ 需超管飞书自确认
        "can_manage_defaults": True,      # ⚠️ 需超管飞书自确认
        # 人员管理（操作需超管飞书自确认）
        "can_view_users": True,
        "can_manage_users": True,         # ⚠️ 需超管飞书自确认
    },
}

# 需要超管飞书确认的操作标记（供 API 层判断是否走 Confirmation 流）
REQUIRES_SUPER_ADMIN_CONFIRMATION = {
    "can_manage_accounts",
    "can_manage_providers",
    "can_manage_defaults",
    "can_manage_users",
}

# 超级管理员飞书ID（从配置读取）
SUPER_ADMIN_FEISHU_USERID = Config.SUPER_ADMIN_FEISHU_USER_ID

# 角色变更：所有变更均需超管确认（保持向前兼容）
NEEDS_SUPER_ADMIN_CONFIRM = {
    ("business", "domain_spec"), ("business", "admin"), ("business", "super_admin"),
    ("domain_spec", "admin"), ("domain_spec", "super_admin"), ("domain_spec", "business"),
    ("admin", "domain_spec"), ("admin", "super_admin"), ("admin", "business"),
    ("super_admin", "admin"), ("super_admin", "domain_spec"), ("super_admin", "business"),
}


def has_permission(role: str, permission: str) -> bool:
    """检查角色是否拥有某个权限"""
    role_info = ROLE_PERMISSIONS.get(role, {})
    return bool(role_info.get(permission, False))


def needs_confirmation(permission: str) -> bool:
    """该权限对应的操作是否需要超管飞书确认"""
    return permission in REQUIRES_SUPER_ADMIN_CONFIRMATION


def needs_super_admin_confirmation(old_role: str, new_role: str) -> bool:
    """判断角色变更是否需要超级管理员确认"""
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
