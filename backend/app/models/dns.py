"""
DNS记录数据模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DnsRecord(Base):
    """
    DNS记录表
    """
    __tablename__ = "dns_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 域名关联
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False, index=True, comment="域名ID")
    
    # 记录信息
    record_type = Column(String(10), nullable=False, comment="记录类型: A/AAAA/CNAME/MX/TXT/SRV/NS")
    host = Column(String(255), nullable=False, comment="主机记录")
    value = Column(String(1000), nullable=False, comment="记录值")
    ttl = Column(Integer, default=300, comment="TTL（秒）")
    priority = Column(Integer, nullable=True, comment="优先级（MX/SRV）")
    weight = Column(Integer, nullable=True, comment="权重（SRV）")
    port = Column(Integer, nullable=True, comment="端口（SRV）")
    
    # 状态
    status = Column(String(20), nullable=False, default="active", comment="状态: active/pending/deleted/error")
    sync_status = Column(String(20), nullable=True, comment="同步状态: synced/pending/error")
    external_id = Column(String(100), nullable=True, comment="外部系统ID（如Cloudflare record ID）")
    
    # 元数据
    remark = Column(String(500), nullable=True, comment="备注")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    last_synced_at = Column(DateTime(timezone=True), nullable=True, comment="最后同步时间")
    
    # 关系
    domain = relationship("Domain", foreign_keys=[domain_id])

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "domain_id": self.domain_id,
            "record_type": self.record_type,
            "host": self.host,
            "value": self.value,
            "ttl": self.ttl,
            "priority": self.priority,
            "weight": self.weight,
            "port": self.port,
            "status": self.status,
            "sync_status": self.sync_status,
            "external_id": self.external_id,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
        }
