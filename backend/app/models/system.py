"""
系统配置模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class SystemDefaults(Base):
    """
    用户个人默认配置（per-user，每人一行）

    - domain_spec：只能读写自己的行
    - super_admin：可读写所有人的行（含替他人设置）
    - 修改需超管飞书确认（SET_DEFAULT_CONFIG）

    迁移说明：v1.3.3 由单行全局表改为 per-user 表，
    init_db.py 会在首次运行时通过 ALTER TABLE 添加 user_id 列并清理旧全局行。
    """
    __tablename__ = "system_defaults"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 归属用户（unique：每人最多一行）
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,   # 迁移过渡期允许 NULL；旧全局行将在 init_db 中清理
        index=True,
        comment="归属用户 ID（per-user 设计，每人一行）",
    )

    default_registrar      = Column(String(50),  nullable=True, comment="默认注册商 code")
    default_dns_provider   = Column(String(50),  nullable=True, comment="默认 DNS 服务商 code")
    default_reg_account_id = Column(Integer,     nullable=True, comment="默认注册账号 ID")
    default_dns_account_id = Column(Integer,     nullable=True, comment="默认 DNS 账号 ID")

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="最后修改时间",
    )

    # 关系
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_system_defaults_user_id"),
    )
