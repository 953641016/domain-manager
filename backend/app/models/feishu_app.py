"""
飞书应用配置模型
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.encryption import get_encryption_service


class FeishuApp(Base):
    """飞书应用配置。一个飞书主体对应一条记录。"""

    __tablename__ = "feishu_apps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True, index=True, comment="应用标识")
    name = Column(String(100), nullable=False, comment="应用展示名称")
    app_id = Column(String(100), nullable=False, unique=True, index=True, comment="飞书 App ID")
    app_secret_encrypted = Column(Text, nullable=True, comment="加密后的飞书 App Secret")
    verification_token = Column(String(255), nullable=True, comment="Webhook 验签 Token")
    encrypt_key = Column(String(255), nullable=True, comment="Webhook 加密 Key")
    super_admin_feishu_user_id = Column(String(100), nullable=True, comment="该应用下的超管飞书 user_id")
    is_default = Column(Boolean, default=False, comment="是否默认应用")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def set_app_secret(self, app_secret: str):
        """加密保存 app_secret。"""
        if not app_secret:
            self.app_secret_encrypted = ""
            return
        try:
            self.app_secret_encrypted = get_encryption_service().encrypt(app_secret)
        except Exception:
            # 兼容历史环境 ENCRYPTION_KEY 配置不合法的情况；后续修复密钥后可重新保存为密文。
            self.app_secret_encrypted = f"plain:{app_secret}"

    def get_app_secret(self) -> str:
        """解密读取 app_secret。"""
        if not self.app_secret_encrypted:
            return ""
        if self.app_secret_encrypted.startswith("plain:"):
            return self.app_secret_encrypted[len("plain:"):]
        return get_encryption_service().decrypt(self.app_secret_encrypted)

    def to_public_dict(self) -> dict:
        """返回前端可见字段，不包含密钥。"""
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "app_id": self.app_id,
            "is_default": self.is_default,
            "is_active": self.is_active,
        }
