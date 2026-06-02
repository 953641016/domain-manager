"""
飞书相关API路由
提供OAuth授权、用户信息获取、webhook事件处理等接口
"""
from fastapi import APIRouter, Body, HTTPException, Query, Request, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.config import Config
from app.services.feishu_service import feishu_service
from app.bots.feishu import feishu_bot
from app.core.database import get_db, SessionLocal


router = APIRouter(
    prefix="/feishu",
    tags=["飞书集成"],
)

# ── 已知 section 列表 ──────────────────────────────────────
SECTIONS_WITH_BITABLE = {
    "vercel":           {"label": "Vercel 域名解析",     "request_type": "dns_record"},
    "clerk":            {"label": "Clerk 域名解析",      "request_type": "dns_record"},
    "cf_redirect":      {"label": "CF 域名跳转解析",     "request_type": "dns_record"},
    "gsc":              {"label": "GSC 网站认证解析",    "request_type": "dns_record"},
    "api_domain":       {"label": "接口域名解析",         "request_type": "dns_record"},
    "email":            {"label": "网站邮箱支持解析",    "request_type": "dns_record"},
}
SECTIONS_NO_BITABLE = {
    "domain_register":  {"label": "域名注册",            "request_type": "domain_register"},
}

DOC_BUTTON_ACTIONS = {
    "domain_purchase": {"label": "购买域名", "request_type": "domain_register"},
    "clerk_dns": {"label": "Clerk 域名解析", "request_type": "dns_record"},
    "backend_dns": {"label": "后端接口服务域名解析", "request_type": "dns_record"},
    "vercel_dns": {"label": "Vercel 域名解析", "request_type": "dns_record"},
    "cf_dns": {"label": "CF 域名解析", "request_type": "dns_record"},
    "gsc_dns": {"label": "GSC 网站认证解析", "request_type": "dns_record"},
    "all_dns_except_gsc": {"label": "一键解析 Clerk + 后端 + Vercel + CF", "request_type": "dns_record"},
}


def _format_card_time(value) -> str:
    if not value:
        return "—"
    try:
        from datetime import timedelta, timezone
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone(timedelta(hours=8)))
        return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


class FeishuUserInfo(BaseModel):
    """飞书用户信息响应模型"""
    user_id: str
    name: str
    en_name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    avatar_url: Optional[str] = None
    union_id: Optional[str] = None
    open_id: Optional[str] = None
    department_name: Optional[str] = None


