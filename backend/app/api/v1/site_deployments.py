"""Site deployment orchestration API.

Permission: POST requires require_domain_spec (domain_spec/super_admin).
Super-admin confirmation: not required; this is an operator-triggered deployment workflow.
Return format: object with deployment and post-deploy API results.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import require_domain_spec
from app.core.database import get_db
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.site_deployment_service import SiteDeploymentError, SiteDeploymentService

router = APIRouter(prefix="/site-deployments", tags=["Site deployments"])


class SiteDeploymentRequest(BaseModel):
    domain: Optional[str] = Field(default=None, description="Base domain or svc domain")
    doc_url: Optional[str] = Field(default=None, description="Feishu doc URL used when domain is omitted")
    operator_name: str = Field(..., min_length=1, max_length=100)
    website_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    appid: Optional[str] = Field(default=None, min_length=1, max_length=64)
    authors: Optional[list[str]] = Field(default=None, description="Frontend authors for auto-site API")
    timeout_seconds: Optional[int] = Field(default=None, ge=10, le=1800)
    poll_interval_seconds: Optional[float] = Field(default=None, ge=1, le=30)


@router.post("", dependencies=[Depends(require_domain_spec)])
def deploy_site(
    data: SiteDeploymentRequest,
    current_user: User = Depends(require_domain_spec),
    db: Session = Depends(get_db),
):
    service = SiteDeploymentService()
    audit = AuditService(db)
    try:
        result = service.deploy_and_notify(
            domain=data.domain,
            doc_url=data.doc_url,
            operator_name=data.operator_name.strip(),
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
            user_id=current_user.id,
            user_name=current_user.name,
            after_state={
                "operator_name": data.operator_name.strip(),
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
            resource_name=data.domain,
            user_id=current_user.id,
            user_name=current_user.name,
            after_state={
                "operator_name": data.operator_name.strip(),
                "doc_url": data.doc_url,
                "website_name": data.website_name,
                "appid": data.appid,
                "authors": data.authors,
            },
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
