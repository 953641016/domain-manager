"""
域名数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Domain(Base):
    """
    域名表
    """
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 域名信息
    name = Column(String(255), nullable=False, unique=True, index=True, comment="域名名称")
    registrar_code = Column(String(50), nullable=True, comment="注册商代码")
    reg_account_id = Column(Integer, ForeignKey("reg_accounts.id"), nullable=True, comment="注册账号ID")
    dns_provider_code = Column(String(50), nullable=True, comment="DNS解析商代码")
    dns_account_id = Column(Integer, ForeignKey("dns_accounts.id"), nullable=True, comment="DNS账号ID")
    
    # 域名状态
    status = Column(String(20), nullable=False, default="active", comment="状态: active/expiring/expired/transferred")
    registration_date = Column(DateTime(timezone=True), nullable=True, comment="注册日期")
    expiration_date = Column(DateTime(timezone=True), nullable=True, comment="过期日期")
    auto_renew = Column(Boolean, default=False, comment="是否自动续费")
    
    # 联系人信息
    registrant_name = Column(String(100), nullable=True, comment="注册人姓名")
    registrant_email = Column(String(255), nullable=True, comment="注册人邮箱")
    registrant_phone = Column(String(50), nullable=True, comment="注册人电话")
    
    # DNS记录
    nameservers = Column(JSON, default=list, comment="NS服务器列表")
    
    # 元数据
    tags = Column(JSON, default=list, comment="标签")
    remark = Column(String(500), nullable=True, comment="备注")
    
    # 归属信息
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="所有者用户ID")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    last_synced_at = Column(DateTime(timezone=True), nullable=True, comment="最后同步时间")
    
    # 关系
    owner = relationship("User", foreign_keys=[owner_id])
    reg_account = relationship("RegAccount", foreign_keys=[reg_account_id])
    dns_account = relationship("DnsAccount", foreign_keys=[dns_account_id])

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "registrar_code": self.registrar_code,
            "reg_account_id": self.reg_account_id,
            "dns_provider_code": self.dns_provider_code,
            "dns_account_id": self.dns_account_id,
            "status": self.status,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "auto_renew": self.auto_renew,
            "registrant_name": self.registrant_name,
            "registrant_email": self.registrant_email,
            "registrant_phone": self.registrant_phone,
            "nameservers": self.nameservers,
            "tags": self.tags,
            "remark": self.remark,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
        }


class RegAccount(Base):
    """
    注册账号表
    """
    __tablename__ = "reg_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 账号信息
    name = Column(String(100), nullable=False, comment="账号名称")
    registrar_code = Column(String(50), nullable=False, comment="注册商代码")
    api_key = Column(String(500), nullable=True, comment="API Key（加密存储）")
    api_secret = Column(String(500), nullable=True, comment="API Secret（加密存储）")
    
    # 归属信息
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="所有者用户ID")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 备注
    remark = Column(String(500), nullable=True, comment="备注")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    owner = relationship("User", foreign_keys=[owner_id])
    domains = relationship("Domain", back_populates="reg_account", foreign_keys=[Domain.reg_account_id])

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "registrar_code": self.registrar_code,
            "owner_id": self.owner_id,
            "is_active": self.is_active,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DnsAccount(Base):
    """
    DNS解析账号表
    """
    __tablename__ = "dns_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 账号信息
    name = Column(String(100), nullable=False, comment="账号名称")
    provider_code = Column(String(50), nullable=False, comment="解析商代码")
    api_key = Column(String(500), nullable=True, comment="API Key（加密存储）")
    api_secret = Column(String(500), nullable=True, comment="API Secret（加密存储）")
    
    # 归属信息
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="所有者用户ID")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 备注
    remark = Column(String(500), nullable=True, comment="备注")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    owner = relationship("User", foreign_keys=[owner_id])
    domains = relationship("Domain", back_populates="dns_account", foreign_keys=[Domain.dns_account_id])

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "provider_code": self.provider_code,
            "owner_id": self.owner_id,
            "is_active": self.is_active,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