@router.get("/oauth-url")
async def get_feishu_oauth_url(
    redirect_uri: str = Query(..., description="回调地址")
):
    """
    获取飞书OAuth授权URL
    前端用这个URL生成二维码，用户扫码后会跳转到redirect_uri
    """
    try:
        oauth_url = feishu_service.get_oauth_url(redirect_uri)
        return {
            "success": True,
            "oauth_url": oauth_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成OAuth URL失败: {str(e)}")


@router.get("/user-info", response_model=FeishuUserInfo)
async def get_feishu_user_info(
    code: str = Query(..., description="OAuth授权码")
):
    """
    通过OAuth code获取用户信息
    用户扫码后，前端拿到code，调用此接口获取用户详情
    """
    try:
        user_data = feishu_service.get_user_info_by_code(code)
        
        # 格式化返回数据
        return FeishuUserInfo(
            user_id=user_data.get("user_id", ""),
            name=user_data.get("name", ""),
            en_name=user_data.get("en_name"),
            email=user_data.get("email"),
            mobile=user_data.get("mobile"),
            avatar_url=user_data.get("avatar_url"),
            union_id=user_data.get("union_id"),
            open_id=user_data.get("open_id"),
            department_name=user_data.get("department_name")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取用户信息失败: {str(e)}")


@router.get("/search-users")
async def search_feishu_users(
    keyword: str = Query(..., min_length=1, description="搜索关键词（姓名）")
):
    """
    按姓名搜索飞书用户
    用于新增用户时快速查找飞书用户ID
    """
    try:
        users = feishu_service.search_users_by_name(keyword)
        return {
            "success": True,
            "users": users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索用户失败: {str(e)}")


@router.get("/user/{user_id}")
async def get_user_by_id(
    user_id: str
):
    """
    通过飞书用户ID获取用户详情
    用于已知道用户ID时获取信息
    """
    try:
        user_data = feishu_service.get_user_by_user_id(user_id)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "success": True,
            "user": user_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")


@router.post("/webhook")
async def feishu_webhook(request: Request):
    """
    飞书事件回调处理接口
    处理URL验证、消息接收、卡片按钮回调等事件
    """
    import logging
    _log = logging.getLogger("feishu.webhook")
    try:
        # 解析请求体
        request_body = await request.json()

        _log.info("feishu webhook body keys=%s type=%s",
                  list(request_body.keys()),
                  request_body.get("type") or request_body.get("header", {}).get("event_type"))

        # 签名验证：兼容 schema 1.0（token 在根节点）和 2.0（token 在 header）
        token_in_body = (
            request_body.get("token")
            or request_body.get("header", {}).get("token")
        )
        if not feishu_service.verify_webhook_signature_token(token_in_body):
            _log.warning("feishu webhook 签名验证失败 token=%s", token_in_body)
            raise HTTPException(status_code=403, detail="签名验证失败")

        # 处理URL验证请求
        if request_body.get("type") == "url_verification":
            return feishu_service.handle_url_verification(request_body)

        # 处理其他事件
        event_type = request_body.get("header", {}).get("event_type")

        if event_type == "im.message.receive_v1":
            event = request_body.get("event", {})
            await feishu_bot.handle_message(event)
            return {"success": True, "message": "消息已接收"}

        # 处理卡片按钮回调（超管点击授权/拒绝账号操作）
        if request_body.get("type") == "card" or event_type == "card.action.trigger":
            _log.info("feishu card action received")
            return await _handle_card_action(request_body)

        # 默认响应
        return {"success": True, "message": "事件已接收"}

    except HTTPException:
        raise
    except Exception as e:
        import logging as _l
        _l.getLogger("feishu.webhook").exception("处理webhook失败")
        raise HTTPException(status_code=500, detail=f"处理webhook失败: {str(e)}")


class SendMessageRequest(BaseModel):
    """发送消息请求模型"""
    receive_id: str
    content: str
    receive_id_type: str = "open_id"


@router.post("/send-message")
async def send_message(request: SendMessageRequest):
    """
    发送飞书消息接口
    """
    try:
        result = feishu_service.send_text_message(
            receive_id=request.receive_id,
            content=request.content,
            receive_id_type=request.receive_id_type
        )
        
        if result.get("code") != 0:
            raise HTTPException(status_code=400, detail=f"发送消息失败: {result}")
        
        return {
            "success": True,
            "data": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


class SendCardRequest(BaseModel):
    """发送卡片消息请求模型"""
    receive_id: str
    card_content: Dict[str, Any]
    receive_id_type: str = "open_id"


@router.post("/send-card")
async def send_card(request: SendCardRequest):
    """
    发送飞书交互式卡片接口
    """
    try:
        result = feishu_service.send_card_message(
            receive_id=request.receive_id,
            card_content=request.card_content,
            receive_id_type=request.receive_id_type
        )
        
        if result.get("code") != 0:
            raise HTTPException(status_code=400, detail=f"发送卡片失败: {result}")
        
        return {
            "success": True,
            "data": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送卡片失败: {str(e)}")


# ════════════════════════════════════════════════════════════
# 飞书文档按钮申请
# 权限：调用方需传入 applicant_feishu_id，后端校验申请人存在、启用且已归属域名专员。
# 超管确认：该业务申请先进入域名专员审批卡片；审批通过后才执行注册或解析。
# 返回格式：对象 {success, request_id, action, domain, records_count}。
# ════════════════════════════════════════════════════════════


class DocButtonSubmitBody(BaseModel):
    action: str
    doc_url: str
    doc_format: str = "standard_v1"
    applicant_feishu_id: str
    source: str = "feishu_doc_button"
    verification_token: Optional[str] = None


@router.post("/doc-button/submit")
def submit_doc_button_request(
    body: Optional[DocButtonSubmitBody] = Body(default=None),
    action: Optional[str] = Query(default=None),
    doc_url: Optional[str] = Query(default=None),
    doc_format: str = Query(default="standard_v1"),
    applicant_feishu_id: Optional[str] = Query(default=None),
    source: str = Query(default="feishu_doc_button"),
    verification_token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """飞书文档/多维表格按钮触发：读取文档内容，创建待审批申请，发送审批卡片。"""
    from app.services.user_service import UserService
    from app.services.request_service import RequestService
    from app.services.feishu_doc_parser import FeishuDocParser
    from app.schemas.request import RequestCreate

    if body is None:
        if not action or not doc_url or not applicant_feishu_id:
            raise HTTPException(status_code=422, detail="缺少必要参数: action、doc_url、applicant_feishu_id")
        body = DocButtonSubmitBody(
            action=action,
            doc_url=doc_url,
            doc_format=doc_format,
            applicant_feishu_id=applicant_feishu_id,
            source=source,
            verification_token=verification_token,
        )

    if Config.FEISHU_VERIFICATION_TOKEN and body.verification_token:
        if body.verification_token != Config.FEISHU_VERIFICATION_TOKEN:
            raise HTTPException(status_code=403, detail="verification_token 不正确")

    action_meta = DOC_BUTTON_ACTIONS.get(body.action)
    if not action_meta:
        raise HTTPException(status_code=400, detail=f"未知 action: {body.action}")

    user_svc = UserService(db)
    applicant = user_svc.get_user_by_name_or_feishu_id(body.applicant_feishu_id)
    if not applicant or not applicant.is_active:
        raise HTTPException(status_code=403, detail="申请人不存在或已禁用")
    if not getattr(applicant, "assigned_specialist_id", None):
        raise HTTPException(status_code=403, detail="申请人尚未分配归属专员，无法提交申请")

    specialist = user_svc.get_user(applicant.assigned_specialist_id)
    if not specialist or specialist.role not in ("domain_spec", "super_admin"):
        raise HTTPException(status_code=400, detail="未找到可审批的归属域名专员")

    try:
        parsed = FeishuDocParser().parse(body.doc_url, body.action, body.doc_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    request_data = {
        "action": body.action,
        "action_label": action_meta["label"],
        "doc_url": body.doc_url,
        "doc_token": parsed.doc_token,
        "doc_title": parsed.title,
        "doc_format": body.doc_format,
        "records": parsed.records,
    }
    if parsed.request_type == "domain_register":
        request_data["domain"] = parsed.domain
    else:
        request_data["dns_provider"] = body.action
        request_data["domain"] = parsed.domain

    if parsed.request_type == "domain_register":
        accounts = _get_reviewable_reg_accounts(db, specialist)
        if not accounts:
            raise HTTPException(status_code=400, detail="归属域名专员没有可用注册账号")
        request_data["price_quotes"] = _quote_reg_account_prices(db, parsed.domain, accounts)
        default_account = _pick_default_reg_account(db, specialist, accounts)
        if default_account:
            request_data["default_reg_account_id"] = default_account.id
            request_data["default_registrar_code"] = default_account.registrar_code
    else:
        accounts = _get_reviewable_dns_accounts(db, specialist)
        if not accounts:
            raise HTTPException(status_code=400, detail="归属域名专员没有可用 DNS 账号")

    req_svc = RequestService(db)
    if parsed.request_type == "domain_register":
        existing = req_svc.get_active_domain_register_request(parsed.domain)
        if existing:
            if existing.status != "pending":
                return {
                    "success": True,
                    "already_processed": True,
                    "request_id": existing.id,
                    "status": existing.status,
                    "action": body.action,
                    "domain": parsed.domain,
                    "records_count": 0,
                    "message": "该域名购买申请已处理，不会重复提交或重复购买",
                }
            existing_data = dict(existing.request_data or {})
            existing_data.update({
                "action": body.action,
                "action_label": action_meta["label"],
                "doc_url": body.doc_url,
                "doc_token": parsed.doc_token,
                "doc_title": parsed.title,
                "doc_format": body.doc_format,
                "domain": parsed.domain,
                "price_quotes": request_data.get("price_quotes"),
                "default_reg_account_id": request_data.get("default_reg_account_id"),
                "default_registrar_code": request_data.get("default_registrar_code"),
            })
            existing.request_data = existing_data
            db.commit()
            db.refresh(existing)
            send_result = _send_doc_request_approval_card(existing, applicant, specialist, accounts)
            return {
                "success": True,
                "resent": True,
                "request_id": existing.id,
                "action": body.action,
                "domain": parsed.domain,
                "records_count": len((existing.request_data or {}).get("records") or []),
                "message": "该域名已有待审批申请，已重新发送审批卡片",
                "feishu_code": send_result.get("code"),
                "feishu_message_id": (send_result.get("data") or {}).get("message_id"),
            }

    req = req_svc.create_request(
        data=RequestCreate(
            type=parsed.request_type,
            domain_name=parsed.domain,
            request_data=request_data,
            source=body.source,
        ),
        requester_id=applicant.id,
        requester_name=applicant.name,
    )

    result = _send_doc_request_approval_card(req, applicant, specialist, accounts)

    return {
        "success": True,
        "request_id": req.id,
        "action": body.action,
        "domain": parsed.domain,
        "records_count": len(parsed.records),
    }


def _send_doc_request_approval_card(req, applicant, specialist, accounts: List[Any]) -> Dict[str, Any]:
    if req.type == "domain_register":
        card = _build_domain_purchase_approval_card(req, applicant, specialist, accounts)
    else:
        card = _build_dns_doc_approval_card(req, applicant, specialist, accounts)

    receive_id = getattr(specialist, "feishu_open_id", None) or getattr(specialist, "feishu_user_id", None)
    receive_type = "open_id" if getattr(specialist, "feishu_open_id", None) else "user_id"
    if not receive_id:
        raise HTTPException(status_code=400, detail="归属域名专员未配置飞书 ID，无法发送审批卡片")
    result = feishu_service.send_card_message(receive_id, card, receive_type)
    if result.get("code") != 0:
        raise HTTPException(status_code=502, detail=f"发送审批卡片失败: {result}")
    return result


def _get_reviewable_reg_accounts(db: Session, reviewer) -> List[Any]:
    from app.models.domain import RegAccount
    query = db.query(RegAccount).filter(RegAccount.is_active == True)  # noqa: E712
    if reviewer.role != "super_admin":
        query = query.filter(RegAccount.owner_id == reviewer.id)
    return query.order_by(RegAccount.name.asc()).all()


def _get_reviewable_dns_accounts(db: Session, reviewer) -> List[Any]:
    from app.models.domain import DnsAccount
    query = db.query(DnsAccount).filter(DnsAccount.is_active == True)  # noqa: E712
    if reviewer.role != "super_admin":
        query = query.filter(DnsAccount.owner_id == reviewer.id)
    return query.order_by(DnsAccount.name.asc()).all()


def _pick_default_reg_account(db: Session, reviewer, accounts: List[Any]):
    from app.models.system import SystemDefaults

    account_map = {account.id: account for account in accounts}
    defaults = db.query(SystemDefaults).filter(SystemDefaults.user_id == reviewer.id).first()
    if defaults and defaults.default_reg_account_id in account_map:
        return account_map[defaults.default_reg_account_id]
    return accounts[0] if accounts else None


def _select_options(accounts: List[Any], code_attr: str) -> List[Dict[str, Any]]:
    return [
        {
            "text": {"tag": "plain_text", "content": f"{account.name}（{getattr(account, code_attr)}）"},
            "value": str(account.id),
        }
        for account in accounts
    ]


def _format_price_quote(quote: Optional[Dict[str, Any]]) -> str:
    if not quote:
        return "价格获取失败"
    if not quote.get("check_successful"):
        message = quote.get("message") or ""
        if "Network is unreachable" in message or "Failed to establish a new connection" in message:
            return "价格获取失败：网络不可达"
        if "timeout" in message.lower() or "timed out" in message.lower():
            return "价格获取失败：接口超时"
        if len(message) > 40:
            return "价格获取失败"
        return message or "价格获取失败"
    if quote.get("available") is False:
        return quote.get("message") or "不可注册"
    price = quote.get("price")
    currency = quote.get("currency") or "USD"
    if price is None:
        return "可注册，价格未返回"
    return f"{price} {currency}"


def _quote_reg_account_prices(db: Session, domain: str, accounts: List[Any]) -> Dict[str, Dict[str, Any]]:
    from app.services.domain_service import DomainService
    from app.adapters.registrar_factory import RegistrarFactory

    domain_svc = DomainService(db)
    quotes: Dict[str, Dict[str, Any]] = {}
    for account in accounts:
        try:
            decrypted = domain_svc.get_reg_account_decrypted(account.id)
            if not decrypted or not decrypted.api_key:
                raise ValueError("账号未配置 API 凭据")
            account_id = decrypted.api_secret if decrypted.registrar_code == "cloudflare" else None
            adapter = RegistrarFactory.create_registrar(
                decrypted.registrar_code,
                decrypted.api_key,
                decrypted.api_secret,
                account_id=account_id,
            )
            quote = adapter.check_domain_availability(domain) or {}
            quotes[str(account.id)] = {
                "account_id": account.id,
                "account_name": account.name,
                "registrar_code": account.registrar_code,
                "available": quote.get("available"),
                "price": quote.get("price"),
                "currency": quote.get("currency"),
                "message": quote.get("message"),
                "tier": quote.get("tier"),
                "check_successful": bool(quote.get("check_successful")),
            }
        except Exception as e:
            quotes[str(account.id)] = {
                "account_id": account.id,
                "account_name": account.name,
                "registrar_code": account.registrar_code,
                "available": None,
                "price": None,
                "currency": None,
                "message": f"价格获取失败: {str(e)}",
                "check_successful": False,
            }
    return quotes


def _reg_account_options_with_prices(accounts: List[Any], quotes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    options = []
    for account in accounts:
        quote = quotes.get(str(account.id))
        price_text = _format_price_quote(quote)
        options.append({
            "text": {"tag": "plain_text", "content": f"{price_text} | {account.registrar_code} | {account.name}"},
            "value": str(account.id),
        })
    return options


def _reg_price_quote_lines(accounts: List[Any], quotes: Dict[str, Dict[str, Any]]) -> str:
    lines = []
    for account in accounts:
        quote = quotes.get(str(account.id))
        price_text = _format_price_quote(quote)
        lines.append(f"- **{account.name}**（{account.registrar_code}）：{price_text}")
    return "\n".join(lines) or "暂无可用注册服务商报价"


def _build_domain_purchase_approval_card(req, applicant, reviewer, accounts: List[Any]) -> Dict[str, Any]:
    data = req.request_data or {}
    quotes = data.get("price_quotes") or {}
    account_options = _reg_account_options_with_prices(accounts, quotes)
    price_quote_lines = _reg_price_quote_lines(accounts, quotes)
    default_account_id = str(data.get("default_reg_account_id") or (accounts[0].id if accounts else ""))
    initial_option = next((opt for opt in account_options if opt.get("value") == default_account_id), account_options[0])
    initial_option_text = initial_option.get("text", {}).get("content") or ""
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🛒 域名购买申请"},
            "template": "orange",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**域名**：{req.domain_name}\n"
                        f"**申请人**：{applicant.name}\n"
                        f"**申请时间**：{_format_card_time(req.created_at)}\n"
                        f"**来源文档**：[{data.get('doc_title', '飞书文档')}]({data.get('doc_url', '')})\n"
                        f"**注册服务商**：请在下方选择\n"
                        f"**预估价格**：见下方服务商报价，最终以审批执行时重新查价为准"
                    ),
                },
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**服务商报价**\n{price_quote_lines}",
                },
            },
            {
                "tag": "form",
                "name": "domain_register_approval_form",
                "elements": [
                    {
                        "tag": "select_static",
                        "placeholder": {"tag": "plain_text", "content": "选择注册服务商"},
                        "initial_option": initial_option_text,
                        "options": account_options,
                        "name": "selected_reg_account_id",
                        "required": True,
                    },
                    {
                        "tag": "select_static",
                        "placeholder": {"tag": "plain_text", "content": "选择注册年限"},
                        "initial_option": "1 年",
                        "options": [
                            {"text": {"tag": "plain_text", "content": "1 年"}, "value": "1"},
                            {"text": {"tag": "plain_text", "content": "2 年"}, "value": "2"},
                            {"text": {"tag": "plain_text", "content": "3 年"}, "value": "3"},
                        ],
                        "name": "register_years",
                        "required": True,
                    },
                    {
                        "tag": "input",
                        "name": "reject_reason",
                        "placeholder": {"tag": "plain_text", "content": "拒绝理由（可选）"},
                    },
                    {
                        "tag": "button",
                        "name": "approve_domain_register",
                        "action_type": "form_submit",
                        "text": {"tag": "plain_text", "content": "✅ 批准并执行"},
                        "type": "primary",
                        "value": {"action": "approve_doc_request", "request_id": req.id},
                    },
                    {
                        "tag": "button",
                        "name": "reject_domain_register",
                        "action_type": "form_submit",
                        "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                        "type": "danger",
                        "value": {"action": "reject_doc_request", "request_id": req.id},
                    },
                ],
            },
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"审批人：{reviewer.name}；申请编号：#{req.id[:8]}"}]},
        ],
    }


