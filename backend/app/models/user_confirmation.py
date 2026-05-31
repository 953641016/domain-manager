"""
待确认操作数据模型
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from enum import Enum
from app.core.database import Base
from app.models.permission import needs_super_admin_confirmation


class ConfirmationOperationType(str, Enum):
    """确认操作类型"""
    ADD_DOMAIN_SPEC = "add_domain_spec"           # 添加域名专员
    UPDATE_DOMAIN_SPEC = "update_domain_spec"     # 更新域名专员
    UPDATE_USER_ROLE = "update_user_role"         # 更新用户角色
    ADD_ADMIN = "add_admin"                       # 添加管理员
    REMOVE_ADMIN = "remove_admin"                 # 移除管理员
    CONFIG_ACCOUNTS = "config_accounts"           # 配置注册商账号（旧，保留兼容）
    PERMISSION_CHANGE = "permission_change"       # 权限变更
    # 域名账号管理（专员操作，需超管授权）
    ADD_REG_ACCOUNT = "add_reg_account"           # 新增注册账号
    UPDATE_REG_ACCOUNT = "update_reg_account"     # 修改注册账号
    DELETE_REG_ACCOUNT = "delete_reg_account"     # 删除注册账号
    ADD_DNS_ACCOUNT = "add_dns_account"           # 新增解析账号
    UPDATE_DNS_ACCOUNT = "update_dns_account"     # 修改解析账号
    DELETE_DNS_ACCOUNT = "delete_dns_account"     # 删除解析账号
    SET_DEFAULT_CONFIG = "set_default_config"     # 设置默认配置
    # 服务商管理（需超管授权）
    ADD_PROVIDER = "add_provider"                 # 新增服务商
    UPDATE_PROVIDER = "update_provider"           # 修改服务商
    DELETE_PROVIDER = "delete_provider"           # 删除服务商


class ConfirmationStatus(str, Enum):
    """确认状态"""
    PENDING = "pending"                          # 待确认
    APPROVED = "approved"                        # 已批准
    REJECTED = "rejected"                        # 已拒绝
    CANCELLED = "cancelled"                      # 已取消


class UserOperationConfirmation(Base):
    """用户操作待确认表"""
    __tablename__ = "user_operation_confirmations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 操作类型
    operation_type = Column(String(50), nullable=False, index=True)

    # 是否需要超级管理员确认
    requires_super_admin = Column(Boolean, nullable=False, default=False, index=True)

    # 发起者信息
    initiator_user_id = Column(Integer, nullable=False, index=True)
    initiator_name = Column(String(100), nullable=False)
    initiator_feishu_userid = Column(String(100), nullable=False)

    # 目标用户信息（待操作的用户）
    target_user_data = Column(JSON, nullable=False)

    # 操作详情（序列化的变更内容）
    operation_details = Column(JSON, nullable=False)

    # 状态
    status = Column(String(20), nullable=False, default=ConfirmationStatus.PENDING, index=True)

    # 确认者信息
    approver_user_id = Column(Integer, nullable=True)
    approver_name = Column(String(100), nullable=True)
    approver_feishu_userid = Column(String(100), nullable=True)

    # 飞书相关
    feishu_message_id = Column(String(100), nullable=True, index=True)
    feishu_chat_id = Column(String(100), nullable=True)

    # 时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # 备注
    reject_reason = Column(String(500), nullable=True)
    remark = Column(String(500), nullable=True)

    @property
    def is_pending(self):
        """是否待确认"""
        return self.status == ConfirmationStatus.PENDING

    @property
    def is_approved(self):
        """是否已批准"""
        return self.status == ConfirmationStatus.APPROVED

    @property
    def is_rejected(self):
        """是否已拒绝"""
        return self.status == ConfirmationStatus.REJECTED
