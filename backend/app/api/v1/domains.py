"""
域名管理API路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, require_manage_users
from app.services.domain_service import DomainService
from app.schemas.domain import (
    DomainCreate, DomainUpdate, DomainResponse, DomainListResponse,
    RegAccountCreate, RegAccountUpdate, RegAccountResponse,
    DnsAccountCreate, DnsAccountUpdate, DnsAccountResponse
)
from app.models.user import User

router = APIRouter(
    prefix="/domains",
    tags=["域名管理"],
)


# ========== 域名管理 ==========

@router.get("", response_model=DomainListResponse)
def get_domains(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    registrar_code: Optional[str] = Query(None, description="注册商筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取域名列表

    根据用户角色返回对应的域名：
    - 业务同事：只能查看自己负责的域名
    - 域名专员/管理员：可以查看所有域名
    """
    service = DomainService(db)

    # 根据角色决定查询范围
    owner_id = None
    # 业务同事和域名专员只能看到自己分配的资源
    if current_user.role in ["business", "domain_spec"]:
        owner_id = current_user.id

    domains = service.get_domains(
        skip=skip,
        limit=limit,
        status=status,
        registrar_code=registrar_code,
        search=search,
        owner_id=owner_id
    )
    total = service.get_domain_count(
        status=status,
        registrar_code=registrar_code,
        search=search,
        owner_id=owner_id
    )

    return DomainListResponse(
        total=total,
        items=[DomainResponse.model_validate(d) for d in domains]
    )


@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(
    domain_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取域名详情
    """
    service = DomainService(db)
    domain = service.get_domain(domain_id)

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="域名不存在"
        )

    return DomainResponse.model_validate(domain)








@router.get("/expiring/list")
def get_expiring_domains(
    days: int = Query(30, ge=1, le=365, description="到期天数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取即将到期的域名

    默认返回30天内到期的域名
    """
    service = DomainService(db)
    domains = service.get_expiring_domains(days)

    return {
        "total": len(domains),
        "items": [DomainResponse.model_validate(d) for d in domains]
    }


# ========== 注册账号管理 ==========

@router.get("/accounts/reg/list")
def get_reg_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    registrar_code: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取注册账号列表
    """
    service = DomainService(db)
    accounts = service.get_reg_accounts(
        skip=skip,
        limit=limit,
        registrar_code=registrar_code,
        owner_id=current_user.id if current_user.role in ["business", "domain_spec"] else None
    )
    return {
        "total": len(accounts),
        "items": [RegAccountResponse.model_validate(a) for a in accounts]
    }


@router.get("/accounts/reg/{account_id}", response_model=RegAccountResponse)
def get_reg_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取注册账号详情
    """
    service = DomainService(db)
    account = service.get_reg_account(account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )

    return RegAccountResponse.model_validate(account)


@router.post("/accounts/reg", response_model=RegAccountResponse, status_code=status.HTTP_201_CREATED)
def create_reg_account(
    data: RegAccountCreate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    创建注册账号

    需要管理员权限
    """
    service = DomainService(db)
    account = service.create_reg_account(data, owner_id=current_user.id)
    return RegAccountResponse.model_validate(account)


@router.put("/accounts/reg/{account_id}", response_model=RegAccountResponse)
def update_reg_account(
    account_id: int,
    data: RegAccountUpdate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    更新注册账号

    需要管理员权限
    """
    service = DomainService(db)
    account = service.update_reg_account(account_id, data)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )

    return RegAccountResponse.model_validate(account)


@router.delete("/accounts/reg/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reg_account(
    account_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    删除注册账号

    需要管理员权限
    """
    service = DomainService(db)
    success = service.delete_reg_account(account_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )


# ========== DNS账号管理 ==========

@router.get("/accounts/dns/list")
def get_dns_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    provider_code: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取DNS账号列表
    """
    service = DomainService(db)
    accounts = service.get_dns_accounts(
        skip=skip,
        limit=limit,
        provider_code=provider_code,
        owner_id=current_user.id if current_user.role in ["business", "domain_spec"] else None
    )
    return {
        "total": len(accounts),
        "items": [DnsAccountResponse.model_validate(a) for a in accounts]
    }


@router.get("/accounts/dns/{account_id}", response_model=DnsAccountResponse)
def get_dns_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取DNS账号详情
    """
    service = DomainService(db)
    account = service.get_dns_account(account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )

    return DnsAccountResponse.model_validate(account)


@router.post("/accounts/dns", response_model=DnsAccountResponse, status_code=status.HTTP_201_CREATED)
def create_dns_account(
    data: DnsAccountCreate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    创建DNS账号

    需要管理员权限
    """
    service = DomainService(db)
    account = service.create_dns_account(data, owner_id=current_user.id)
    return DnsAccountResponse.model_validate(account)


@router.put("/accounts/dns/{account_id}", response_model=DnsAccountResponse)
def update_dns_account(
    account_id: int,
    data: DnsAccountUpdate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    更新DNS账号

    需要管理员权限
    """
    service = DomainService(db)
    account = service.update_dns_account(account_id, data)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )

    return DnsAccountResponse.model_validate(account)


@router.delete("/accounts/dns/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dns_account(
    account_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    删除DNS账号

    需要管理员权限
    """
    service = DomainService(db)
    success = service.delete_dns_account(account_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账号不存在"
        )