def _build_dns_doc_approval_card(req, applicant, reviewer, accounts: List[Any]) -> Dict[str, Any]:
    data = req.request_data or {}
    records = data.get("records") or []
    preview = "\n".join(
        f"• `{r.get('hostname')}` {r.get('type')} → {r.get('target') or '待配置'}"
        for r in records[:12]
    )
    if len(records) > 12:
        preview += f"\n... 另有 {len(records) - 12} 条"
    account_options = _select_options(accounts, "provider_code")
    initial_option_text = account_options[0].get("text", {}).get("content") if account_options else ""
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🌐 DNS 解析申请"},
            "template": "blue",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**申请类型**：{data.get('action_label', req.type)}\n"
                        f"**主域名**：{req.domain_name}\n"
                        f"**申请人**：{applicant.name}\n"
                        f"**申请时间**：{_format_card_time(req.created_at)}\n"
                        f"**记录数**：{len(records)}\n"
                        f"**来源文档**：[{data.get('doc_title', '飞书文档')}]({data.get('doc_url', '')})"
                    ),
                },
            },
            {"tag": "hr"},
            {"tag": "div", "text": {"tag": "lark_md", "content": preview or "无记录"}},
            {
                "tag": "form",
                "name": "dns_doc_approval_form",
                "elements": [
                    {
                        "tag": "select_static",
                        "placeholder": {"tag": "plain_text", "content": "选择 DNS 账号"},
                        "initial_option": initial_option_text,
                        "options": account_options,
                        "name": "selected_dns_account_id",
                        "required": True,
                    },
                    {
                        "tag": "input",
                        "name": "approval_comment",
                        "placeholder": {"tag": "plain_text", "content": "审核备注（可选）"},
                    },
                    {
                        "tag": "input",
                        "name": "reject_reason",
                        "placeholder": {"tag": "plain_text", "content": "拒绝理由（可选）"},
                    },
                    {
                        "tag": "button",
                        "name": "approve_dns_doc",
                        "action_type": "form_submit",
                        "text": {"tag": "plain_text", "content": "✅ 批准并执行"},
                        "type": "primary",
                        "value": {"action": "approve_doc_request", "request_id": req.id},
                    },
                    {
                        "tag": "button",
                        "name": "reject_dns_doc",
                        "action_type": "form_submit",
                        "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                        "type": "danger",
                        "value": {"action": "reject_doc_request", "request_id": req.id},
                    },
                ],
            },
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"审批人：{reviewer.name}；申请编号：#{req.id[:8]}"}]},
        ],
    }


