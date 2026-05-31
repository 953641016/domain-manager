"""
SSL证书管理API路由
提供SSL证书查询、监控和告警功能
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from app.api.dependencies import require_admin
from app.models.user import User
from app.services.ssl_service import ssl_service

router = APIRouter(
    prefix="/ssl",
    tags=["SSL证书管理"],
)


class CertificateInfo(BaseModel):
    """证书信息"""
    domain: str
    issuer: str
    valid_from: str
    valid_to: str
    days_remaining: int
    is_valid: bool
    serial_number: Optional[str] = None
    fingerprint: Optional[str] = None


class CertificateMonitorResponse(BaseModel):
    """证书监控响应"""
    success: bool
    certificates: List[CertificateInfo]
    total: int
    valid_count: int
    expiring_soon_count: int


class CertificateAlertRequest(BaseModel):
    """证书告警请求"""
    threshold_days: int = 7


class CertificateAlertResponse(BaseModel):
    """证书告警响应"""
    success: bool
    alert_domains: List[str]
    alert_count: int


def _to_cert_info(raw: dict, threshold_days: int) -> dict:
    """将 ssl_service 的原始字典转换为 API 期望的 CertificateInfo 格式"""
    not_before = raw.get("not_before")
    not_after  = raw.get("not_after")
    days       = raw.get("days_remaining")
    return {
        "domain":         raw.get("domain", ""),
        "issuer":         raw.get("issuer", ""),
        "valid_from":     not_before.isoformat() if not_before else "",
        "valid_to":       not_after.isoformat()  if not_after  else "",
        "days_remaining": days if days is not None else -1,
        "is_valid":       (days is not None and days > 0),
        "serial_number":  raw.get("serial_number"),
        "fingerprint":    raw.get("fingerprint"),
    }


@router.get("/certificates", response_model=CertificateMonitorResponse)
async def list_certificates(
    threshold_days: int = 30,
    current_user: User = Depends(require_admin),
):
    """
    获取 SSL 证书监控信息（仅限项目运维域名，非业务域名）
    读取宿主机 /etc/letsencrypt/live/ 下的证书（只读挂载）
    实际续期由宿主机 certbot 自动完成，此处仅做状态监控
    """
    try:
        raw_certs = ssl_service.list_all_certificates()
        certificates = [_to_cert_info(c, threshold_days) for c in raw_certs]
        return CertificateMonitorResponse(
            success=True,
            certificates=certificates,
            total=len(certificates),
            valid_count=sum(1 for c in certificates if c["is_valid"]),
            expiring_soon_count=sum(
                1 for c in certificates
                if c["is_valid"] and c["days_remaining"] <= threshold_days
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取证书信息失败: {str(e)}"
        )


@router.post("/alerts", response_model=CertificateAlertResponse)
async def get_certificate_alerts(
    request: CertificateAlertRequest,
    current_user: User = Depends(require_admin),
):
    """
    获取证书告警信息

    返回即将过期的证书列表，用于发送告警通知
    """
    try:
        alert_domains = ssl_service.get_expiring_certificates(request.threshold_days)
        return CertificateAlertResponse(
            success=True,
            alert_domains=alert_domains,
            alert_count=len(alert_domains)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取证书告警失败: {str(e)}"
        )


@router.get("/health")
async def check_ssl_health(
    current_user: User = Depends(require_admin),
):
    """
    检查SSL服务健康状态

    返回SSL证书监控服务的状态
    """
    try:
        raw_certs = ssl_service.list_all_certificates()
        certs = [_to_cert_info(c, 30) for c in raw_certs]
        return {
            "status": "ok",
            "monitored_domains": len(certs),
            "valid_certificates": sum(1 for c in certs if c["is_valid"]),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SSL健康检查失败: {str(e)}"
        )
