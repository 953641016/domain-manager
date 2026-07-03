"""Site deployment orchestration API.

Permission: POST requires applicant_feishu_id; domain_spec/super_admin can operate directly, business users must be active and assigned to a domain specialist.
Super-admin confirmation: not required; this is an operator-triggered deployment workflow.
Return format: object with deployment and post-deploy API results.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import Config
from app.core.database import get_db
from app.services.audit_service import AuditService
from app.services.site_deployment_service import SiteDeploymentError, SiteDeploymentService
from app.services.user_service import UserService

router = APIRouter(prefix="/site-deployments", tags=["Site deployments"])


class SiteDeploymentRequest(BaseModel):
    register_domain: Optional[str] = Field(default=None, description="Base domain or svc domain")
    doc_url: Optional[str] = Field(default=None, description="Feishu doc URL used when register_domain is omitted")
    applicant_feishu_id: str = Field(..., min_length=1, max_length=100)
    website_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    appid: Optional[str] = Field(default=None, min_length=1, max_length=64)
    authors: Optional[list[str]] = Field(default=None, description="Frontend authors for auto-site API")
    verification_token: Optional[str] = Field(default=None, max_length=200)
    timeout_seconds: Optional[int] = Field(default=None, ge=10, le=1800)
    poll_interval_seconds: Optional[float] = Field(default=None, ge=1, le=30)


async def require_site_deployment_applicant(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    applicant_feishu_id = str(payload.get("applicant_feishu_id") or "").strip()
    if not applicant_feishu_id:
        raise HTTPException(status_code=422, detail="缺少必要参数: applicant_feishu_id")

    verification_token = str(payload.get("verification_token") or "").strip()
    if Config.FEISHU_VERIFICATION_TOKEN and verification_token:
        if verification_token != Config.FEISHU_VERIFICATION_TOKEN:
            raise HTTPException(status_code=403, detail="verification_token 不正确")

    user_svc = UserService(db)
    applicant = user_svc.get_user_by_name_or_feishu_id(applicant_feishu_id)
    if not applicant or not applicant.is_active:
        raise HTTPException(status_code=403, detail="申请人不存在或已禁用")

    specialist = None
    if applicant.role in ("domain_spec", "super_admin"):
        specialist = applicant
    else:
        if not getattr(applicant, "assigned_specialist_id", None):
            raise HTTPException(status_code=403, detail="申请人尚未分配归属专员，无法提交申请")
        specialist = user_svc.get_user(applicant.assigned_specialist_id)
        if not specialist or not specialist.is_active or specialist.role not in ("domain_spec", "super_admin"):
            raise HTTPException(status_code=400, detail="未找到可执行的归属域名专员")

    request.state.site_deployment_applicant = applicant
    request.state.site_deployment_specialist = specialist


@router.post("", dependencies=[Depends(require_site_deployment_applicant)])
def deploy_site(
    data: SiteDeploymentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    service = SiteDeploymentService()
    audit = AuditService(db)
    applicant = getattr(request.state, "site_deployment_applicant", None)
    specialist = getattr(request.state, "site_deployment_specialist", None)
    operator_name = getattr(applicant, "name", None) or data.applicant_feishu_id.strip()
    try:
        result = service.deploy_and_notify(
            domain=data.register_domain,
            doc_url=data.doc_url,
            operator_name=operator_name,
            website_name=data.website_name.strip() if data.website_name else None,
            appid=data.appid.strip() if data.appid else None,
            authors=data.authors,
            timeout_seconds=data.timeout_seconds,
            poll_interval_seconds=data.poll_interval_seconds,
        )
        audit.log(
            action="deploy_nginx_site",
            resource_type="site_deployment",
            resource_name=result.get("service_domain"),
            user_id=getattr(applicant, "id", None),
            user_name=getattr(applicant, "name", None) or data.applicant_feishu_id,
            after_state={
                "applicant_feishu_id": data.applicant_feishu_id.strip(),
                "specialist_id": getattr(specialist, "id", None),
                "specialist_name": getattr(specialist, "name", None),
                "operator_name": operator_name,
                "register_domain": data.register_domain,
                "doc_url": data.doc_url,
                "website_name": data.website_name,
                "appid": data.appid,
                "authors": data.authors,
                "result": result,
            },
            status="success" if result.get("success") else "failed",
            error_message=(result.get("deploy_result") or {}).get("error"),
        )
        return result
    except (ValueError, SiteDeploymentError) as exc:
        audit.log(
            action="deploy_nginx_site",
            resource_type="site_deployment",
            resource_name=data.register_domain,
            user_id=getattr(applicant, "id", None),
            user_name=getattr(applicant, "name", None) or data.applicant_feishu_id,
            after_state={
                "applicant_feishu_id": data.applicant_feishu_id.strip(),
                "specialist_id": getattr(specialist, "id", None),
                "specialist_name": getattr(specialist, "name", None),
                "operator_name": operator_name,
                "register_domain": data.register_domain,
                "doc_url": data.doc_url,
                "website_name": data.website_name,
                "appid": data.appid,
                "authors": data.authors,
            },
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
