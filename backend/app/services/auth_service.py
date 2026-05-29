"""
认证服务模块
处理飞书OAuth登录、JWT令牌生成和验证
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.feishu_service import feishu_service
from app.core.security import create_access_token, decode_access_token
from app.config import Config


class AuthService:
    """认证服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_oauth_url(self, redirect_uri: str) -> str:
        """
        获取飞书OAuth授权URL
        """
        return feishu_service.get_oauth_url(redirect_uri)

    def login_with_feishu_code(self, code: str) -> Dict[str, Any]:
        """
        使用飞书OAuth code登录

        Args:
            code: 飞书OAuth授权码

        Returns:
            包含access_token和用户信息的字典

        Raises:
            Exception: 登录失败时抛出异常
        """
        # 1. 通过code获取飞书用户信息
        feishu_user = feishu_service.get_user_info_by_code(code)

        feishu_user_id = feishu_user.get("user_id") or feishu_user.get("open_id")
        feishu_union_id = feishu_user.get("union_id")
        feishu_open_id = feishu_user.get("open_id")
        name = feishu_user.get("name", "")
        en_name = feishu_user.get("en_name", "")
        email = feishu_user.get("email", "")
        mobile = feishu_user.get("mobile", "")
        avatar_url = feishu_user.get("avatar_url", "")

        if not feishu_user_id:
            raise Exception("无法获取飞书用户ID")

        # 2. 查找或创建本地用户
        user = self.db.query(User).filter(
            (User.feishu_user_id == feishu_user_id) |
            (User.feishu_union_id == feishu_union_id)
        ).first()

        if user:
            # 更新用户信息
            user.name = name or user.name
            user.en_name = en_name or user.en_name
            user.email = email or user.email
            user.phone = mobile or user.phone
            user.avatar_url = avatar_url or user.avatar_url
            if feishu_union_id:
                user.feishu_union_id = feishu_union_id
            if feishu_open_id:
                user.feishu_open_id = feishu_open_id
            self.db.commit()
            self.db.refresh(user)
        else:
            # 检查是否是超级管理员
            is_super_admin = feishu_user_id == Config.SUPER_ADMIN_FEISHU_USER_ID

            # 检查是否在管理员列表中
            is_admin = Config.is_admin(feishu_user_id)

            # 确定默认角色
            if is_super_admin:
                role = "super_admin"
            elif is_admin:
                role = "admin"
            else:
                role = "business"

            # 创建新用户
            user = User(
                name=name,
                en_name=en_name,
                feishu_user_id=feishu_user_id,
                feishu_union_id=feishu_union_id,
                feishu_open_id=feishu_open_id,
                email=email,
                phone=mobile,
                avatar_url=avatar_url,
                role=role,
                is_active=True
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        # 3. 检查用户是否有Web端访问权限
        from app.models.permission import ROLE_PERMISSIONS
        role_perms = ROLE_PERMISSIONS.get(user.role, {})
        if not role_perms.get("web_access", False):
            raise Exception(f"您的角色（{role_perms.get('name', user.role)}）没有Web端访问权限，请通过飞书客户端提交申请")

        # 4. 生成JWT访问令牌
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role}
        )

        # 5. 返回结果
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "en_name": user.en_name,
                "role": user.role,
                "email": user.email,
                "phone": user.phone,
                "avatar_url": user.avatar_url,
                "feishu_user_id": user.feishu_user_id,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        }

    def get_current_user(self, token: str) -> Optional[User]:
        """
        通过JWT令牌获取当前用户

        Args:
            token: JWT访问令牌

        Returns:
            用户对象，如果无效则返回None
        """
        payload = decode_access_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = self.db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None

        return user

    def refresh_token(self, token: str) -> Optional[str]:
        """
        刷新JWT令牌

        Args:
            token: 当前的JWT访问令牌

        Returns:
            新的访问令牌，如果无效则返回None
        """
        user = self.get_current_user(token)
        if not user:
            return None

        # 生成新的访问令牌
        new_token = create_access_token(
            data={"sub": str(user.id), "role": user.role}
        )

        return new_token
