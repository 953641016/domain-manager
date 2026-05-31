"""
系统配置 API
- GET  /config/defaults    获取系统默认配置（domain_spec / super_admin 可读）
- PUT  /config/defaults    更新系统默认配置（domain_spec / super_admin 可发起，需超管飞书确认）

权限策略与账号/服务商管理一致：
  can_view_providers  → GET
  can_manage_providers → PUT（走飞书确认，返回 pending_approval）
返回格式：单个对象 {default_registrar, default_dns_provider, ...}
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.dependencies import require_view_providers, require_manage_providers
from app.models.user import User
from app.models.system import SystemDefaults
from app.models.user_confirmation import ConfirmationOperationType
from app.services.user_confirmation_service import UserOperationConfirmationService

router = APIRouter(prefix="/config", tags=["系统配置"])


# ==================== Schema ====================

class DefaultsResponse(BaseModel):
    default_registrar: Optional[str] = None
    default_dns_provider: Optional[str] = None
    default_reg_account_id: Optional[int] = None
    default_dns_account_id: Optional[int] = None

    model_config = {"from_attributes": True}


class DefaultsUpdate(BaseModel):
    default_registrar: Optional[str] = None
    default_dns_provider: Optional[str] = None
    default_reg_account_id: Optional[int] = None
    default_dns_account_id: Optional[int] = None


# ==================== 工具 ====================

def _get_or_create_defaults(db: Session) -> SystemDefaults:
    """获取系统默认配置记录，不存在则创建（id=1 单行）"""
    row = db.query(SystemDefaults).filter_by(id=1).first()
    if not row:
        row = SystemDefaults(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


# ==================== 端点 ====================

@router.get("/defaults", response_model=DefaultsResponse)
def get_defaults(
    current_user: User = Depends(require_view_providers),
    db: Session = Depends(get_db),
):
    """获取系统默认配置（domain_spec / super_admin 可读）"""
    row = _get_or_create_defaults(db)
    return DefaultsResponse.model_validate(row)


@router.put("/defaults")
def update_defaults(
    data: DefaultsUpdate,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """
    更新系统默认配置（domain_spec / super_admin 均需超管飞书确认）
    返回 {status: "pending_approval", message: "..."}，HTTP 202
    """
    conf_svc = UserOperationConfirmationService(db)
    conf = conf_svc.create_confirmation(
        operation_type=ConfirmationOperationType.UPDATE_REG_ACCOUNT,  # 复用账号操作类型
        initiator_user_id=current_user.id,
        initiator_name=current_user.name,
        initiator_feishu_userid=getattr(current_user, "feishu_user_id", "") or "",
        target_user_data={"initiator_id": current_user.id, "initiator_role": current_user.role},
        operation_details={
            "type": "update_system_defaults",
            "changes": data.model_dump(exclude_none=True),
        },
        requires_super_admin=True,
    )
    conf_svc.send_account_op_card_to_super_admin(conf)
    return {"status": "pending_approval", "confirmation_id": conf.id,
            "message": "已向超级管理员发送授权申请，审批通过后默认配置将生效"}
