"""
飞书多维表格绑定配置
记录每个用户在各 section 下绑定的 Bitable app_token + table_id
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class FeishuBitableConfig(Base):
    __tablename__ = "feishu_bitable_configs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    section    = Column(String(100), nullable=False, comment="申请类型，如 vercel/clerk/domain_register")
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, comment="绑定人")
    app_token  = Column(String(200), nullable=False, comment="Bitable 文档 token")
    table_id   = Column(String(200), nullable=False, comment="具体表格 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("section", "user_id", name="uq_section_user"),
    )
