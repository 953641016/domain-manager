"""
审计日志数据模型
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from sqlalchemy.sql import func
from app.core.database import Base


class AuditLog(Base):
    """
    审计日志表
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 用户信息
    user_id = Column(Integer, nullable=True, index=True, comment="用户ID")
    user_name = Column(String(100), nullable=True, comment="用户姓名")
    
    # 操作信息
    action = Column(String(50), nullable=False, index=True, comment="操作类型")
    resource_type = Column(String(50), nullable=False, index=True, comment="资源类型")
    resource_id = Column(String(100), nullable=True, comment="资源ID")
    resource_name = Column(String(255), nullable=True, comment="资源名称")
    
    # 请求信息
    method = Column(String(10), nullable=True, comment="HTTP方法")
    path = Column(String(500), nullable=True, comment="请求路径")
    ip_address = Column(String(50), nullable=True, comment="IP地址")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    
    # 操作详情
    before_state = Column(JSON, nullable=True, comment="变更前状态")
    after_state = Column(JSON, nullable=True, comment="变更后状态")
    
    # 结果
    status = Column(String(20), nullable=False, default="success", comment="状态: success/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="创建时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "method": self.method,
            "path": self.path,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
