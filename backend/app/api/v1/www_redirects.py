"""POST /www-redirects：返回单个配置结果对象。

权限：沿用飞书按钮的可选 verification_token 校验，申请人必须为启用的
domain_spec/super_admin；校验域名及 DNS 账号归属。
仅操作域名规则和解析，不修改服务商账号/关键系统配置，无需超管二次确认。
业务用户不能以个人身份直接执行；业务申请继续走原有飞书审批入口。
"""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import Config
from app.core.database import get_db
from app.models.user import User
from app.services.user_service import UserService
from app.services.www_redirect_service import WwwRedirectService


class WwwRedirectBody(BaseModel):
    domain: Optional[str] = Field(default=None, max_length=2048)
    doc_url: Optional[str] = Field(default=None, max_length=4096)
    applicant_feishu_id: str = Field(min_length=1)
    verification_token: Optional[str] = None


def resolve_www_redirect_body(
    body: Optional[WwwRedirectBody] = Body(default=None),
    domain: Optional[str] = Query(default=None, max_length=2048),
    doc_url: Optional[str] = Query(default=None, max_length=4096),
    applicant_feishu_id: Optional[str] = Query(default=None),
    verification_token: Optional[str] = Query(default=None),
) -> WwwRedirectBody:
    # 与旧按钮接口一致：有 JSON body 时以 body 为准，否则使用查询参数。
    if body is not None:
        return body
    if not applicant_feishu_id:
        raise HTTPException(422, "缺少必要参数: applicant_feishu_id")
    return WwwRedirectBody(
        domain=domain, doc_url=doc_url, applicant_feishu_id=applicant_feishu_id,
        verification_token=verification_token,
    )


def require_www_redirect(
    body: WwwRedirectBody = Depends(resolve_www_redirect_body),
    db: Session = Depends(get_db),
) -> User:
    # 保持 /feishu/doc-button/submit 的兼容语义：两端都有 Token 才比较。
    if Config.FEISHU_VERIFICATION_TOKEN and body.verification_token:
        if body.verification_token != Config.FEISHU_VERIFICATION_TOKEN:
            raise HTTPException(403, "verification_token 不正确")
    user = UserService(db).get_user_by_name_or_feishu_id(body.applicant_feishu_id)
    if not user or not user.is_active or user.role not in ("domain_spec", "super_admin"):
        raise HTTPException(403, "申请人必须是启用的域名专员或超级管理员")
    return user


router = APIRouter(prefix="/www-redirects", tags=["www 重定向"])


@router.post("", dependencies=[Depends(require_www_redirect)])
def create_www_redirect(
    body: WwwRedirectBody = Depends(resolve_www_redirect_body),
    actor: User = Depends(require_www_redirect),
    db: Session = Depends(get_db),
):
    return WwwRedirectService(db).configure(actor, body.domain, body.doc_url)
