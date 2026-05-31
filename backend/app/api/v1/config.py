"""
系统默认配置 API（per-user 版本，v1.3.3）

路由总览：
  GET  /config/defaults           → 当前用户自己的默认配置（domain_spec/super_admin 可读）
  PUT  /config/defaults           → 设置自己的默认配置（需超管飞书确认）
  GET  /config/defaults/all       → 所有专员的默认配置列表（super_admin 专属）
  PUT  /config/defaults/{uid}     → 超管替指定用户设置默认配置（super_admin 专属，需飞书确认）

权限：
  require_view_providers  → GET 系列
  require_manage_providers → PUT 系列（走飞书确认，返回 pending_approval）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.api.dependencies import require_view_providers, require_manage_providers
from app.models.user import User
from app.models.system import SystemDefaults
from app.models.user_confirmation import ConfirmationOperationType
from app.services.user_confirmation_service import UserOperationConfirmationService

router = APIRouter(prefix="/config", tags=["系统配置"])


# ==================== Schema ====================

class DefaultsResponse(BaseModel):
    """单用户默认配置响应"""
    user_id: Optional[int] = None
    default_registrar: Optional[str] = None
    default_dns_provider: Optional[str] = None
    default_reg_account_id: Optional[int] = None
    default_dns_account_id: Optional[int] = None

    model_config = {"from_attributes": True}


class UserDefaultsItem(BaseModel):
    """超管视图：某个用户 + 其默认配置"""
    user_id: int
    user_name: str
    user_role: str
    default_registrar: Optional[str] = None
    default_dns_provider: Optional[str] = None
    default_reg_account_id: Optional[int] = None
    default_dns_account_id: Optional[int] = None


class DefaultsUpdate(BaseModel):
    default_registrar: Optional[str] = None
    default_dns_provider: Optional[str] = None
    default_reg_account_id: Optional[int] = None
    default_dns_account_id: Optional[int] = None


# ==================== 工具 ====================

def _get_defaults_for_user(db: Session, user_id: int) -> Optional[SystemDefaults]:
    """获取指定用户的默认配置行（不存在返回 None）"""
    return db.query(SystemDefaults).filter(SystemDefaults.user_id == user_id).first()


def _make_defaults_confirmation(
    db: Session,
    current_user: User,
    target_user_id: int,
    target_user_name: str,
    data: DefaultsUpdate,
) -> dict:
    """发起默认配置变更的飞书确认"""
    conf_svc = UserOperationConfirmationService(db)
    conf = conf_svc.create_confirmation(
        operation_type=ConfirmationOperationType.SET_DEFAULT_CONFIG,
        initiator_user_id=current_user.id,
        initiator_name=current_user.name,
        initiator_feishu_userid=getattr(current_user, "feishu_user_id", "") or "",
        target_user_data={
            "target_user_id": target_user_id,
            "target_user_name": target_user_name,
        },
        operation_details={
            "type": "set_user_defaults",
            "target_user_id": target_user_id,
            "changes": data.model_dump(exclude_none=True),
        },
        requires_super_admin=True,
    )
    conf_svc.send_account_op_card_to_super_admin(conf)
    return {
        "status": "pending_approval",
        "confirmation_id": conf.id,
        "message": f"已向超级管理员发送授权申请，审批通过后「{target_user_name}」的默认配置将生效",
    }


# ==================== 端点 ====================

@router.get("/defaults", response_model=DefaultsResponse)
def get_my_defaults(
    current_user: User = Depends(require_view_providers),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的默认配置（domain_spec/super_admin 可读）
    如果尚未设置过，返回全空的默认值（不报错）。
    """
    row = _get_defaults_for_user(db, current_user.id)
    if not row:
        return DefaultsResponse(user_id=current_user.id)
    return DefaultsResponse.model_validate(row)


@router.get("/defaults/all", response_model=List[UserDefaultsItem])
def get_all_defaults(
    current_user: User = Depends(require_view_providers),
    db: Session = Depends(get_db),
):
    """
    获取所有专员的默认配置列表（super_admin 专属）
    包含尚未设置默认配置的专员（字段全为 null）。
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可查看所有用户的默认配置",
        )

    # 取所有活跃的 domain_spec + super_admin
    users = (
        db.query(User)
        .filter(User.role.in_(["domain_spec", "super_admin"]), User.is_active == True)
        .order_by(User.role.desc(), User.id.asc())   # super_admin 排前面
        .all()
    )

    # 批量取已设置的行
    user_ids = [u.id for u in users]
    defaults_rows = db.query(SystemDefaults).filter(
        SystemDefaults.user_id.in_(user_ids)
    ).all()
    defaults_map = {r.user_id: r for r in defaults_rows}

    result = []
    for u in users:
        d = defaults_map.get(u.id)
        result.append(UserDefaultsItem(
            user_id=u.id,
            user_name=u.name,
            user_role=u.role,
            default_registrar=d.default_registrar if d else None,
            default_dns_provider=d.default_dns_provider if d else None,
            default_reg_account_id=d.default_reg_account_id if d else None,
            default_dns_account_id=d.default_dns_account_id if d else None,
        ))
    return result


@router.put("/defaults")
def update_my_defaults(
    data: DefaultsUpdate,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """
    设置当前用户自己的默认配置（domain_spec/super_admin 均需超管飞书确认）
    返回 {status: "pending_approval", ...}
    """
    return _make_defaults_confirmation(
        db, current_user,
        target_user_id=current_user.id,
        target_user_name=current_user.name,
        data=data,
    )


@router.put("/defaults/{target_user_id}")
def update_user_defaults(
    target_user_id: int,
    data: DefaultsUpdate,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """
    超管替指定用户设置默认配置（super_admin 专属，需飞书确认）
    返回 {status: "pending_approval", ...}
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可替他人设置默认配置",
        )

    target = db.query(User).filter(User.id == target_user_id, User.is_active == True).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目标用户不存在")
    if target.role not in ("domain_spec", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能为 domain_spec 或 super_admin 设置默认配置",
        )

    return _make_defaults_confirmation(
        db, current_user,
        target_user_id=target_user_id,
        target_user_name=target.name,
        data=data,
    )
