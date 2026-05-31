"""
用户服务 - 用户管理业务逻辑
"""

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User
from app.models.permission import ROLE_PERMISSIONS, get_all_roles
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: int) -> Optional[User]:
        """
        根据ID获取用户
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_feishu_userid(self, feishu_userid: str) -> Optional[User]:
        """
        根据飞书用户ID获取用户
        """
        return self.db.query(User).filter(User.feishu_user_id == feishu_userid).first()

    def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """
        获取用户列表
        """
        query = self.db.query(User)

        if role:
            query = query.filter(User.role == role)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if search:
            query = query.filter(
                (User.name.contains(search)) |
                (User.email.contains(search)) |
                (User.feishu_user_id.contains(search))
            )

        return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    def get_users_count(
        self,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> int:
        """
        获取用户总数
        """
        query = self.db.query(func.count(User.id))

        if role:
            query = query.filter(User.role == role)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        if search:
            query = query.filter(
                (User.name.contains(search)) |
                (User.email.contains(search)) |
                (User.feishu_user_id.contains(search))
            )

        return query.scalar() or 0

    def create_user(self, user_in: UserCreate) -> Tuple[User, bool]:
        """
        创建用户

        Returns:
            (User, bool) - (用户对象, 是否需要管理员确认)
        """
        # 检查用户是否已存在
        existing_user = self.get_user_by_feishu_userid(user_in.feishu_userid)
        if existing_user:
            raise ValueError(f"用户已存在: {user_in.feishu_userid}")

        # 获取角色权限
        role_perms = ROLE_PERMISSIONS.get(user_in.role, {})
        permission_list = [k for k, v in role_perms.items() if isinstance(v, bool)]

        # 判断是否需要确认
        needs_confirmation = user_in.role in ["domain_spec", "admin"]

        # 创建用户
        user = User(
            name=user_in.name,
            email=user_in.email,
            phone=user_in.phone,
            department=user_in.department,
            feishu_user_id=user_in.feishu_userid,
            feishu_union_id=user_in.feishu_unionid,
            feishu_open_id=user_in.feishu_openid,
            role=user_in.role,
            permissions=permission_list,
            remark=user_in.remark,
            is_active=True
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user, needs_confirmation

    def update_user(self, user_id: int, user_in: UserUpdate) -> Tuple[Optional[User], bool, Dict[str, Any]]:
        """
        更新用户

        Returns:
            (Optional[User], bool, Dict) - (用户对象, 是否需要确认, 变更详情)
        """
        user = self.get_user(user_id)
        if not user:
            return None, False, {}

        # 更新字段
        update_data = user_in.model_dump(exclude_unset=True)

        # 判断是否需要确认（角色变更为高权限）
        old_role = user.role
        new_role = update_data.get("role", old_role)
        needs_confirmation = False
        change_details = {}

        # 检查是否是关键角色变更
        critical_role_change = (
            (old_role != "domain_spec" and new_role == "domain_spec") or
            (old_role != "admin" and new_role == "admin") or
            (old_role == "admin" and new_role != "admin") or
            (old_role == "domain_spec" and new_role != "domain_spec" and new_role != "business")
        )

        if critical_role_change:
            needs_confirmation = True
            change_details = {
                "old_role": old_role,
                "new_role": new_role
            }

        # 如果更新了角色，重新计算权限
        if "role" in update_data:
            role_perms = ROLE_PERMISSIONS.get(update_data["role"], {})
            update_data["permissions"] = [k for k, v in role_perms.items() if isinstance(v, bool)]

        for field, value in update_data.items():
            if field in change_details:
                continue
            old_value = getattr(user, field)
            if old_value != value:
                change_details[field] = {
                    "old": old_value,
                    "new": value
                }

        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)

        return user, needs_confirmation, change_details

    def delete_user(self, user_id: int) -> bool:
        """
        删除用户（软删除，将 is_active 设为 False）
        """
        user = self.get_user(user_id)
        if not user:
            return False

        user.is_active = False
        self.db.commit()

        return True

    def activate_user(self, user_id: int) -> Optional[User]:
        """
        激活用户
        """
        user = self.get_user(user_id)
        if not user:
            return None

        user.is_active = True
        self.db.commit()
        self.db.refresh(user)

        return user

    @staticmethod
    def get_role_info(role_code: str) -> Optional[dict]:
        """
        获取角色信息
        """
        if role_code not in ROLE_PERMISSIONS:
            return None

        role_data = ROLE_PERMISSIONS[role_code]
        return {
            "code": role_code,
            "name": role_data["name"],
            "description": role_data["description"],
            "web_access": role_data.get("web_access", False),
            "permissions": [k for k, v in role_data.items() if isinstance(v, bool)]
        }

    @staticmethod
    def get_all_roles() -> List[dict]:
        """
        获取所有角色信息
        """
        return get_all_roles()
