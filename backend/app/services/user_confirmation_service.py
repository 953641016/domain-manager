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

        # 执行实际操作
        try:
            self._execute_approved_action(confirmation)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("执行授权操作失败: %s", e)

        # 通知发起人
        self._notify_initiator(confirmation, approved=True)

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

        # 通知发起人
        self._notify_initiator(confirmation, approved=False)

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

    # ==================== 执行实际操作 ====================

    def _execute_approved_action(self, confirmation: UserOperationConfirmation) -> None:
        """审批通过后执行实际的账号操作"""
        from app.services.domain_service import DomainService
        from app.schemas.domain import (
            RegAccountCreate, RegAccountUpdate,
            DnsAccountCreate, DnsAccountUpdate,
        )

        op = confirmation.operation_type
        details = confirmation.operation_details or {}
        domain_svc = DomainService(self.db)

        if op == ConfirmationOperationType.ADD_REG_ACCOUNT:
            data = RegAccountCreate(**details["data"])
            domain_svc.create_reg_account(data, owner_id=details.get("owner_id"))

        elif op == ConfirmationOperationType.UPDATE_REG_ACCOUNT:
            data = RegAccountUpdate(**details["data"])
            domain_svc.update_reg_account(details["account_id"], data)

        elif op == ConfirmationOperationType.DELETE_REG_ACCOUNT:
            domain_svc.delete_reg_account(details["account_id"])

        elif op == ConfirmationOperationType.ADD_DNS_ACCOUNT:
            data = DnsAccountCreate(**details["data"])
            domain_svc.create_dns_account(data, owner_id=details.get("owner_id"))

        elif op == ConfirmationOperationType.UPDATE_DNS_ACCOUNT:
            data = DnsAccountUpdate(**details["data"])
            domain_svc.update_dns_account(details["account_id"], data)

        elif op == ConfirmationOperationType.DELETE_DNS_ACCOUNT:
            domain_svc.delete_dns_account(details["account_id"])

    def _notify_initiator(self, confirmation: UserOperationConfirmation, approved: bool) -> None:
        """通知发起人操作结果"""
        initiator = self.db.query(User).filter_by(id=confirmation.initiator_user_id).first()
        if not initiator:
            return
        receive_id = getattr(initiator, "feishu_open_id", None) or getattr(initiator, "feishu_user_id", None)
        if not receive_id:
            return
        receive_type = "open_id" if getattr(initiator, "feishu_open_id", None) else "user_id"
        desc = self.format_operation_description(confirmation)
        if approved:
            msg = f"✅ 您的操作已获超级管理员授权并执行\n{desc}"
        else:
            reason = confirmation.reject_reason or "未说明原因"
            msg = f"❌ 您的操作申请被拒绝\n{desc}\n拒绝原因：{reason}"
        try:
            from app.services.feishu_service import FeishuService
            FeishuService().send_text_message(receive_id, msg, receive_type)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("发送通知给发起人失败")

    def send_account_op_card_to_super_admin(
        self,
        confirmation: UserOperationConfirmation,
        api_key_masked: str = "",
    ) -> None:
        """向超级管理员发送账号操作授权飞书卡片"""
        super_admin = self.get_super_admin()
        if not super_admin:
            return
        receive_id = getattr(super_admin, "feishu_open_id", None) or getattr(super_admin, "feishu_user_id", None)
        if not receive_id:
            return
        receive_type = "open_id" if getattr(super_admin, "feishu_open_id", None) else "user_id"

        op_labels = {
            "add_reg_account": "新增注册账号",
            "update_reg_account": "修改注册账号",
            "delete_reg_account": "删除注册账号",
            "add_dns_account": "新增解析账号",
            "update_dns_account": "修改解析账号",
            "delete_dns_account": "删除解析账号",
            "set_default_config": "修改默认配置",
        }
        op_label = op_labels.get(confirmation.operation_type, confirmation.operation_type)
        details = confirmation.operation_details or {}
        account_name = details.get("data", {}).get("name") or details.get("account_name", "")

        lines = [
            f"**操作人：** {confirmation.initiator_name}",
            f"**操作类型：** {op_label}",
        ]
        if account_name:
            lines.append(f"**账号名称：** {account_name}")
        if api_key_masked:
            lines.append(f"**API Key：** {api_key_masked}")
        if details.get("account_id"):
            lines.append(f"**账号ID：** {details['account_id']}")

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "🔐 账号配置授权申请"},
                "template": "orange"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "\n".join(lines)}
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 授权执行"},
                            "type": "primary",
                            "value": {"action": "approve_account_op", "confirmation_id": str(confirmation.id)}
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                            "type": "danger",
                            "value": {"action": "reject_account_op", "confirmation_id": str(confirmation.id)}
                        }
                    ]
                }
            ]
        }

        try:
            from app.services.feishu_service import FeishuService
            result = FeishuService().send_card_message(receive_id, card, receive_type)
            msg_id = result.get("data", {}).get("message_id")
            if msg_id:
                self.update_feishu_message_id(confirmation.id, msg_id)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("发送授权卡片给超管失败")

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

        elif op_type == ConfirmationOperationType.ADD_REG_ACCOUNT:
            return f"{prefix}新增注册账号：{details.get('data', {}).get('name', '')}"

        elif op_type == ConfirmationOperationType.UPDATE_REG_ACCOUNT:
            return f"{prefix}修改注册账号 ID={details.get('account_id')}"

        elif op_type == ConfirmationOperationType.DELETE_REG_ACCOUNT:
            return f"{prefix}删除注册账号 ID={details.get('account_id')}"

        elif op_type == ConfirmationOperationType.ADD_DNS_ACCOUNT:
            return f"{prefix}新增解析账号：{details.get('data', {}).get('name', '')}"

        elif op_type == ConfirmationOperationType.UPDATE_DNS_ACCOUNT:
            return f"{prefix}修改解析账号 ID={details.get('account_id')}"

        elif op_type == ConfirmationOperationType.DELETE_DNS_ACCOUNT:
            return f"{prefix}删除解析账号 ID={details.get('account_id')}"

        elif op_type == ConfirmationOperationType.SET_DEFAULT_CONFIG:
            return f"{prefix}修改系统默认配置"

        return f"{prefix}未知操作：{op_type}"
