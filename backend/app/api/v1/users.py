"""
用户管理 API
所有写操作（增改删）均需超管飞书确认（带外确认原则）
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import (
    get_current_active_user,
    require_manage_users,
    require_view_users,
)
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    RoleInfo
)
from app.services.user_service import UserService
from app.models.user import User
from app.models.user_confirmation import ConfirmationOperationType
from app.services.user_confirmation_service import UserOperationConfirmationService

router = APIRouter(
    prefix="/users",
    tags=["用户管理"],
)


def _user_confirmation(db, current_user: User, op_type: ConfirmationOperationType, details: dict) -> dict:
    """创建用户操作的超管确认请求并发飞书卡片"""
    svc = UserOperationConfirmationService(db)
    conf = svc.create_confirmation(
        operation_type=op_type,
        initiator_user_id=current_user.id,
        initiator_name=current_user.name,
        initiator_feishu_userid=getattr(current_user, "feishu_user_id", "") or "",
        target_user_data={"initiator_id": current_user.id, "initiator_role": current_user.role},
        operation_details=details,
        requires_super_admin=True,
        remark="web",
    )
    svc.send_account_op_card_to_super_admin(conf)
    return {
        "status": "pending_approval",
        "confirmation_id": conf.id,
        "message": "已向超级管理员发送授权申请，请等待审批",
    }


# ==================== 查询（只读，无需确认）====================

@router.get("", response_model=UserListResponse)
def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    feishu_app_id: Optional[int] = Query(None),
    current_user: User = Depends(require_view_users),
    db: Session = Depends(get_db),
):
    """获取用户列表（admin/super_admin 可见）"""
    service = UserService(db)
    users = service.get_users(skip=skip, limit=limit, role=role, is_active=is_active, search=search, feishu_app_id=feishu_app_id)
    total = service.get_users_count(role=role, is_active=is_active, search=search, feishu_app_id=feishu_app_id)
    return UserListResponse(total=total, items=users)


@router.get("/roles", response_model=list[RoleInfo])
def get_roles(current_user: User = Depends(get_current_active_user)):
    """获取所有角色信息"""
    return UserService.get_all_roles()


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前登录用户信息"""
    return current_user


@router.get("/specialists", response_model=list)
def get_specialists(
    feishu_app_id: Optional[int] = Query(None),
    current_user: User = Depends(require_view_users),
    db: Session = Depends(get_db),
):
    """获取域名专员列表（用于设置归属专员下拉）"""
    service = UserService(db)
    specs = service.get_users(role="domain_spec", is_active=True, limit=500, feishu_app_id=feishu_app_id)
    return [{"id": u.id, "name": u.name, "feishu_app_id": u.feishu_app_id} for u in specs]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(require_view_users),
    db: Session = Depends(get_db),
):
    """获取用户详情"""
    service = UserService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


# ==================== 写操作（均需超管飞书确认）====================

@router.post("")
def create_user(
    user_in: UserCreate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    创建用户（需超管飞书确认）
    业务人员(business)须在确认后手动设置归属专员
    """
    return _user_confirmation(
        db, current_user,
        ConfirmationOperationType.ADD_DOMAIN_SPEC
        if getattr(user_in, "role", "business") in ("domain_spec", "admin", "super_admin")
        else ConfirmationOperationType.ADD_DOMAIN_SPEC,
        details={
            "action": "create_user",
            "user_data": {
                "name": user_in.name,
                "role": user_in.role,
                "feishu_app_id": getattr(user_in, "feishu_app_id", None),
                "feishu_user_id": getattr(user_in, "feishu_userid", None) or getattr(user_in, "feishu_user_id", None),
                "email": getattr(user_in, "email", None),
                "department": getattr(user_in, "department", None),
            },
        },
    )


@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """更新用户信息（需超管飞书确认）"""
    service = UserService(db)
    target = service.get_user(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    details: dict = {
        "action": "update_user",
        "user_id": user_id,
        "target_name": target.name,
        "target_role": target.role,
        "changes": user_in.model_dump(exclude_none=True),
    }

    # 超管转让检测：将某人提升为 super_admin 且对方当前不是超管
    # → 原子操作：提升新超管 + 降级原超管为系统管理员
    if user_in.role == "super_admin" and target.role != "super_admin":
        from app.services.user_confirmation_service import UserOperationConfirmationService
        current_sa = UserOperationConfirmationService(db).get_super_admin()
        if current_sa and current_sa.id != user_id:
            details["transfer_super_admin"] = True
            details["old_super_admin_id"] = current_sa.id
            details["old_super_admin_name"] = current_sa.name

    return _user_confirmation(
        db, current_user,
        ConfirmationOperationType.UPDATE_USER_ROLE
        if user_in.role else ConfirmationOperationType.UPDATE_DOMAIN_SPEC,
        details=details,
    )


def _check_disable_delete_permission(current_user: User, target: User):
    """禁用/删除前的通用权限检查"""
    if target.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="超级管理员不能直接禁用或删除。如需更换超管，请将目标用户的角色改为「超级管理员」，系统将自动转让并将原超管降为系统管理员。",
        )
    if current_user.id == target.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能禁用或删除自己的账号")


@router.post("/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """禁用用户（is_active=False，可恢复；需超管飞书确认）"""
    service = UserService(db)
    target = service.get_user(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if not target.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已处于禁用状态")
    _check_disable_delete_permission(current_user, target)
    return _user_confirmation(
        db, current_user,
        ConfirmationOperationType.REMOVE_ADMIN
        if target.role in ("admin",) else ConfirmationOperationType.UPDATE_DOMAIN_SPEC,
        details={
            "action": "deactivate_user",
            "user_id": user_id,
            "target_name": target.name,
            "target_role": target.role,
        },
    )


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """删除用户（硬删除，不可恢复；需超管飞书确认）"""
    service = UserService(db)
    target = service.get_user(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    _check_disable_delete_permission(current_user, target)
    return _user_confirmation(
        db, current_user,
        ConfirmationOperationType.REMOVE_ADMIN
        if target.role in ("admin",) else ConfirmationOperationType.UPDATE_DOMAIN_SPEC,
        details={
            "action": "delete_user",
            "user_id": user_id,
            "target_name": target.name,
            "target_role": target.role,
        },
    )


@router.post("/{user_id}/activate")
def activate_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """激活用户（需超管飞书确认）"""
    service = UserService(db)
    target = service.get_user(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return _user_confirmation(
        db, current_user,
        ConfirmationOperationType.UPDATE_DOMAIN_SPEC,
        details={
            "action": "activate_user",
            "user_id": user_id,
            "target_name": target.name,
        },
    )
