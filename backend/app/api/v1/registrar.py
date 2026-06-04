"""
服务商管理 API（注册商 + DNS解析商）
- GET 接口：domain_spec / super_admin 可见（admin 无权）
- 增改删：均经超管飞书确认流程（domain_spec / super_admin 可发起）
- 服务商从数据库读取（替代硬编码工厂）
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import (
    get_current_active_user,
    require_view_providers,
    require_manage_providers,
)
from app.models.user import User
from app.models.domain import Registrar, DnsProvider
from app.models.user_confirmation import ConfirmationOperationType
from app.schemas.domain import (
    RegistrarCreate, RegistrarUpdate, RegistrarResponse,
    DnsProviderCreate, DnsProviderUpdate, DnsProviderResponse,
)
from app.services.user_confirmation_service import UserOperationConfirmationService

router = APIRouter(prefix="/providers", tags=["服务商管理"])

HIDDEN_REGISTRAR_CODES = {"namecheap", "enom"}

# ==================== 内部工具 ====================

def _make_provider_confirmation(db, current_user, op_type, details, description=""):
    """发起服务商操作确认"""
    conf_svc = UserOperationConfirmationService(db)
    conf = conf_svc.create_confirmation(
        operation_type=op_type,
        initiator_user_id=current_user.id,
        initiator_name=current_user.name,
        initiator_feishu_userid=getattr(current_user, "feishu_user_id", "") or "",
        target_user_data={"initiator_id": current_user.id, "initiator_role": current_user.role},
        operation_details=details,
        requires_super_admin=True,
    )
    conf_svc.send_account_op_card_to_super_admin(conf)
    return {"status": "pending_approval", "confirmation_id": conf.id,
            "message": "已向超级管理员发送授权申请，请等待审批"}


def _check_provider_in_use(db, provider_type: str, code: str) -> bool:
    """检查服务商是否被账号引用（删除前校验）"""
    from app.models.domain import RegAccount, DnsAccount
    if provider_type == "registrar":
        return db.query(RegAccount).filter_by(registrar_code=code).count() > 0
    else:
        return db.query(DnsAccount).filter_by(provider_code=code).count() > 0


# ==================== 注册商 ====================

@router.get("/registrars", response_model=list[RegistrarResponse])
def list_registrars(
    enabled_only: bool = Query(True),
    current_user: User = Depends(require_view_providers),
    db: Session = Depends(get_db),
):
    """获取注册商列表（domain_spec/super_admin 可见）"""
    q = db.query(Registrar)
    q = q.filter(~Registrar.code.in_(HIDDEN_REGISTRAR_CODES))
    if enabled_only:
        q = q.filter(Registrar.is_enabled == True)
    return [RegistrarResponse.model_validate(r) for r in q.order_by(Registrar.name).all()]


@router.post("/registrars")
def create_registrar(
    data: RegistrarCreate,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """新增注册商（需超管飞书确认）"""
    if db.query(Registrar).filter_by(code=data.code).first():
        raise HTTPException(status_code=400, detail=f"注册商代码 '{data.code}' 已存在")
    return _make_provider_confirmation(
        db, current_user,
        ConfirmationOperationType.ADD_PROVIDER,
        details={"provider_type": "registrar", "data": data.model_dump()},
    )


@router.put("/registrars/{registrar_id}")
def update_registrar(
    registrar_id: int,
    data: RegistrarUpdate,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """修改注册商（需超管飞书确认）"""
    if not db.query(Registrar).filter_by(id=registrar_id).first():
        raise HTTPException(status_code=404, detail="注册商不存在")
    return _make_provider_confirmation(
        db, current_user,
        ConfirmationOperationType.UPDATE_PROVIDER,
        details={"provider_type": "registrar", "id": registrar_id, "data": data.model_dump(exclude_none=True)},
    )


@router.delete("/registrars/{registrar_id}")
def delete_registrar(
    registrar_id: int,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """删除注册商（需超管飞书确认；有账号引用时拒绝）"""
    reg = db.query(Registrar).filter_by(id=registrar_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="注册商不存在")
    if _check_provider_in_use(db, "registrar", reg.code):
        raise HTTPException(status_code=400, detail="该注册商下仍有注册账号，无法删除")
    return _make_provider_confirmation(
        db, current_user,
        ConfirmationOperationType.DELETE_PROVIDER,
        details={"provider_type": "registrar", "id": registrar_id, "code": reg.code},
    )


# ==================== DNS解析商 ====================

@router.get("/dns-providers", response_model=list[DnsProviderResponse])
def list_dns_providers(
    enabled_only: bool = Query(True),
    current_user: User = Depends(require_view_providers),
    db: Session = Depends(get_db),
):
    """获取解析商列表（domain_spec/super_admin 可见）"""
    q = db.query(DnsProvider)
    if enabled_only:
        q = q.filter(DnsProvider.is_enabled == True)
    return [DnsProviderResponse.model_validate(p) for p in q.order_by(DnsProvider.name).all()]


@router.post("/dns-providers")
def create_dns_provider(
    data: DnsProviderCreate,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """新增解析商（需超管飞书确认）"""
    if db.query(DnsProvider).filter_by(code=data.code).first():
        raise HTTPException(status_code=400, detail=f"解析商代码 '{data.code}' 已存在")
    return _make_provider_confirmation(
        db, current_user,
        ConfirmationOperationType.ADD_PROVIDER,
        details={"provider_type": "dns_provider", "data": data.model_dump()},
    )


@router.put("/dns-providers/{provider_id}")
def update_dns_provider(
    provider_id: int,
    data: DnsProviderUpdate,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """修改解析商（需超管飞书确认）"""
    if not db.query(DnsProvider).filter_by(id=provider_id).first():
        raise HTTPException(status_code=404, detail="解析商不存在")
    return _make_provider_confirmation(
        db, current_user,
        ConfirmationOperationType.UPDATE_PROVIDER,
        details={"provider_type": "dns_provider", "id": provider_id, "data": data.model_dump(exclude_none=True)},
    )


@router.delete("/dns-providers/{provider_id}")
def delete_dns_provider(
    provider_id: int,
    current_user: User = Depends(require_manage_providers),
    db: Session = Depends(get_db),
):
    """删除解析商（需超管飞书确认；有账号引用时拒绝）"""
    prov = db.query(DnsProvider).filter_by(id=provider_id).first()
    if not prov:
        raise HTTPException(status_code=404, detail="解析商不存在")
    if _check_provider_in_use(db, "dns_provider", prov.code):
        raise HTTPException(status_code=400, detail="该解析商下仍有解析账号，无法删除")
    return _make_provider_confirmation(
        db, current_user,
        ConfirmationOperationType.DELETE_PROVIDER,
        details={"provider_type": "dns_provider", "id": provider_id, "code": prov.code},
    )


# ==================== 向后兼容：旧接口别名 ====================
# registrar.py 旧路由 /registrar/list 和 /registrar/dns-providers 由 main.py 保留

@router.get("/registrars/legacy-list")
def legacy_list_registrars(
    current_user: User = Depends(require_view_providers),
    db: Session = Depends(get_db),
):
    """旧格式兼容（Config.tsx 下拉框使用）"""
    registrars = (
        db.query(Registrar)
        .filter(Registrar.is_enabled == True)
        .filter(~Registrar.code.in_(HIDDEN_REGISTRAR_CODES))
        .order_by(Registrar.name)
        .all()
    )
    return {"registrars": [{"code": r.code, "name": r.name, "description": r.description or ""} for r in registrars]}


@router.get("/dns-providers/legacy-list")
def legacy_list_dns_providers(
    current_user: User = Depends(require_view_providers),
    db: Session = Depends(get_db),
):
    """旧格式兼容（Config.tsx 下拉框使用）"""
    providers = db.query(DnsProvider).filter(DnsProvider.is_enabled == True).order_by(DnsProvider.name).all()
    return {"dns_providers": [{"code": p.code, "name": p.name, "description": p.description or ""} for p in providers]}
