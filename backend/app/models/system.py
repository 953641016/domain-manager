"""
系统配置模型
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class SystemDefaults(Base):
    """
    系统默认配置（单行表，只存一条记录 id=1）
    保存新建域名时的默认注册商/DNS服务商/账号偏好。
    修改需 super_admin 权限，无需飞书确认（属于操作偏好，非账号凭据变更）。
    """
    __tablename__ = "system_defaults"

    id = Column(Integer, primary_key=True, default=1)
    default_registrar     = Column(String(50),  nullable=True, comment="默认注册商 code")
    default_dns_provider  = Column(String(50),  nullable=True, comment="默认 DNS 服务商 code")
    default_reg_account_id = Column(Integer,    nullable=True, comment="默认注册账号 ID")
    default_dns_account_id = Column(Integer,    nullable=True, comment="默认 DNS 账号 ID")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), comment="最后修改时间")
