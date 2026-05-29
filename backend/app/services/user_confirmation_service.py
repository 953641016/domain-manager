"""
用户操作确认服务 - 支持超级管理员确认
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.user import User
from app.models.permission import (
    ROLE_PERMISSIONS,
    needs_super_admin_confirmation,
    SUPER_ADMIN_FEISHU_USERID
)
from app.models.user_confirmation import (
    UserOperationConfirmation,
    ConfirmationOperationType,
    ConfirmationStatus
)


class UserOperationConfirmationService:
    def __init__(self, db: Session):
        self.db = db

    def create_confirmation(
        self,
        operation_type: ConfirmationOperationType,
        initiator_user_id: int,
        initiator_name: str,
        initiator_feishu_userid: str,
        target_user_data: Dict[str, Any],
        operation_details: Dict[str, Any],
        requires_super_admin: bool = False,
        remark: Optional[str] = None
    ) -> UserOperationConfirmation:
        """
        创建待确认操作

        Args:
            operation_type: 操作类型
            initiator_user_id: 发起者用户ID
            initiator_name: 发起者姓名
            initiator_feishu_userid: 发起者飞书ID
            target_user_data: 目标用户数据
            operation_details: 操作详情
            requires_super_admin: 是否需要超级管理员确认
            remark: 备注
        """
        confirmation = UserOperationConfirmation(
            operation_type=operation_type,
            requires_super_admin=requires_super_admin,
            initiator_user_id=initiator_user_id,
            initiator_name=initiator_name,
            initiator_feishu_userid=initiator_feishu_userid,
            target_user_data=target_user_data,
            operation_details=operation_details,
            status=ConfirmationStatus.PENDING,
            remark=remark
        )

        self.db.add(confirmation)
        self.db.commit()
        self.db.refresh(confirmation)

        return confirmation

    def get_confirmation(self, confirmation_id: int) -> Optional[UserOperationConfirmation]:
        """获取待确认操作"""
        return self.db.query(UserOperationConfirmation).filter_by(id=confirmation_id).first()

    def get_confirmation_by_feishu_message(
        self, feishu_message_id: str
    ) -> Optional[UserOperationConfirmation]:
        """通过飞书消息ID获取待确认操作"""
        return self.db.query(UserOperationConfirmation).filter_by(
            feishu_message_id=feishu_message_id
        ).first()

    def get_pending_confirmations(
        self,
        initiator_user_id: Optional[int] = None,
        operation_type: Optional[str] = None
    ) -> List[UserOperationConfirmation]:
        """
        获取待确认的操作列表

        Args:
            initiator_user_id: 发起者用户ID（可选，只查看自己发起的）
            operation_type: 操作类型（可选）
        """
        query = self.db.query(UserOperationConfirmation).filter_by(
            status=ConfirmationStatus.PENDING
        )

        if initiator_user_id:
            query = query.filter_by(initiator_user_id=initiator_user_id)

        if operation_type:
            query = query.filter_by(operation_type=operation_type)

        return query.order_by(UserOperationConfirmation.created_at.desc()).all()

    def get_confirmations(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        initiator_user_id: Optional[int] = None
    ) -> List[UserOperationConfirmation]:
        """获取操作记录列表"""
        query = self.db.query(UserOperationConfirmation)

        if status:
            query = query.filter_by(status=status)

        if initiator_user_id:
            query = query.filter_by(initiator_user_id=initiator_user_id)

        return query.order_by(UserOperationConfirmation.created_at.desc()).offset(skip).limit(limit).all()

    def get_confirmations_count(
        self,
        status: Optional[str] = None,
        initiator_user_id: Optional[int] = None
    ) -> int:
        """获取操作记录数量"""
        query = self.db.query(UserOperationConfirmation)

        if status:
            query = query.filter_by(status=status)

        if initiator_user_id:
            query = query.filter_by(initiator_user_id=initiator_user_id)

        return query.count()

    def approve_confirmation(
        self,
        confirmation_id: int,
        approver_user_id: int,
        approver_name: str,
        approver_feishu_userid: str
    ) -> Optional[UserOperationConfirmation]:
        """
        批准操作

        Args:
            confirmation_id: 确认操作ID
            approver_user_id: 批准者用户ID
            approver_name: 批准者姓名
            approver_feishu_userid: 批准者飞书ID
        """
        confirmation = self.get_confirmation(confirmation_id)

        if not confirmation or not confirmation.is_pending:
            return None

        # 检查是否需要超级管理员确认
        if confirmation.requires_super_admin:
            # 获取超级管理员用户
            super_admin = self.get_super_admin()
            if not super_admin or super_admin.feishu_userid != approver_feishu_userid:
                # 不是超级管理员，拒绝批准
                return None

        # 检查是否是自己批准自己发起的操作
        if confirmation.initiator_user_id == approver_user_id:
            return None

        # 更新状态
        confirmation.status = ConfirmationStatus.APPROVED
        confirmation.approver_user_id = approver_user_id
        confirmation.approver_name = approver_name
        confirmation.approver_feishu_userid = approver_feishu_userid
        confirmation.confirmed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(confirmation)

        return confirmation

    def reject_confirmation(
        self,
        confirmation_id: int,
        approver_user_id: int,
        approver_name: str,
        approver_feishu_userid: str,
        reject_reason: Optional[str] = None
    ) -> Optional[UserOperationConfirmation]:
        """
        拒绝操作

        Args:
            confirmation_id: 确认操作ID
            approver_user_id: 拒绝者用户ID
            approver_name: 拒绝者姓名
            approver_feishu_userid: 拒绝者飞书ID
            reject_reason: 拒绝原因
        """
        confirmation = self.get_confirmation(confirmation_id)

        if not confirmation or not confirmation.is_pending:
            return None

        # 检查是否需要超级管理员确认
        if confirmation.requires_super_admin:
            # 获取超级管理员用户
            super_admin = self.get_super_admin()
            if not super_admin or super_admin.feishu_userid != approver_feishu_userid:
                # 不是超级管理员，拒绝批准
                return None

        # 检查是否是自己拒绝自己发起的操作
        if confirmation.initiator_user_id == approver_user_id:
            return None

        # 更新状态
        confirmation.status = ConfirmationStatus.REJECTED
        confirmation.approver_user_id = approver_user_id
        confirmation.approver_name = approver_name
        confirmation.approver_feishu_userid = approver_feishu_userid
        confirmation.reject_reason = reject_reason
        confirmation.confirmed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(confirmation)

        return confirmation

    def cancel_confirmation(
        self,
        confirmation_id: int,
        initiator_user_id: int
    ) -> Optional[UserOperationConfirmation]:
        """
        取消待确认操作（只能由发起者取消）
        """
        confirmation = self.get_confirmation(confirmation_id)

        if not confirmation or not confirmation.is_pending:
            return None

        if confirmation.initiator_user_id != initiator_user_id:
            return None

        confirmation.status = ConfirmationStatus.CANCELLED
        self.db.commit()
        self.db.refresh(confirmation)

        return confirmation

    def update_feishu_message_id(
        self,
        confirmation_id: int,
        feishu_message_id: str,
        feishu_chat_id: Optional[str] = None
    ) -> Optional[UserOperationConfirmation]:
        """更新飞书消息ID"""
        confirmation = self.get_confirmation(confirmation_id)

        if not confirmation:
            return None

        confirmation.feishu_message_id = feishu_message_id
        confirmation.feishu_chat_id = feishu_chat_id
        self.db.commit()
        self.db.refresh(confirmation)

        return confirmation

    def get_super_admin(self) -> Optional[User]:
        """获取超级管理员（唯一）"""
        return self.db.query(User).filter_by(
            role="super_admin",
            is_active=True
        ).first()

    def get_admin_users(self, exclude_user_id: Optional[int] = None) -> List[User]:
        """获取所有管理员用户（用于发送确认消息）"""
        query = self.db.query(User).filter(
            User.role.in_(["admin", "super_admin"]),
            User.is_active == True
        )

        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)

        return query.all()

    def get_user_by_feishu_id(self, feishu_userid: str) -> Optional[User]:
        """通过飞书用户ID获取用户"""
        return self.db.query(User).filter_by(
            feishu_userid=feishu_userid,
            is_active=True
        ).first()

    def format_operation_description(self, confirmation: UserOperationConfirmation) -> str:
        """格式化操作描述文本（用于显示）"""
        op_type = confirmation.operation_type
        target_data = confirmation.target_user_data
        details = confirmation.operation_details

        prefix = ""
        if confirmation.requires_super_admin:
            prefix = "【需超级管理员确认】"

        if op_type == ConfirmationOperationType.ADD_DOMAIN_SPEC:
            return f"{prefix}添加域名专员：{target_data.get('name')} ({target_data.get('feishu_userid')})"

        elif op_type == ConfirmationOperationType.UPDATE_DOMAIN_SPEC:
            changes = []
            if 'name' in details:
                changes.append(f"姓名: {details['name']}")
            if 'department' in details:
                changes.append(f"部门: {details['department']}")
            return f"{prefix}更新域名专员：{target_data.get('name')} - {'; '.join(changes)}"

        elif op_type == ConfirmationOperationType.UPDATE_USER_ROLE:
            old_role = details.get('old_role', 'unknown')
            new_role = details.get('new_role', 'unknown')
            old_role_name = ROLE_PERMISSIONS.get(old_role, {}).get('name', old_role)
            new_role_name = ROLE_PERMISSIONS.get(new_role, {}).get('name', new_role)
            return f"{prefix}变更用户角色：{target_data.get('name')} - {old_role_name} → {new_role_name}"

        elif op_type == ConfirmationOperationType.ADD_ADMIN:
            return f"{prefix}添加系统管理员：{target_data.get('name')} ({target_data.get('feishu_userid')})"

        elif op_type == ConfirmationOperationType.REMOVE_ADMIN:
            return f"{prefix}移除系统管理员：{target_data.get('name')}"

        elif op_type == ConfirmationOperationType.CONFIG_ACCOUNTS:
            return f"{prefix}配置注册商账号：{details.get('account_name')}"

        elif op_type == ConfirmationOperationType.PERMISSION_CHANGE:
            return f"{prefix}权限变更：{target_data.get('name')}"

        return f"{prefix}未知操作：{op_type}"
