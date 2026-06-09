"""
域名管理API路由

账号自检路由说明：
- 权限：require_view_accounts，domain_spec 仅可检测自己账号，super_admin 可检测全部账号
- 超管确认：不需要；自检只读取服务商接口，不新增/修改/删除账号配置
- 返回格式：对象 {success, status, message, checks, details}
"""
from typing import Optional
import requests
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import (
    get_current_active_user,
    require_view_accounts, require_manage_accounts,
    require_view_domains, require_manage_users,
)
from app.services.domain_service import DomainService
from app.services.user_confirmation_service import UserOperationConfirmationService
from app.models.user_confirmation import ConfirmationOperationType
from app.models.domain import RegAccount, DnsAccount
from app.schemas.domain import (
    DomainCreate, DomainUpdate, DomainResponse, DomainListResponse,
    RegAccountCreate, RegAccountUpdate, RegAccountResponse,
    DnsAccountCreate, DnsAccountUpdate, DnsAccountResponse
)
from app.models.user import User
from app.adapters.registrar_factory import RegistrarFactory

router = APIRouter(
    prefix="/domains",
    tags=["域名管理"],
)


def _build_owner_map(db: Session, accounts) -> dict:
    """批量查归属专员姓名，返回 {owner_id: name}"""
    owner_ids = {a.owner_id for a in accounts if a.owner_id}
    if not owner_ids:
        return {}
    users = db.query(User).filter(User.id.in_(owner_ids)).all()
    return {u.id: u.name for u in users}


def _with_owner(response_cls, account, owner_map: dict):
    """将 ORM 对象 + owner_name 合并为 response schema"""
    obj = response_cls.model_validate(account)
    obj.owner_name = owner_map.get(account.owner_id) if account.owner_id else None
    return obj


def _with_dns_account_name(domain):
    """将域名 ORM 对象转换为响应，并附带 DNS 账号名称"""
    obj = DomainResponse.model_validate(domain)
    obj.dns_account_name = domain.dns_account.name if domain.dns_account else None
    return obj


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
        items=[_with_dns_account_name(d) for d in domains]
    )


@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(
    domain_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取域名详情（domain_spec 只能查看自己名下的域名）
    """
    service = DomainService(db)
    domain = service.get_domain(domain_id)

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="域名不存在"
        )

    # domain_spec 只能查看自己名下的域名
    if current_user.role == "domain_spec" and domain.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此域名"
        )

    return _with_dns_account_name(domain)








@router.get("/expiring/list")
def get_expiring_domains(
    days: int = Query(30, ge=1, le=365, description="到期天数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取即将到期的域名（domain_spec 只看自己名下的；super_admin 看全部）

    默认返回30天内到期的域名
    """
    service = DomainService(db)
    # domain_spec 只能看自己名下的域名
    owner_id = current_user.id if current_user.role == "domain_spec" else None
    domains = service.get_expiring_domains(days, owner_id=owner_id)

    return {
        "total": len(domains),
        "items": [_with_dns_account_name(d) for d in domains]
    }


# ========== 注册账号管理 ==========

@router.get("/accounts/reg/list")
def get_reg_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    registrar_code: Optional[str] = Query(None),
    current_user: User = Depends(require_view_accounts),  # admin 无此权限 → 403
    db: Session = Depends(get_db),
):
    """获取注册账号列表（domain_spec 只见自己的；super_admin 见全部含归属专员姓名）"""
    service = DomainService(db)
    owner_id = current_user.id if current_user.role == "domain_spec" else None
    accounts = service.get_reg_accounts(
        skip=skip, limit=limit, registrar_code=registrar_code, owner_id=owner_id
    )
    owner_map = _build_owner_map(db, accounts)
    return {"total": len(accounts), "items": [_with_owner(RegAccountResponse, a, owner_map) for a in accounts]}