# ════════════════════════════════════════════════════════════
# 移动端 HTML 模板工具
# ════════════════════════════════════════════════════════════

def _html_page(
    title: str,
    icon: str,
    heading: str,
    body: str,
    auto_close_ms: int = 0,
) -> str:
    """
    生成移动端友好的结果页 HTML。
    所有扫码回调页统一使用此模板，确保在飞书 App 内置浏览器中正常显示。
    """
    close_script = (
        f'<script>setTimeout(function(){{window.close();}},{auto_close_ms});</script>'
        if auto_close_ms else ""
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',sans-serif;
         background:#f5f6fa;display:flex;align-items:center;justify-content:center;
         min-height:100vh;padding:24px 16px}}
    .card{{background:#fff;border-radius:16px;padding:44px 28px 36px;
           max-width:400px;width:100%;text-align:center;
           box-shadow:0 4px 24px rgba(0,0,0,.09)}}
    .icon{{font-size:52px;margin-bottom:18px;line-height:1}}
    h2{{font-size:20px;font-weight:600;color:#1a1a1a;margin-bottom:14px}}
    p{{font-size:15px;color:#666;line-height:1.75;margin-top:6px}}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h2>{heading}</h2>
    {body}
  </div>
  {close_script}
</body>
</html>"""


@router.get("/add-user-callback")
async def add_user_callback(
    code: str = Query(..., description="飞书授权码"),
    db: Session = Depends(get_db),
):
    """
    扫码添加用户回调（经超管飞书确认后才真正创建）
    用户扫码 → 获取飞书信息 → 发超管确认卡片 → 超管批准 → 创建用户
    """
    try:
        from app.services.user_service import UserService
        from app.services.user_confirmation_service import UserOperationConfirmationService
        from app.models.user_confirmation import ConfirmationOperationType

        user_info = feishu_service.get_user_info_by_code(code)
        if not user_info:
            raise HTTPException(status_code=400, detail="获取用户信息失败")

        user_service = UserService(db)
        feishu_user_id = user_info.get("user_id") or user_info.get("open_id", "")
        if not feishu_user_id:
            raise HTTPException(status_code=400, detail="未获取到用户ID")

        existing_user = user_service.get_user_by_feishu_userid(feishu_user_id)
        if existing_user:
            return HTMLResponse(content=_html_page(
                title="已在系统中",
                icon="✅",
                heading=f"{existing_user.name} 已在系统中",
                body="<p>无需重复添加，您已可以正常登录使用。</p>",
                auto_close_ms=2500,
            ))

        # 发超管确认卡片，由超管审批后才创建用户
        conf_svc = UserOperationConfirmationService(db)
        super_admin = conf_svc.get_super_admin()
        if not super_admin:
            # 系统尚未配置超管，临时直接创建（冷启动场景）
            from app.schemas.user import UserCreate
            user_create = UserCreate(
                name=user_info.get("name", "未知用户"),
                feishu_user_id=feishu_user_id,
                feishu_union_id=user_info.get("union_id"),
                feishu_open_id=user_info.get("open_id"),
                role="business",
                email=user_info.get("email"),
                phone=user_info.get("mobile"),
                department=user_info.get("department_name"),
            )
            user_service.create_user(user_create)
            return HTMLResponse(content=_html_page(
                title="添加成功",
                icon="🎉",
                heading="账号已创建",
                body="<p>系统初始化模式，已直接创建账号，现在可以登录使用。</p>",
                auto_close_ms=3000,
            ))

        # 幂等拦截：同一飞书用户若已有待审批的申请，不再重复创建
        from app.models.user_confirmation import UserOperationConfirmation, ConfirmationStatus
        pending = db.query(UserOperationConfirmation).filter(
            UserOperationConfirmation.initiator_feishu_userid == feishu_user_id,
            UserOperationConfirmation.status == ConfirmationStatus.PENDING,
        ).first()
        if pending:
            name = user_info.get("name", "您")
            return HTMLResponse(content=_html_page(
                title="申请待审批",
                icon="⏳",
                heading="申请正在审批中",
                body=f"<p>{name}，您的加入申请已提交，正在等待超级管理员审批。</p><p>请耐心等候飞书通知，无需重复扫码。</p>",
                auto_close_ms=4000,
            ))

        # 使用超管 ID 作为发起人（扫码人尚无系统账号）
        conf = conf_svc.create_confirmation(
            operation_type=ConfirmationOperationType.ADD_DOMAIN_SPEC,
            initiator_user_id=super_admin.id,
            initiator_name=user_info.get("name", "未知用户"),
            initiator_feishu_userid=feishu_user_id,
            target_user_data={
                "name": user_info.get("name"),
                "feishu_userid": feishu_user_id,
            },
            operation_details={
                "action": "create_user",
                "source": "qr_scan",
                "user_data": {
                    "name": user_info.get("name", "未知用户"),
                    "role": "business",
                    "feishu_user_id": feishu_user_id,
                    "feishu_union_id": user_info.get("union_id"),
                    "feishu_open_id": user_info.get("open_id"),
                    "email": user_info.get("email"),
                    "department": user_info.get("department_name"),
                },
            },
            requires_super_admin=True,
            remark="qr_scan",
        )
        conf_svc.send_account_op_card_to_super_admin(conf)

        name = user_info.get("name", "您")
        return HTMLResponse(content=_html_page(
            title="申请已提交",
            icon="📬",
            heading="申请已提交",
            body=f"<p>{name}，您的加入申请已发送给超级管理员审批。</p><p>审批通过后您将收到飞书通知，届时即可使用系统。</p>",
            auto_close_ms=4000,
        ))
    except HTTPException:
        raise
    except Exception as e:
        return HTMLResponse(content=_html_page(
            title="提交失败",
            icon="❌",
            heading="提交失败",
            body="<p>系统发生错误，请稍后重试或联系管理员。</p>",
        ))


# ════════════════════════════════════════════════════════════
# 确认页主入口
# ════════════════════════════════════════════════════════════

@router.get("/confirm-request")
def confirm_request_page(
    section: str = Query(..., description="申请类型，如 vercel/domain_register"),
    current_user=Depends(lambda: None),   # OAuth 由前端处理，后端只验 token
    db: Session = Depends(get_db),
):
    """
    返回确认页所需数据：
    - 该 section 是否已绑定 Bitable
    - 若已绑定，返回 Bitable 记录摘要（供前端展示）
    - 若未绑定，告知前端需要先绑定
    """
    # 实际调用时 current_user 由 get_current_active_user 注入，
    # 这里写成独立端点方便前端 OAuth 回调后携 JWT 访问
    raise HTTPException(status_code=501, detail="请通过前端页面访问")


class ConfirmPageData(BaseModel):
    section: str
    label: str
    needs_binding: bool
    records: List[Dict[str, Any]] = []


@router.get("/confirm-data", response_model=ConfirmPageData)
def get_confirm_data(
    section: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(__import__("app.api.dependencies", fromlist=["get_current_active_user"]).get_current_active_user),
):
    """
    前端确认页加载时调用（需 JWT）。
    返回：section 标签、是否已绑定、已绑定时的 Bitable 记录列表。
    """
    from app.models.feishu_bitable import FeishuBitableConfig

    all_sections = {**SECTIONS_WITH_BITABLE, **SECTIONS_NO_BITABLE}
    meta = all_sections.get(section)
    if not meta:
        raise HTTPException(status_code=400, detail=f"未知的 section: {section}")

    # 无 Bitable 的申请类型（域名注册）
    if section in SECTIONS_NO_BITABLE:
        return ConfirmPageData(section=section, label=meta["label"], needs_binding=False)

    # 查绑定记录
    cfg = db.query(FeishuBitableConfig).filter_by(
        section=section, user_id=current_user.id
    ).first()

    if not cfg:
        return ConfirmPageData(section=section, label=meta["label"], needs_binding=True)

    # 读取 Bitable 记录
    try:
        raw_rows = feishu_service.read_bitable_records(cfg.app_token, cfg.table_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"读取多维表格失败：{e}")

    records = []
    for row in raw_rows:
        fields = row.get("fields", {})
        hostname = str(fields.get("Hostname") or fields.get("hostname") or "").strip()
        rtype    = str(fields.get("Type")     or fields.get("type")     or "").strip()
        target   = str(fields.get("Target")   or fields.get("target")   or "").strip()
        if hostname and hostname not in ("—", "-") and rtype and target:
            records.append({"hostname": hostname, "type": rtype.upper(), "target": target})

    return ConfirmPageData(
        section=section,
        label=meta["label"],
        needs_binding=False,
        records=records,
    )


class BindBitableBody(BaseModel):
    section: str
    bitable_url: str   # 用户粘贴的飞书 Bitable URL


@router.post("/bind-bitable")
def bind_bitable(
    body: BindBitableBody,
    db: Session = Depends(get_db),
    current_user=Depends(__import__("app.api.dependencies", fromlist=["get_current_active_user"]).get_current_active_user),
):
    """
    用户首次使用时绑定 Bitable：解析 URL 提取 app_token + table_id，存库。
    """
    import re
    from app.models.feishu_bitable import FeishuBitableConfig

    if body.section not in SECTIONS_WITH_BITABLE:
        raise HTTPException(status_code=400, detail=f"section '{body.section}' 不需要绑定 Bitable")

    # 解析飞书 Bitable URL
    # 格式：https://xxx.feishu.cn/base/{app_token}?table={table_id}&...
    m = re.search(r"/base/([A-Za-z0-9]+)", body.bitable_url)
    if not m:
        raise HTTPException(status_code=400, detail="无法解析 Bitable URL，请确认复制的是多维表格新页面的完整地址")
    app_token = m.group(1)

    t = re.search(r"[?&]table=([A-Za-z0-9]+)", body.bitable_url)
    if not t:
        raise HTTPException(status_code=400, detail="URL 中未找到 table 参数，请确认复制的是包含表格 ID 的完整地址")
    table_id = t.group(1)

    # 验证可访问性
    try:
        feishu_service.read_bitable_records(app_token, table_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"无法访问该多维表格，请检查应用权限：{e}")

    # 保存或更新绑定
    cfg = db.query(FeishuBitableConfig).filter_by(
        section=body.section, user_id=current_user.id
    ).first()
    if cfg:
        cfg.app_token = app_token
        cfg.table_id  = table_id
    else:
        db.add(FeishuBitableConfig(
            section=body.section,
            user_id=current_user.id,
            app_token=app_token,
            table_id=table_id,
        ))
    db.commit()

    return {"success": True, "app_token": app_token, "table_id": table_id}


class SubmitRequestBody(BaseModel):
    section: str
    domain: str
    records: List[Dict[str, Any]] = []   # DNS 类申请传此字段；域名注册类忽略


@router.post("/submit-request")
def submit_request(
    body: SubmitRequestBody,
    db: Session = Depends(get_db),
    current_user=Depends(__import__("app.api.dependencies", fromlist=["get_current_active_user"]).get_current_active_user),
):
    """
    确认页用户点"确认提交"后调用。
    """
    from app.services.user_service import UserService
    from app.services.request_service import RequestService
    from app.schemas.request import RequestCreate

    if not getattr(current_user, "assigned_specialist_id", None):
        raise HTTPException(status_code=403, detail="您尚未分配归属专员，无法提交申请，请联系管理员配置")

    all_sections = {**SECTIONS_WITH_BITABLE, **SECTIONS_NO_BITABLE}
    meta = all_sections.get(body.section)
    if not meta:
        raise HTTPException(status_code=400, detail=f"未知的 section: {body.section}")

    req_type = meta["request_type"]
    user_svc = UserService(db)
    req_svc  = RequestService(db)

    if req_type == "domain_register":
        if not body.domain:
            raise HTTPException(status_code=400, detail="请填写要注册的域名")
        # 幂等：是否已有 pending 申请
        existing = req_svc.get_pending_domain_request(body.domain)
        if existing:
            raise HTTPException(status_code=409, detail=f"域名 {body.domain} 已有待审批申请（ID: {existing.id}）")
        request_data = {"domain": body.domain}
    else:
        if not body.records:
            raise HTTPException(status_code=400, detail="没有有效的解析记录，请先在多维表格中填写")
        request_data = {
            "dns_provider": body.section,
            "domain": body.domain,
            "records": body.records,
        }

    req = req_svc.create_request(
        data=RequestCreate(
            type=req_type,
            domain_name=body.domain,
            request_data=request_data,
            source="feishu_doc",
        ),
        requester_id=current_user.id,
        requester_name=current_user.name,
    )

    # 发审批卡片给归属专员
    specialist = user_svc.get_user(current_user.assigned_specialist_id)
    if specialist:
        receive_id = getattr(specialist, "feishu_open_id", None) or getattr(specialist, "feishu_user_id", None)
        receive_type = "open_id" if getattr(specialist, "feishu_open_id", None) else "user_id"
        if receive_id:
            if req_type == "dns_record":
                feishu_service.send_dns_approval_card(
                    receive_id=receive_id,
                    request_id=req.id,
                    requester_name=current_user.name,
                    domain=body.domain,
                    dns_provider=body.section,
                    records=body.records,
                    receive_id_type=receive_type,
                    application_time=req.created_at,
                )
            else:
                feishu_service.send_text_message(
                    receive_id=receive_id,
                    content=(
                        f"📋 域名注册申请\n"
                        f"申请人：{current_user.name}\n"
                        f"申请时间：{_format_card_time(req.created_at)}\n"
                        f"域名：{body.domain}\n"
                        f"请登录 Web 后台审批。"
                    ),
                    receive_id_type=receive_type,
                )

    return {"success": True, "request_id": req.id}


class TableRequestBody(BaseModel):
    """多维表格按钮触发的申请请求体（由飞书自动化注入）"""
    feishu_user_id: str          # 点击按钮的用户飞书 user_id / open_id
    app_token: str               # 多维表格所属 Bitable 的 app_token
    table_id: str                # 具体哪张表
    dns_provider: str            # 解析平台，写死在自动化配置里，如 "vercel"
    domain: str                  # 域名，写死在自动化配置里，如 "krea2.net"


@router.post("/table-request")
async def feishu_table_request(body: TableRequestBody, db: Session = Depends(get_db)):
    """
    多维表格"提交全部记录"按钮触发的入口。

    飞书自动化 HTTP 节点调用此接口，后端：
    1. 验证用户身份 & 归属专员
    2. 从 Bitable 读取所有 DNS 记录
    3. 创建 dns_record 申请
    4. 向归属专员发送审批卡片
    """
    from app.services.user_service import UserService
    from app.services.request_service import RequestService
    from app.schemas.request import RequestCreate

    user_svc = UserService(db)

    # 用 feishu_user_id 或 open_id 找用户
    user = user_svc.get_user_by_feishu_userid(body.feishu_user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="用户不存在或已禁用，请联系管理员")

    if not getattr(user, "assigned_specialist_id", None):
        raise HTTPException(status_code=403, detail="您尚未分配归属专员，无法提交申请，请联系管理员")

    # 读取 Bitable 所有记录
    raw_rows = feishu_service.read_bitable_records(body.app_token, body.table_id)

    # 过滤：去掉空行和专用提交行（Hostname 为空或仅含"—"）
    records = []
    for row in raw_rows:
        fields = row.get("fields", {})
        hostname = str(fields.get("Hostname") or fields.get("hostname") or "").strip()
        rtype    = str(fields.get("Type")     or fields.get("type")     or "").strip()
        target   = str(fields.get("Target")   or fields.get("target")   or "").strip()
        if hostname and hostname not in ("—", "-") and rtype and target:
            records.append({"hostname": hostname, "type": rtype.upper(), "target": target})

    if not records:
        raise HTTPException(status_code=400, detail="表格中没有有效的解析记录，请先填写后再提交")

    # 创建申请记录
    req_svc = RequestService(db)
    req = req_svc.create_request(
        data=RequestCreate(
            type="dns_record",
            domain_name=body.domain,
            request_data={
                "dns_provider": body.dns_provider,
                "domain": body.domain,
                "records": records,
            },
            source="feishu_table",
        ),
        requester_id=user.id,
        requester_name=user.name,
    )

    # 找归属专员并发审批卡片
    specialist = user_svc.get_user(user.assigned_specialist_id)
    if specialist:
        receive_id = getattr(specialist, "feishu_open_id", None) or getattr(specialist, "feishu_user_id", None)
        receive_type = "open_id" if getattr(specialist, "feishu_open_id", None) else "user_id"
        if receive_id:
            feishu_service.send_dns_approval_card(
                receive_id=receive_id,
                request_id=req.id,
                requester_name=user.name,
                domain=body.domain,
                    dns_provider=body.dns_provider,
                    records=records,
                    receive_id_type=receive_type,
                    application_time=req.created_at,
                )

    return {"success": True, "request_id": req.id, "records_count": len(records)}


async def _handle_card_action(body: dict) -> dict:
    """
    处理飞书卡片按钮回调
    超管点击"授权执行"或"拒绝"按钮时触发
    """
    try:
        action = body.get("action", {})
        value = action.get("value", {}) or body.get("event", {}).get("action", {}).get("value", {})
        operator = body.get("operator", {}) or body.get("event", {}).get("operator", {})

        card_action = value.get("action", "")

        # DNS 解析申请审批（专员操作）
        if card_action in ("approve_dns_request", "reject_dns_request"):
            return await _handle_dns_card_action(card_action, value, operator)

        # 新版文档按钮申请审批（域名购买 / DNS）
        if card_action in ("approve_doc_request", "reject_doc_request"):
            form_values = _extract_card_form_values(body)
            return await _handle_doc_request_card_action(card_action, value, form_values, operator)

        confirmation_id = value.get("confirmation_id")
        if not confirmation_id or card_action not in ("approve_account_op", "reject_account_op"):
            return {"success": True, "message": "非账号授权卡片，忽略"}

        confirmation_id = int(confirmation_id)
        operator_open_id = operator.get("open_id", "") or operator.get("user_id", "")
        form_values = _extract_card_form_values(body)

        from app.core.database import SessionLocal
        from app.services.user_confirmation_service import UserOperationConfirmationService

        db = SessionLocal()
        try:
            conf_svc = UserOperationConfirmationService(db)
            approver = conf_svc.get_user_by_feishu_id(operator_open_id)
            if not approver or approver.role != "super_admin":
                return {"toast": {"type": "error", "content": "只有超级管理员可以审批此操作"}}

            if card_action == "approve_account_op":
                result = conf_svc.approve_confirmation(
                    confirmation_id=confirmation_id,
                    approver_user_id=approver.id,
                    approver_name=approver.name,
                    approver_feishu_userid=operator_open_id,
                )
                return {"toast": {"type": "success" if result else "error",
                                  "content": "已授权执行" if result else "授权失败（已处理或不存在）"}}
            else:
                result = conf_svc.reject_confirmation(
                    confirmation_id=confirmation_id,
                    approver_user_id=approver.id,
                    approver_name=approver.name,
                    approver_feishu_userid=operator_open_id,
                    reject_reason=_as_text(form_values.get("reject_reason")) or "未填写",
                )
                return {"toast": {"type": "info" if result else "error",
                                  "content": "已拒绝操作申请" if result else "拒绝失败（已处理或不存在）"}}
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("处理卡片回调失败")
        return {"toast": {"type": "error", "content": f"处理失败: {str(e)}"}}


def _extract_card_form_values(body: dict) -> Dict[str, Any]:
    """兼容不同飞书卡片版本的表单回传结构。"""
    action = body.get("action", {}) or body.get("event", {}).get("action", {})
    candidates = [
        action.get("form_value"),
        action.get("form_values"),
        action.get("input_values"),
        action.get("value", {}).get("form_value") if isinstance(action.get("value"), dict) else None,
    ]
    result: Dict[str, Any] = {}
    for item in candidates:
        if isinstance(item, dict):
            result.update(item)
    return result


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, list) and value:
        value = value[0]
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("value") or value.get("text") or ""
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip()


async def _handle_doc_request_card_action(card_action: str, value: dict, form_values: Dict[str, Any], operator: dict) -> dict:
    """处理新版文档按钮申请审批卡片。"""
    import logging
    logger = logging.getLogger(__name__)

    request_id = value.get("request_id")
    if not request_id:
        return {"toast": {"type": "error", "content": "卡片数据异常，缺少 request_id"}}

    operator_open_id = operator.get("open_id", "") or operator.get("user_id", "")
    db = SessionLocal()
    try:
        from app.services.user_service import UserService
        from app.services.request_service import RequestService
        from app.services.execution_service import ExecutionService
        from app.models.domain import RegAccount, DnsAccount

        user_svc = UserService(db)
        req_svc = RequestService(db)

        reviewer = user_svc.get_user_by_any_feishu_id(operator_open_id)
        if not reviewer or reviewer.role not in ("domain_spec", "super_admin"):
            return {"toast": {"type": "error", "content": "只有域名专员可以审批此申请"}}

        req = req_svc.get_request(request_id)
        if not req or req.status != "pending":
            return {"toast": {"type": "error", "content": "申请不存在或已处理"}}

        applicant = user_svc.get_user(req.requester_id)
        if reviewer.role != "super_admin":
            if not applicant or applicant.assigned_specialist_id != reviewer.id:
                return {"toast": {"type": "error", "content": "该申请不属于您负责的业务同事"}}

        if card_action == "reject_doc_request":
            reason = _as_text(form_values.get("reject_reason")) or "未填写"
            req_svc.reject_request(request_id, reviewer.id, reviewer.name, reason=reason)
            _notify_request_rejected(req, applicant, reviewer, reason)
            return {"toast": {"type": "info", "content": "已拒绝该申请"}}

        if req.type == "domain_register":
            account_id = _as_int(form_values.get("selected_reg_account_id"))
            if not account_id:
                return {"toast": {"type": "error", "content": "请选择注册厂商账号"}}
            account = db.query(RegAccount).filter(RegAccount.id == account_id, RegAccount.is_active == True).first()  # noqa: E712
            if not account or (reviewer.role != "super_admin" and account.owner_id != reviewer.id):
                return {"toast": {"type": "error", "content": "无权使用该注册账号"}}
            selected_quotes = _quote_reg_account_prices(db, req.domain_name, [account])
            selected_quote = selected_quotes.get(str(account.id)) or {}
            if selected_quote.get("check_successful") and selected_quote.get("available") is False:
                return {"toast": {"type": "error", "content": f"所选服务商显示该域名不可注册：{selected_quote.get('message') or '不可注册'}"}}
            req.selected_reg_account_id = account.id
            req.selected_registrar_code = account.registrar_code
            request_data = dict(req.request_data or {})
            request_data["register_years"] = _as_text(form_values.get("register_years")) or "1"
            request_data["selected_price_quote"] = selected_quote
            req.request_data = request_data
        else:
            account_id = _as_int(form_values.get("selected_dns_account_id"))
            if not account_id:
                return {"toast": {"type": "error", "content": "请选择 DNS 账号"}}
            account = db.query(DnsAccount).filter(DnsAccount.id == account_id, DnsAccount.is_active == True).first()  # noqa: E712
            if not account or (reviewer.role != "super_admin" and account.owner_id != reviewer.id):
                return {"toast": {"type": "error", "content": "无权使用该 DNS 账号"}}
            req.selected_dns_account_id = account.id
            req.selected_dns_provider_code = account.provider_code
            comment = _as_text(form_values.get("approval_comment"))
            if comment:
                request_data = dict(req.request_data or {})
                request_data["approval_comment"] = comment
                req.request_data = request_data
        db.commit()
        db.refresh(req)

        req_svc.approve_request(request_id, reviewer.id, reviewer.name)
        try:
            ExecutionService(db).execute_and_notify(req)
        except Exception as e:
            logger.exception("文档按钮申请执行失败: %s", e)
        return {"toast": {"type": "success", "content": "已批准，正在执行"}}
    except Exception as e:
        logger.exception("处理文档按钮审批卡片失败")
        return {"toast": {"type": "error", "content": f"处理失败: {str(e)}"}}
    finally:
        db.close()


def _notify_request_rejected(req, applicant, reviewer, reason: str) -> None:
    label = "域名购买" if req.type == "domain_register" else "DNS 解析"
    targets = []
    if applicant:
        targets.append((
            applicant,
            (
                f"❌ {label}申请已拒绝\n"
                f"域名：{req.domain_name}\n"
                f"审核人：{getattr(reviewer, 'name', '未知')}\n"
                f"拒绝理由：{reason or '未填写'}"
            ),
        ))
    if reviewer and (not applicant or reviewer.id != applicant.id):
        targets.append((
            reviewer,
            (
                f"❌ 您已拒绝{label}申请\n"
                f"域名：{req.domain_name}\n"
                f"申请人：{getattr(applicant, 'name', req.requester_name)}\n"
                f"拒绝理由：{reason or '未填写'}"
            ),
        ))
    for user, content in targets:
        receive_id = getattr(user, "feishu_open_id", None) or getattr(user, "feishu_user_id", None)
        if not receive_id:
            continue
        receive_type = "open_id" if getattr(user, "feishu_open_id", None) else "user_id"
        try:
            feishu_service.send_text_message(receive_id, content, receive_type)
        except Exception:
            pass


async def _handle_dns_card_action(card_action: str, value: dict, operator: dict) -> dict:
    """专员点击 DNS 审批卡片后的处理（批准/拒绝）。"""
    import logging
    logger = logging.getLogger(__name__)

    request_id = value.get("request_id")
    if not request_id:
        return {"toast": {"type": "error", "content": "卡片数据异常，缺少 request_id"}}

    operator_open_id = operator.get("open_id", "") or operator.get("user_id", "")

    db = SessionLocal()
    try:
        from app.services.user_service import UserService
        from app.services.request_service import RequestService
        from app.services.execution_service import ExecutionService

        user_svc = UserService(db)
        req_svc  = RequestService(db)

        # 找操作人（open_id / user_id 均可）
        specialist = user_svc.get_user_by_any_feishu_id(operator_open_id)
        if not specialist or specialist.role not in ("domain_spec", "super_admin"):
            return {"toast": {"type": "error", "content": "只有域名专员可以审批此申请"}}

        request = req_svc.get_request(request_id)
        if not request:
            return {"toast": {"type": "error", "content": "申请不存在或已处理"}}

        # 校验归属：申请人的归属专员必须是当前操作人（超管除外）
        if specialist.role != "super_admin":
            requester = user_svc.get_user(request.requester_id)
            if not requester or requester.assigned_specialist_id != specialist.id:
                return {"toast": {"type": "error", "content": "该申请不属于您负责的业务同事"}}

        if card_action == "approve_dns_request":
            req_svc.approve_request(request_id, specialist.id, specialist.name)
            # 自动执行
            try:
                ExecutionService(db).execute_and_notify(request)
            except Exception as e:
                logger.exception("DNS 申请执行失败: %s", e)
            return {"toast": {"type": "success", "content": "已批准，正在执行 DNS 配置"}}
        else:
            req_svc.reject_request(request_id, specialist.id, specialist.name, reason="专员拒绝")
            requester = user_svc.get_user(request.requester_id)
            _notify_request_rejected(request, requester, specialist, "专员拒绝")
            return {"toast": {"type": "info", "content": "已拒绝该申请"}}
    except Exception as e:
        logger.exception("处理 DNS 审批卡片失败")
        return {"toast": {"type": "error", "content": f"处理失败: {str(e)}"}}
    finally:
        db.close()
