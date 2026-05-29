"""
申请数据模型
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Request(Base):
    """
    申请表
    """
    __tablename__ = "requests"

    id = Column(String(36), primary_key=True, comment="申请ID (UUID)")
    
    # 申请信息
    type = Column(String(20), nullable=False, comment="申请类型: domain_register/dns_record")
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="申请人ID")
    requester_name = Column(String(100), nullable=False, comment="申请人姓名")
    
    # 域名信息
    domain_name = Column(String(255), nullable=False, index=True, comment="域名")
    
    # 申请内容
    request_data = Column(JSON, nullable=True, comment="申请数据（JSON）")
    
    # 审批配置
    selected_registrar_code = Column(String(50), nullable=True, comment="选择的注册商代码")
    selected_reg_account_id = Column(Integer, ForeignKey("reg_accounts.id"), nullable=True, comment="选择的注册账号ID")
    selected_dns_provider_code = Column(String(50), nullable=True, comment="选择的DNS解析商代码")
    selected_dns_account_id = Column(Integer, ForeignKey("dns_accounts.id"), nullable=True, comment="选择的DNS账号ID")
    
    # 状态
    status = Column(String(20), nullable=False, default="pending", comment="状态: pending/approved/rejected/completed/failed")
    
    # 审批信息
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人ID")
    approver_name = Column(String(100), nullable=True, comment="审批人姓名")
    approved_at = Column(DateTime(timezone=True), nullable=True, comment="审批时间")
    reject_reason = Column(Text, nullable=True, comment="拒绝原因")
    
    # 执行结果
    execution_result = Column(JSON, nullable=True, comment="执行结果")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 飞书集成
    conversation_id = Column(String(255), nullable=True, comment="飞书会话ID")
    source = Column(String(20), nullable=True, comment="来源: feishu_bot/feishu_table/web")
    feishu_message_id = Column(String(255), nullable=True, comment="飞书消息ID")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    requester = relationship("User", foreign_keys=[requester_id])
    approver = relationship("User", foreign_keys=[approver_id])
    reg_account = relationship("RegAccount", foreign_keys=[selected_reg_account_id])
    dns_account = relationship("DnsAccount", foreign_keys=[selected_dns_account_id])

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "domain_name": self.domain_name,
            "request_data": self.request_data,
            "selected_registrar_code": self.selected_registrar_code,
            "selected_reg_account_id": self.selected_reg_account_id,
            "selected_dns_provider_code": self.selected_dns_provider_code,
            "selected_dns_account_id": self.selected_dns_account_id,
            "status": self.status,
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "reject_reason": self.reject_reason,
            "execution_result": self.execution_result,
            "error_message": self.error_message,
            "conversation_id": self.conversation_id,
            "source": self.source,
            "feishu_message_id": self.feishu_message_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
