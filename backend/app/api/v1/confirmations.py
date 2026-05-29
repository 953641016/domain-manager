"""
用户确认操作API
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user_confirmation import (
    ConfirmationOperationType,
    ConfirmationStatus
)
from app.schemas.user_confirmation import (
    UserOperationConfirmationCreate,
    UserOperationConfirmationReject,
    UserOperationConfirmationResponse,
    UserOperationConfirmationListResponse
)
from app.services.user_confirmation_service import UserOperationConfirmationService


router = APIRouter(
    prefix="/confirmations",
    tags=["用户确认操作"],
)


def get_confirmation_service(db: Session = Depends(get_db)) -> UserOperationConfirmationService:
    """获取确认服务实例"""
    return UserOperationConfirmationService(db)


@router.get("", response_model=UserOperationConfirmationListResponse)
def get_confirmations(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    initiator_user_id: Optional[int] = Query(None, description="发起者用户ID筛选"),
    service: UserOperationConfirmationService = Depends(get_confirmation_service)
):
    """获取确认操作列表"""
    confirmations = service.get_confirmations(
        skip=skip,
        limit=limit,
        status=status,
        initiator_user_id=initiator_user_id
    )
    total = service.get_confirmations_count(
        status=status,
        initiator_user_id=initiator_user_id
    )

    items = []
    for conf in confirmations:
        item = UserOperationConfirmationResponse.model_validate(conf)
        item.operation_description = service.format_operation_description(conf)
        items.append(item)

    return UserOperationConfirmationListResponse(total=total, items=items)


@router.get("/pending", response_model=UserOperationConfirmationListResponse)
def get_pending_confirmations(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    service: UserOperationConfirmationService = Depends(get_confirmation_service)
):
    """获取待确认的操作列表"""
    confirmations = service.get_pending_confirmations()

    items = []
    for conf in confirmations[skip:skip+limit]:
        item = UserOperationConfirmationResponse.model_validate(conf)
        item.operation_description = service.format_operation_description(conf)
        items.append(item)

    return UserOperationConfirmationListResponse(total=len(confirmations), items=items)


@router.get("/{confirmation_id}", response_model=UserOperationConfirmationResponse)
def get_confirmation(
    confirmation_id: int,
    service: UserOperationConfirmationService = Depends(get_confirmation_service)
):
    """获取确认操作详情"""
    confirmation = service.get_confirmation(confirmation_id)

    if not confirmation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="确认操作不存在"
        )

    item = UserOperationConfirmationResponse.model_validate(confirmation)
    item.operation_description = service.format_operation_description(confirmation)

    return item


@router.post("/{confirmation_id}/approve", response_model=UserOperationConfirmationResponse)
def approve_confirmation(
    confirmation_id: int,
    approver_user_id: int = Query(..., description="批准者用户ID"),
    approver_name: str = Query(..., description="批准者姓名"),
    approver_feishu_userid: str = Query(..., description="批准者飞书ID"),
    service: UserOperationConfirmationService = Depends(get_confirmation_service)
):
    """批准确认操作"""
    confirmation = service.approve_confirmation(
        confirmation_id=confirmation_id,
        approver_user_id=approver_user_id,
        approver_name=approver_name,
        approver_feishu_userid=approver_feishu_userid
    )

    if not confirmation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="确认操作不存在或已处理"
        )

    item = UserOperationConfirmationResponse.model_validate(confirmation)
    item.operation_description = service.format_operation_description(confirmation)

    return item


@router.post("/{confirmation_id}/reject", response_model=UserOperationConfirmationResponse)
def reject_confirmation(
    confirmation_id: int,
    reject_data: UserOperationConfirmationReject,
    approver_user_id: int = Query(..., description="拒绝者用户ID"),
    approver_name: str = Query(..., description="拒绝者姓名"),
    approver_feishu_userid: str = Query(..., description="拒绝者飞书ID"),
    service: UserOperationConfirmationService = Depends(get_confirmation_service)
):
    """拒绝确认操作"""
    confirmation = service.reject_confirmation(
        confirmation_id=confirmation_id,
        approver_user_id=approver_user_id,
        approver_name=approver_name,
        approver_feishu_userid=approver_feishu_userid,
        reject_reason=reject_data.reject_reason
    )

    if not confirmation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="确认操作不存在或已处理"
        )

    item = UserOperationConfirmationResponse.model_validate(confirmation)
    item.operation_description = service.format_operation_description(confirmation)

    return item


@router.post("/{confirmation_id}/cancel", response_model=UserOperationConfirmationResponse)
def cancel_confirmation(
    confirmation_id: int,
    initiator_user_id: int = Query(..., description="发起者用户ID"),
    service: UserOperationConfirmationService = Depends(get_confirmation_service)
):
    """取消确认操作（只能由发起者取消）"""
    confirmation = service.cancel_confirmation(
        confirmation_id=confirmation_id,
        initiator_user_id=initiator_user_id
    )

    if not confirmation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="确认操作不存在或无权限取消"
        )

    item = UserOperationConfirmationResponse.model_validate(confirmation)
    item.operation_description = service.format_operation_description(confirmation)

    return item


@router.get("/admins/list", response_model=list)
def get_admin_users(
    exclude_user_id: Optional[int] = Query(None, description="排除的用户ID"),
    service: UserOperationConfirmationService = Depends(get_confirmation_service)
):
    """获取管理员用户列表（用于发送确认消息）"""
    admins = service.get_admin_users(exclude_user_id=exclude_user_id)

    return [
        {
            "id": admin.id,
            "name": admin.name,
            "feishu_userid": admin.feishu_userid,
            "email": admin.email
        }
        for admin in admins
    ]