@router.get("/accounts/reg/{account_id}", response_model=RegAccountResponse)
def get_reg_account(
    account_id: int,
    current_user: User = Depends(require_view_accounts),
    db: Session = Depends(get_db),
):
    """获取注册账号详情（domain_spec 只能查自己的，super_admin 不限）"""
    service = DomainService(db)
    account = service.get_reg_account(account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    if current_user.role == "domain_spec" and account.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看他人账号")
    owner_map = _build_owner_map(db, [account])
    return _with_owner(RegAccountResponse, account, owner_map)


@router.post("/accounts/reg/{account_id}/self-check")
def self_check_reg_account(
    account_id: int,
    current_user: User = Depends(require_view_accounts),
    db: Session = Depends(get_db),
):
    """注册账号自检：只读调用注册商查价/可用性接口，不修改账号配置。"""
    service = DomainService(db)
    account = service.get_reg_account(account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    if current_user.role == "domain_spec" and account.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权检测他人账号")
    return _self_check_reg_account(service, account)


def _check_account_ownership(db, account_id: int, current_user: User, model_class) -> None:
    """归属校验：domain_spec 只能操作自己 owner 的账号（#2 归属校验）"""
    if current_user.role == "super_admin":
        return  # 超管无限制
    account = db.query(model_class).filter_by(id=account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    if account.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作他人的账号")


def _format_provider_error(data, fallback: str = "服务商接口调用失败") -> str:
    if isinstance(data, dict):
        errors = data.get("errors")
        if errors:
            return str(errors)
        code = data.get("code")
        message = data.get("message") or data.get("detail")
        if code and message:
            return f"{code}: {message}"
        if message:
            return str(message)
        if code:
            return str(code)
    return fallback


def _self_check_reg_account(service: DomainService, account: RegAccount) -> dict:
    decrypted = service.get_reg_account_decrypted(account.id)
    checks = []
    details = {
        "account_id": account.id,
        "account_name": account.name,
        "registrar_code": account.registrar_code,
    }

    if not decrypted or not decrypted.api_key:
        return {
            "success": False,
            "status": "failed",
            "message": "账号未配置 API Key / Token",
            "checks": [{"name": "凭据配置", "success": False, "message": "账号未配置 API Key / Token"}],
            "details": details,
        }

    if decrypted.registrar_code == "cloudflare" and not decrypted.api_secret:
        return {
            "success": False,
            "status": "failed",
            "message": "Cloudflare 注册账号未配置 Account ID",
            "checks": [{"name": "凭据配置", "success": False, "message": "Cloudflare 注册账号未配置 Account ID"}],
            "details": details,
        }

    try:
        adapter = RegistrarFactory.create_registrar(
            decrypted.registrar_code,
            decrypted.api_key,
            decrypted.api_secret,
            account_id=decrypted.api_secret if decrypted.registrar_code == "cloudflare" else None,
        )
        quote = adapter.check_domain_availability("example-test-20260603-domain.com") or {}
    except Exception as e:
        quote = {"check_successful": False, "message": str(e)}

    check_success = bool(quote.get("check_successful"))
    checks.append({
        "name": "查价/可注册性接口",
        "success": check_success,
        "message": quote.get("message") or ("接口可访问" if check_success else "检查失败"),
    })
    details.update({
        "test_domain": quote.get("domain") or "example-test-20260603-domain.com",
        "available": quote.get("available"),
        "price": quote.get("price"),
        "currency": quote.get("currency"),
        "provider_message": quote.get("message"),
    })

    return {
        "success": check_success,
        "status": "ok" if check_success else "failed",
        "message": "注册账号自检通过" if check_success else (quote.get("message") or "注册账号自检失败"),
        "checks": checks,
        "details": details,
    }


def _self_check_dns_account(service: DomainService, account: DnsAccount) -> dict:
    decrypted = service.get_dns_account_decrypted(account.id)
    details = {
        "account_id": account.id,
        "account_name": account.name,
        "provider_code": account.provider_code,
    }
    if not decrypted or not decrypted.api_key:
        return {
            "success": False,
            "status": "failed",
            "message": "账号未配置 API Key / Token",
            "checks": [{"name": "凭据配置", "success": False, "message": "账号未配置 API Key / Token"}],
            "details": details,
        }

    checks = []
    if decrypted.provider_code == "cloudflare":
        headers = {"Authorization": f"Bearer {decrypted.api_key}", "Content-Type": "application/json"}
        is_account_token = str(decrypted.api_key or "").startswith("cfat_")
        if is_account_token:
            checks.append({
                "name": "Token 类型",
                "success": True,
                "message": "Cloudflare Account API Token；跳过 /user/tokens/verify",
            })
        else:
            try:
                verify_resp = requests.get(
                    "https://api.cloudflare.com/client/v4/user/tokens/verify",
                    headers=headers,
                    timeout=10,
                )
                verify_data = verify_resp.json()
            except Exception as e:
                verify_data = {"success": False, "errors": [str(e)]}
            verify_ok = bool(verify_data.get("success"))
            checks.append({
                "name": "Token 验证",
                "success": verify_ok,
                "message": "Token 有效" if verify_ok else _format_provider_error(verify_data, "Token 验证失败"),
            })

        try:
            zones_resp = requests.get(
                "https://api.cloudflare.com/client/v4/zones",
                headers=headers,
                params={"per_page": 1},
                timeout=10,
            )
            zones_data = zones_resp.json()
        except Exception as e:
            zones_data = {"success": False, "errors": [str(e)]}
        zones_ok = bool(zones_data.get("success"))
        checks.append({
            "name": "Zone 读取权限",
            "success": zones_ok,
            "message": "可读取 Zone 列表" if zones_ok else _format_provider_error(zones_data, "Zone 读取失败"),
        })
        result_info = zones_data.get("result_info") or {}
        sample_zone = ((zones_data.get("result") or [{}])[0] or {}) if zones_ok else {}
        details.update({
            "zone_count": result_info.get("total_count"),
            "sample_zone": sample_zone.get("name") if zones_ok else None,
        })

        if zones_ok and sample_zone.get("id"):
            try:
                records_resp = requests.get(
                    f"https://api.cloudflare.com/client/v4/zones/{sample_zone['id']}/dns_records",
                    headers=headers,
                    params={"per_page": 1},
                    timeout=10,
                )
                records_data = records_resp.json()
            except Exception as e:
                records_data = {"success": False, "errors": [str(e)]}
            records_ok = bool(records_data.get("success"))
            checks.append({
                "name": "DNS 记录读取权限",
                "success": records_ok,
                "message": "可读取 DNS 记录" if records_ok else _format_provider_error(records_data, "DNS 记录读取失败"),
            })
    elif decrypted.provider_code == "dnspod":
        try:
            adapter = RegistrarFactory.create_dns_provider("dnspod", decrypted.api_key, decrypted.api_secret)
            resp = adapter._request("DescribeDomainList", {"Type": "1", "Offset": 0, "Limit": 1})
            checks.append({"name": "域名列表读取权限", "success": True, "message": "可读取 DNSPod 域名列表"})
            details.update({
                "domain_count": resp.get("DomainCountInfo", {}).get("Total") if isinstance(resp, dict) else None,
                "sample_domain": ((resp.get("DomainList") or [{}])[0] or {}).get("Name") if isinstance(resp, dict) else None,
            })
        except Exception as e:
            checks.append({"name": "域名列表读取权限", "success": False, "message": str(e)})
    else:
        checks.append({"name": "服务商支持", "success": False, "message": f"暂不支持自检的 DNS 服务商: {decrypted.provider_code}"})

    success = all(item.get("success") for item in checks)
    failed = next((item for item in checks if not item.get("success")), None)
    return {
        "success": success,
        "status": "ok" if success else "failed",
        "message": "DNS账号自检通过" if success else (failed.get("message") if failed else "DNS账号自检失败"),
        "checks": checks,
        "details": details,
    }


def _make_confirmation(
    db, current_user: User, op_type: ConfirmationOperationType,
    details: dict, api_key_masked: str = ""
) -> dict:
    """发起需超管确认的操作：创建 Confirmation 记录并发飞书卡片给超管"""
    conf_svc = UserOperationConfirmationService(db)
    conf = conf_svc.create_confirmation(
        operation_type=op_type,
        initiator_user_id=current_user.id,
        initiator_name=current_user.name,
        initiator_feishu_userid=getattr(current_user, "feishu_user_id", "") or "",
        target_user_data={"initiator_id": current_user.id, "initiator_name": current_user.name,
                          "initiator_role": current_user.role},
        operation_details=details,
        requires_super_admin=True,
    )
    conf_svc.send_account_op_card_to_super_admin(conf, api_key_masked=api_key_masked)
    return {"status": "pending_approval", "confirmation_id": conf.id,
            "message": "已向超级管理员发送授权申请，请等待审批"}


@router.post("/accounts/reg")
def create_reg_account(
    data: RegAccountCreate,
    current_user: User = Depends(require_manage_accounts),  # admin → 403
    db: Session = Depends(get_db),
):
    """新增注册账号（domain_spec/super_admin 均需超管飞书确认）
    owner 规则：domain_spec → 自己；super_admin → target_owner_id 或自己
    """
    if current_user.role == "super_admin" and data.target_owner_id:
        owner_id = data.target_owner_id
    else:
        owner_id = current_user.id
    masked = ("****" + data.api_key[-4:]) if data.api_key and len(data.api_key) >= 4 else "****"
    payload = data.model_dump(exclude={"target_owner_id"})
    return _make_confirmation(
        db, current_user,
        ConfirmationOperationType.ADD_REG_ACCOUNT,
        details={"data": payload, "owner_id": owner_id, "set_as_default": data.set_as_default},
        api_key_masked=masked,
    )


@router.put("/accounts/reg/{account_id}")
def update_reg_account(
    account_id: int,
    data: RegAccountUpdate,
    current_user: User = Depends(require_manage_accounts),
    db: Session = Depends(get_db),
):
    """修改注册账号（所有角色均需超管确认；domain_spec 须是自己的账号）"""
    _check_account_ownership(db, account_id, current_user, RegAccount)
    masked = ("****" + data.api_key[-4:]) if getattr(data, "api_key", None) and len(data.api_key) >= 4 else ""
    return _make_confirmation(
        db, current_user,
        ConfirmationOperationType.UPDATE_REG_ACCOUNT,
        details={"account_id": account_id, "data": data.model_dump(exclude_none=True)},
        api_key_masked=masked,
    )


@router.delete("/accounts/reg/{account_id}")
def delete_reg_account(
    account_id: int,
    current_user: User = Depends(require_manage_accounts),
    db: Session = Depends(get_db),
):
    """删除注册账号（所有角色均需超管确认；domain_spec 须是自己的账号）"""
    _check_account_ownership(db, account_id, current_user, RegAccount)
    return _make_confirmation(
        db, current_user,
        ConfirmationOperationType.DELETE_REG_ACCOUNT,
        details={"account_id": account_id},
    )


# ========== DNS账号管理 ==========

@router.get("/accounts/dns/list")
def get_dns_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    provider_code: Optional[str] = Query(None),
    current_user: User = Depends(require_view_accounts),  # admin → 403
    db: Session = Depends(get_db),
):
    """获取DNS账号列表（domain_spec 只见自己的；super_admin 见全部含归属专员姓名）"""
    service = DomainService(db)
    owner_id = current_user.id if current_user.role == "domain_spec" else None
    accounts = service.get_dns_accounts(
        skip=skip, limit=limit, provider_code=provider_code, owner_id=owner_id
    )
    owner_map = _build_owner_map(db, accounts)
    return {"total": len(accounts), "items": [_with_owner(DnsAccountResponse, a, owner_map) for a in accounts]}


@router.get("/accounts/dns/{account_id}", response_model=DnsAccountResponse)
def get_dns_account(
    account_id: int,
    current_user: User = Depends(require_view_accounts),
    db: Session = Depends(get_db),
):
    """获取DNS账号详情（domain_spec 只能查自己的，super_admin 不限）"""
    service = DomainService(db)
    account = service.get_dns_account(account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    if current_user.role == "domain_spec" and account.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看他人账号")
    owner_map = _build_owner_map(db, [account])
    return _with_owner(DnsAccountResponse, account, owner_map)


@router.post("/accounts/dns/{account_id}/self-check")
def self_check_dns_account(
    account_id: int,
    current_user: User = Depends(require_view_accounts),
    db: Session = Depends(get_db),
):
    """DNS账号自检：只读调用 DNS 服务商 Token/域名列表接口，不修改账号配置。"""
    service = DomainService(db)
    account = service.get_dns_account(account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    if current_user.role == "domain_spec" and account.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权检测他人账号")
    return _self_check_dns_account(service, account)


@router.post("/accounts/dns")
def create_dns_account(
    data: DnsAccountCreate,
    current_user: User = Depends(require_manage_accounts),  # admin → 403
    db: Session = Depends(get_db),
):
    """新增解析账号（domain_spec/super_admin 均需超管飞书确认）
    owner 规则：domain_spec → 自己；super_admin → target_owner_id 或自己
    """
    if current_user.role == "super_admin" and data.target_owner_id:
        owner_id = data.target_owner_id
    else:
        owner_id = current_user.id
    masked = ("****" + data.api_key[-4:]) if data.api_key and len(data.api_key) >= 4 else "****"
    payload = data.model_dump(exclude={"target_owner_id"})
    return _make_confirmation(
        db, current_user,
        ConfirmationOperationType.ADD_DNS_ACCOUNT,
        details={"data": payload, "owner_id": owner_id},
        api_key_masked=masked,
    )


@router.put("/accounts/dns/{account_id}")
def update_dns_account(
    account_id: int,
    data: DnsAccountUpdate,
    current_user: User = Depends(require_manage_accounts),
    db: Session = Depends(get_db),
):
    """修改解析账号（所有角色均需超管确认；domain_spec 须是自己的账号）"""
    _check_account_ownership(db, account_id, current_user, DnsAccount)
    masked = ("****" + data.api_key[-4:]) if getattr(data, "api_key", None) and len(data.api_key) >= 4 else ""
    return _make_confirmation(
        db, current_user,
        ConfirmationOperationType.UPDATE_DNS_ACCOUNT,
        details={"account_id": account_id, "data": data.model_dump(exclude_none=True)},
        api_key_masked=masked,
    )


@router.delete("/accounts/dns/{account_id}")
def delete_dns_account(
    account_id: int,
    current_user: User = Depends(require_manage_accounts),
    db: Session = Depends(get_db),
):
    """删除解析账号（所有角色均需超管确认；domain_spec 须是自己的账号）"""
    _check_account_ownership(db, account_id, current_user, DnsAccount)
    return _make_confirmation(
        db, current_user,
        ConfirmationOperationType.DELETE_DNS_ACCOUNT,
        details={"account_id": account_id},
    )
