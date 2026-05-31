"""
用户操作确认服务 - 支持超级管理员确认
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
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

CONFIRMATION_EXPIRE_HOURS = 24  # 确认有效期


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
            execution_status="pending",
            source=remark or "web",           # 来源（调用方可通过 remark 传 source）
            expires_at=datetime.utcnow() + timedelta(hours=CONFIRMATION_EXPIRE_HOURS),
            remark=None
        )

        self.db.add(confirmation)
        self.db.commit()
        self.db.refresh(confirmation)

        # 审计留痕 #1：申请已提交
        self._audit(
            action=f"{operation_type}_requested",
            confirmation=confirmation,
            user_id=initiator_user_id,
            user_name=initiator_name,
            status="success",
            after_state={"operation_type": operation_type, "source": confirmation.source},
        )

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

        # 幂等检查：已处理的确认不能重复执行（防飞书重投 / 手抖双击）
        if not confirmation.is_pending:
            return None

        # 已过期则自动作废
        if confirmation.expires_at and datetime.utcnow() > confirmation.expires_at.replace(tzinfo=None):
            confirmation.status = ConfirmationStatus.CANCELLED
            confirmation.reject_reason = "确认已超时（24小时），自动作废"
            self.db.commit()
            return None

        # 审批人必须是超级管理员
        super_admin = self.get_super_admin()
        if not super_admin or super_admin.id != approver_user_id:
            return None

        # 更新状态
        confirmation.status = ConfirmationStatus.APPROVED
        confirmation.approver_user_id = approver_user_id
        confirmation.approver_name = approver_name
        confirmation.approver_feishu_userid = approver_feishu_userid
        confirmation.confirmed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(confirmation)

        # 审计留痕 #2：已授权
        self._audit(
            action=f"{confirmation.operation_type}_approved",
            confirmation=confirmation,
            user_id=approver_user_id,
            user_name=approver_name,
            status="success",
            after_state={"approver": approver_name, "confirmed_via": "feishu_client"},
        )

        # 执行实际操作并追踪结果
        exec_error = None
        try:
            self._execute_approved_action(confirmation)
            confirmation.execution_status = "success"
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("执行授权操作失败: %s", e)
            exec_error = str(e)
            confirmation.execution_status = "failed"
        self.db.commit()

        # 审计留痕 #3：执行结果
        self._audit(
            action=f"{confirmation.operation_type}_executed",
            confirmation=confirmation,
            user_id=approver_user_id,
            user_name=approver_name,
            status="success" if not exec_error else "failed",
            error_message=exec_error,
        )

        # 通知发起人（如实反映执行结果）
        self._notify_initiator(confirmation, approved=True, exec_error=exec_error)

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

        # 幂等：已处理不重复
        if not confirmation.is_pending:
            return None

        super_admin = self.get_super_admin()
        if not super_admin or super_admin.id != approver_user_id:
            return None

        confirmation.status = ConfirmationStatus.REJECTED
        confirmation.execution_status = "failed"
        confirmation.approver_user_id = approver_user_id
        confirmation.approver_name = approver_name
        confirmation.approver_feishu_userid = approver_feishu_userid
        confirmation.reject_reason = reject_reason
        confirmation.confirmed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(confirmation)

        # 审计留痕 #2：已拒绝
        self._audit(
            action=f"{confirmation.operation_type}_rejected",
            confirmation=confirmation,
            user_id=approver_user_id,
            user_name=approver_name,
            status="failed",
            error_message=reject_reason,
            after_state={"reason": reject_reason, "confirmed_via": "feishu_client"},
        )

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
        """
        获取超级管理员。
        优先返回 .env 中 SUPER_ADMIN_FEISHU_USER_ID 指定的用户；
        若未配置或未找到，则返回任意有飞书ID的 super_admin。
        """
        from app.config import Config
        feishu_id = Config.SUPER_ADMIN_FEISHU_USER_ID
        if feishu_id:
            user = self.db.query(User).filter(
                User.feishu_user_id == feishu_id,
                User.is_active == True,
            ).first()
            if user:
                return user
        # 兜底：取有飞书ID的活跃超管
        return self.db.query(User).filter(
            User.role == "super_admin",
            User.is_active == True,
            User.feishu_user_id != None,
            User.feishu_user_id != "",
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
        """通过飞书用户ID获取用户（open_id / user_id 均可）"""
        return self.db.query(User).filter(
            (User.feishu_user_id == feishu_userid) | (User.feishu_open_id == feishu_userid),
            User.is_active == True,
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

        # 用户增改删：以 details["action"] 为准（operation_type 仅用于卡片归类）
        if details.get("action") in ("create_user", "update_user", "deactivate_user", "delete_user", "activate_user"):
            self._execute_user_op(details)
            return

        domain_svc = DomainService(self.db)

        # 账号操作：写库时 domain_service 会自动加密 API Key
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

        elif op == ConfirmationOperationType.ADD_PROVIDER:
            self._execute_provider_op("add", details)
        elif op == ConfirmationOperationType.UPDATE_PROVIDER:
            self._execute_provider_op("update", details)
        elif op == ConfirmationOperationType.DELETE_PROVIDER:
            self._execute_provider_op("delete", details)

    def _execute_provider_op(self, action: str, details: dict) -> None:
        """执行服务商增改删"""
        from app.models.domain import Registrar, DnsProvider
        provider_type = details.get("provider_type")
        model_cls = Registrar if provider_type == "registrar" else DnsProvider

        if action == "add":
            data = details.get("data", {})
            obj = model_cls(**data)
            self.db.add(obj)
            self.db.commit()
        elif action == "update":
            obj = self.db.query(model_cls).filter_by(id=details["id"]).first()
            if obj:
                for k, v in details.get("data", {}).items():
                    setattr(obj, k, v)
                self.db.commit()
        elif action == "delete":
            obj = self.db.query(model_cls).filter_by(id=details["id"]).first()
            if obj:
                self.db.delete(obj)
                self.db.commit()

    def _execute_user_op(self, details: dict) -> None:
        """执行用户增改删（审批通过后）"""
        from app.services.user_service import UserService
        from app.schemas.user import UserCreate, UserUpdate

        user_svc = UserService(self.db)
        action = details.get("action")

        if action == "create_user":
            data = UserCreate(**details["user_data"])
            user_svc.create_user(data)

        elif action == "update_user":
            data = UserUpdate(**details.get("changes", {}))
            user_svc.update_user(details["user_id"], data)

        elif action == "deactivate_user":
            # 软禁用：is_active=False，可通过 activate 恢复
            user_svc.delete_user(details["user_id"])

        elif action == "delete_user":
            # 硬删除：从数据库中移除用户记录
            user_svc.hard_delete_user(details["user_id"])

        elif action == "activate_user":
            user_svc.activate_user(details["user_id"])

    def _notify_initiator(
        self,
        confirmation: UserOperationConfirmation,
        approved: bool,
        exec_error: Optional[str] = None,
    ) -> None:
        """通知发起人操作结果（如实反映执行状态）"""
        initiator = self.db.query(User).filter_by(id=confirmation.initiator_user_id).first()
        if not initiator:
            return
        receive_id = getattr(initiator, "feishu_open_id", None) or getattr(initiator, "feishu_user_id", None)
        if not receive_id:
            return
        receive_type = "open_id" if getattr(initiator, "feishu_open_id", None) else "user_id"
        desc = self.format_operation_description(confirmation)
        # 移除对用户无意义的内部标记前缀
        desc = desc.replace("【需超级管理员确认】", "").strip()
        if not approved:
            reason = confirmation.reject_reason or "未说明原因"
            msg = f"❌ 操作申请被拒绝\n操作：{desc}\n原因：{reason}"
        elif exec_error:
            friendly = self._friendly_error(exec_error)
            msg = f"⚠️ 操作执行失败\n操作：{desc}\n原因：{friendly}\n如有疑问请联系超级管理员"
        else:
            msg = f"✅ 操作执行成功\n操作：{desc}"
        try:
            from app.services.feishu_service import FeishuService
            FeishuService().send_text_message(receive_id, msg, receive_type)
        except Exception:
            import logging
            logging.getLogger(__name__).warning("发送通知给发起人失败")

    def _audit(
        self,
        action: str,
        confirmation: UserOperationConfirmation,
        user_id: Optional[int],
        user_name: Optional[str],
        status: str = "success",
        error_message: Optional[str] = None,
        after_state: Optional[dict] = None,
    ) -> None:
        """写审计日志（三时机共用）"""
        try:
            from app.services.audit_service import AuditService
            AuditService(self.db).log(
                action=action,
                resource_type="confirmation",
                resource_id=str(confirmation.id),
                resource_name=self.format_operation_description(confirmation),
                user_id=user_id,
                user_name=user_name,
                after_state=after_state or {},
                status=status,
                error_message=error_message,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).warning("写审计日志失败")

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

        details = confirmation.operation_details or {}
        action = details.get("action", "")
        op_type = confirmation.operation_type

        # 操作事项（动词短语）
        事项_map = {
            "create_user":     "创建用户",
            "update_user":     "修改用户",
            "deactivate_user": "禁用用户",
            "delete_user":     "删除用户",
            "activate_user":   "激活用户",
            "add_reg_account":    "新增注册账号",
            "update_reg_account": "修改注册账号",
            "delete_reg_account": "删除注册账号",
            "add_dns_account":    "新增解析账号",
            "update_dns_account": "修改解析账号",
            "delete_dns_account": "删除解析账号",
            "set_default_config": "修改默认配置",
            "add_provider":    "新增服务商",
            "update_provider": "修改服务商",
            "delete_provider": "删除服务商",
        }
        op_event = 事项_map.get(action) or 事项_map.get(op_type, op_type)

        # 操作对象（目标 + 补充说明）
        if action == "create_user":
            ud = details.get("user_data", {})
            op_target = f"{ud.get('name', '')}（{self._role_name(ud.get('role', ''))}）"
        elif action in ("deactivate_user", "delete_user", "activate_user", "update_user"):
            name = details.get("target_name", "")
            role = self._role_name(details.get("target_role", ""))
            suffix = {
                "deactivate_user": "，禁用后可恢复",
                "delete_user":     "，⚠️ 硬删除不可恢复",
                "activate_user":   "",
                "update_user":     "",
            }.get(action, "")
            changes = details.get("changes", {})
            change_str = "；".join(
                f"{k}→{v}" for k, v in changes.items()
            ) if changes and action == "update_user" else ""
            op_target = f"{name}（{role}{suffix}）" + (f"\n变更：{change_str}" if change_str else "")
        else:
            acc_name = details.get("data", {}).get("name") or details.get("account_name", "")
            op_target = acc_name or "—"

        lines = [
            f"申请人：{confirmation.initiator_name}",
            f"操作事项：{op_event}",
            f"操作对象：{op_target}",
        ]
        if api_key_masked:
            lines.append(f"API Key：{api_key_masked}")

        # 卡片标题
        if action in ("create_user", "update_user", "deactivate_user", "delete_user", "activate_user"):
            card_title = "👤 用户管理授权申请"
        elif op_type in ("add_provider", "update_provider", "delete_provider"):
            card_title = "🏷️ 服务商配置授权申请"
        else:
            card_title = "🔐 账号配置授权申请"

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": card_title},
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

    @staticmethod
    def _role_name(role: Optional[str]) -> str:
        if not role:
            return "未指定"
        return ROLE_PERMISSIONS.get(role, {}).get("name", role)

    @staticmethod
    def _friendly_error(error: str) -> str:
        """
        将技术性异常信息转换为用户友好的中文提示。
        规范：用户侧通知消息不得暴露原始 ID、SQL 错误或堆栈信息。
        """
        e = str(error).lower()
        if "用户已存在" in error or "already exists" in e or ("unique" in e and "user" in e):
            return "该用户已存在，可能是重复提交申请，无需再次处理"
        if "feishu" in e and ("id" in e or "userid" in e):
            return "飞书账号已绑定其他用户，请联系管理员确认"
        if "not found" in e or "不存在" in error:
            return "目标数据不存在或已被删除"
        if "permission" in e or "权限" in error:
            return "权限不足，无法执行此操作"
        if "timeout" in e or "超时" in error:
            return "操作超时，请稍后重试"
        return "系统执行异常，请联系超级管理员"

    def _format_user_op(self, prefix: str, action: str, details: dict) -> str:
        """渲染用户增改删的描述文本"""
        if action == "create_user":
            ud = details.get("user_data", {})
            return f"{prefix}新增用户：{ud.get('name')}（{self._role_name(ud.get('role'))}）"

        if action == "update_user":
            changes = details.get("changes", {}) or {}
            parts = []
            if "name" in changes:
                parts.append(f"姓名→{changes['name']}")
            if "role" in changes:
                parts.append(f"角色→{self._role_name(changes['role'])}")
            if "department" in changes:
                parts.append(f"部门→{changes['department']}")
            if "assigned_specialist_id" in changes:
                parts.append(f"归属专员ID→{changes['assigned_specialist_id']}")
            if "is_active" in changes:
                parts.append(f"启用→{changes['is_active']}")
            summary = "；".join(parts) if parts else "（无可显示字段）"
            return f"{prefix}更新用户：{details.get('target_name')} - {summary}"

        if action == "deactivate_user":
            return (
                f"{prefix}禁用用户：{details.get('target_name')}"
                f"（{self._role_name(details.get('target_role'))}，禁用后可恢复）"
            )

        if action == "delete_user":
            return (
                f"{prefix}删除用户：{details.get('target_name')}"
                f"（{self._role_name(details.get('target_role'))}，⚠️ 硬删除不可恢复）"
            )

        if action == "activate_user":
            return f"{prefix}激活用户：{details.get('target_name')}"

        return f"{prefix}用户操作：{action}"

    def format_operation_description(self, confirmation: UserOperationConfirmation) -> str:
        """格式化操作描述文本（用于显示）"""
        op_type = confirmation.operation_type
        target_data = confirmation.target_user_data
        details = confirmation.operation_details

        prefix = ""
        if confirmation.requires_super_admin:
            prefix = "【需超级管理员确认】"

        # 用户增改删：统一以 details["action"] 渲染（目标信息存于 operation_details）
        action = (details or {}).get("action")
        if action in ("create_user", "update_user", "deactivate_user", "delete_user", "activate_user"):
            return self._format_user_op(prefix, action, details)

        if op_type == ConfirmationOperationType.ADD_DOMAIN_SPEC:
            return f"{prefix}添加用户：{target_data.get('name')}"

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
            return f"{prefix}添加系统管理员：{target_data.get('name')}"

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
