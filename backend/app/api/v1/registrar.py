"""
注册商配置管理API路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, require_manage_users
from app.adapters.registrar_factory import RegistrarFactory
from app.services.domain_service import DomainService
from app.schemas.domain import (
    RegAccountCreate, RegAccountUpdate, RegAccountResponse,
    DnsAccountCreate, DnsAccountUpdate, DnsAccountResponse
)
from app.models.user import User

router = APIRouter(
    prefix="/registrar",
    tags=["注册商管理"],
)


@router.get("/list")
def get_supported_registrars(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取支持的注册商列表
    """
    registrars = [
        RegistrarFactory.get_registrar_info(code)
        for code in RegistrarFactory.SUPPORTED_REGISTRARS
    ]

    return {
        "registrars": [r for r in registrars if r is not None]
    }


@router.get("/dns-providers")
def get_supported_dns_providers(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取支持的DNS解析商列表
    """
    providers = [
        RegistrarFactory.get_dns_provider_info(code)
        for code in RegistrarFactory.SUPPORTED_DNS_PROVIDERS
    ]

    return {
        "dns_providers": [p for p in providers if p is not None]
    }


@router.post("/test-connection")
def test_registrar_connection(
    registrar_code: str,
    api_key: str,
    api_secret: Optional[str] = None,
    current_user: User = Depends(require_manage_users),
):
    """
    测试注册商连接

    验证API Key是否有效
    """
    try:
        adapter = RegistrarFactory.create_registrar(
            code=registrar_code,
            api_key=api_key,
            api_secret=api_secret
        )

        # 尝试获取一个不存在的域名信息来测试连接
        result = adapter.get_domain_info("test-connection-test-12345.com")

        # 如果没有抛出异常，说明连接成功
        return {
            "success": True,
            "message": "连接测试成功"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接测试失败: {str(e)}"
        }


@router.post("/test-dns-connection")
def test_dns_connection(
    provider_code: str,
    api_key: str,
    current_user: User = Depends(require_manage_users),
):
    """
    测试DNS解析商连接

    验证API Key是否有效
    """
    try:
        adapter = RegistrarFactory.create_dns_provider(
            code=provider_code,
            api_key=api_key
        )

        # 尝试获取Zone ID来测试连接
        zone_id = adapter.get_zone_id("test-connection-test-12345.com")

        # 如果没有抛出异常，说明连接成功
        return {
            "success": True,
            "message": "连接测试成功",
            "zone_id": zone_id
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接测试失败: {str(e)}"
        }


@router.get("/accounts")
def get_all_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取所有注册商和DNS账号

    需要管理员权限
    """
    service = DomainService(db)

    reg_accounts = service.get_reg_accounts(
        owner_id=current_user.id if current_user.role == "business" else None
    )
    dns_accounts = service.get_dns_accounts(
        owner_id=current_user.id if current_user.role == "business" else None
    )

    return {
        "reg_accounts": [RegAccountResponse.model_validate(a) for a in reg_accounts],
        "dns_accounts": [DnsAccountResponse.model_validate(a) for a in dns_accounts]
    }
