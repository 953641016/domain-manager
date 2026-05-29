"""
用户数据模型
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """
    用户表
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 用户信息
    name = Column(String(100), nullable=False, comment="用户姓名")
    email = Column(String(255), nullable=True, index=True, comment="邮箱")
    phone = Column(String(50), nullable=True, comment="手机号")
    department = Column(String(100), nullable=True, comment="部门")
    
    # 飞书身份
    feishu_userid = Column(String(100), nullable=False, unique=True, index=True, comment="飞书用户ID")
    feishu_unionid = Column(String(100), nullable=True, comment="飞书UnionID")
    feishu_openid = Column(String(100), nullable=True, comment="飞书OpenID")
    
    # 权限配置
    role = Column(String(20), nullable=False, default="business", comment="用户角色: business/domain_spec/admin")
    permissions = Column(JSON, default=list, comment="自定义权限列表")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 备注
    remark = Column(String(500), nullable=True, comment="备注")
