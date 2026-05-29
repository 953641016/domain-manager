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
    en_name = Column(String(100), nullable=True, comment="英文名")
    email = Column(String(255), nullable=True, index=True, comment="邮箱")
    phone = Column(String(50), nullable=True, comment="手机号")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    department = Column(String(100), nullable=True, comment="部门")
    
    # 飞书身份
    feishu_user_id = Column(String(100), nullable=True, unique=True, index=True, comment="飞书用户ID")
    feishu_union_id = Column(String(100), nullable=True, index=True, comment="飞书UnionID")
    feishu_open_id = Column(String(100), nullable=True, comment="飞书OpenID")
    
    # 权限配置
    role = Column(String(20), nullable=False, default="business", comment="用户角色: business/domain_spec/admin/super_admin")
    permissions = Column(JSON, default=list, comment="自定义权限列表")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 备注
    remark = Column(String(500), nullable=True, comment="备注")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "en_name": self.en_name,
            "email": self.email,
            "phone": self.phone,
            "avatar_url": self.avatar_url,
            "department": self.department,
            "feishu_user_id": self.feishu_user_id,
            "feishu_union_id": self.feishu_union_id,
            "role": self.role,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "remark": self.remark,
        }
