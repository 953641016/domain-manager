"""
申请管理API路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, require_manage_users
from app.services.request_service import RequestService
from app.schemas.request import (
    RequestCreate, RequestUpdate, RequestApprove, RequestReject,
    RequestResponse, RequestListResponse, RequestStatsResponse
)
from app.models.user import User

router = APIRouter(
    prefix="/requests",
    tags=["申请管理"],
)


@router.get("", response_model=RequestListResponse)
def get_requests(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态筛选"),
    type: Optional[str] = Query(None, description="类型筛选"),
    domain_name: Optional[str] = Query(None, description="域名搜索"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取申请列表

    根据用户角色返回对应的申请：
    - 业务同事：只能查看自己的申请
    - 域名专员/管理员：可以查看所有申请
    """
    service = RequestService(db)

    # 根据角色决定查询范围
    requester_id = None
    if current_user.role == "business":
        requester_id = current_user.id

    requests = service.get_requests(
        skip=skip,
        limit=limit,
        status=status_filter,
        request_type=type,
        requester_id=requester_id,
        domain_name=domain_name
    )
    total = service.get_request_count(
        status=status_filter,
        request_type=type,
        requester_id=requester_id,
        domain_name=domain_name
    )

    return RequestListResponse(
        total=total,
        items=[RequestResponse.model_validate(r) for r in requests]
    )


@router.get("/stats", response_model=RequestStatsResponse)
def get_request_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取申请统计
    """
    service = RequestService(db)
    stats = service.get_stats()
    return RequestStatsResponse(**stats)


@router.get("/pending")
def get_pending_requests(
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    获取待审批的申请

    需要管理员或域名专员权限
    """
    service = RequestService(db)
    requests = service.get_pending_requests()

    return {
        "total": len(requests),
        "items": [RequestResponse.model_validate(r) for r in requests]
    }


@router.get("/my")
def get_my_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取我的申请
    """
    service = RequestService(db)
    requests = service.get_my_requests(
        requester_id=current_user.id,
        skip=skip,
        limit=limit
    )
    total = service.get_request_count(requester_id=current_user.id)

    return {
        "total": total,
        "items": [RequestResponse.model_validate(r) for r in requests]
    }


@router.get("/{request_id}", response_model=RequestResponse)
def get_request(
    request_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取申请详情
    """
    service = RequestService(db)
    request = service.get_request(request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="申请不存在"
        )

    # 检查权限：业务同事只能查看自己的申请
    if current_user.role == "business" and request.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此申请"
        )

    return RequestResponse.model_validate(request)


@router.post("", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    data: RequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    创建申请

    所有用户都可以创建申请
    """
    service = RequestService(db)

    # 验证申请类型
    valid_types = ["domain_register", "dns_record"]
    if data.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的申请类型: {data.type}"
        )

    try:
        request = service.create_request(
            data=data,
            requester_id=current_user.id,
            requester_name=current_user.name
        )
        return RequestResponse.model_validate(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{request_id}", response_model=RequestResponse)
def update_request(
    request_id: str,
    data: RequestUpdate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    更新申请

    需要管理员权限
    """
    service = RequestService(db)
    request = service.update_request(request_id, data)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="申请不存在"
        )

    return RequestResponse.model_validate(request)


@router.post("/{request_id}/approve", response_model=RequestResponse)
def approve_request(
    request_id: str,
    data: RequestApprove = RequestApprove(),
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    审批通过申请

    需要管理员或域名专员权限
    """
    service = RequestService(db)
    try:
        # 审批时若指定了注册商/解析账号覆盖，先写入申请
        override = data.model_dump(
            include={
                "selected_registrar_code", "selected_reg_account_id",
                "selected_dns_provider_code", "selected_dns_account_id",
            },
            exclude_none=True,
        )
        if override:
            existing = service.get_request(request_id)
            if existing:
                for key, value in override.items():
                    setattr(existing, key, value)
                db.commit()

        request = service.approve_request(
            request_id=request_id,
            approver_id=current_user.id,
            approver_name=current_user.name,
            comment=data.comment
        )

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="申请不存在"
            )

        # 打通主线：审批通过后自动执行（注册/DNS配置）并发送差异化通知
        if data.auto_execute:
            from app.services.execution_service import ExecutionService
            ExecutionService(db).execute_and_notify(request)
            db.refresh(request)

        return RequestResponse.model_validate(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/reject", response_model=RequestResponse)
def reject_request(
    request_id: str,
    data: RequestReject,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    拒绝申请

    需要管理员或域名专员权限
    """
    service = RequestService(db)
    try:
        request = service.reject_request(
            request_id=request_id,
            approver_id=current_user.id,
            approver_name=current_user.name,
            reason=data.reason
        )

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="申请不存在"
            )

        return RequestResponse.model_validate(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/complete", response_model=RequestResponse)
def complete_request(
    request_id: str,
    execution_result: Optional[dict] = None,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    标记申请为已完成

    需要管理员或域名专员权限
    """
    service = RequestService(db)
    request = service.complete_request(request_id, execution_result)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="申请不存在"
        )

    return RequestResponse.model_validate(request)


@router.post("/{request_id}/fail", response_model=RequestResponse)
def fail_request(
    request_id: str,
    error_message: str,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    标记申请为失败

    需要管理员或域名专员权限
    """
    service = RequestService(db)
    request = service.fail_request(request_id, error_message)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="申请不存在"
        )

    return RequestResponse.model_validate(request)
