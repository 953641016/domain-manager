"""
飞书相关API路由
提供OAuth授权、用户信息获取、webhook事件处理等接口
"""
from fastapi import APIRouter, HTTPException, Query, Request, Depends
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
            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>用户已存在</title></head>
<body style="text-align:center;padding:50px;font-family:sans-serif">
<h2>用户 "{existing_user.name}" 已在系统中</h2>
<p>无需重复添加。</p>
<script>setTimeout(function(){{ window.close(); }}, 2000);</script>
</body></html>"""
            return HTMLResponse(content=html)

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
            html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>添加成功</title></head>
<body style="text-align:center;padding:50px;font-family:sans-serif">
<h2>已添加（系统初始化模式）</h2>
<p>超级管理员尚未配置，已直接创建账号。</p>
<script>setTimeout(function(){ window.close(); }, 3000);</script>
</body></html>"""
            return HTMLResponse(content=html)

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
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>申请已提交</title></head>
<body style="text-align:center;padding:50px;font-family:sans-serif">
<h2>申请已提交</h2>
<p>{name}，您的加入申请已发送给超级管理员审批。</p>
<p>审批通过后您将收到飞书通知，届时即可使用系统。</p>
<script>setTimeout(function(){{ window.close(); }}, 4000);</script>
</body></html>"""
        return HTMLResponse(content=html)
    except HTTPException:
        raise
    except Exception as e:
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>添加失败</title></head>
<body style="text-align:center;padding:50px;font-family:sans-serif">
<h2>用户添加失败</h2>
<p>{str(e)}</p>
</body></html>"""
        return HTMLResponse(content=html)


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
                )
            else:
                feishu_service.send_text_message(
                    receive_id=receive_id,
                    content=f"📋 域名注册申请\n申请人：{current_user.name}\n域名：{body.domain}\n请登录 Web 后台审批。",
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

        confirmation_id = value.get("confirmation_id")
        if not confirmation_id or card_action not in ("approve_account_op", "reject_account_op"):
            return {"success": True, "message": "非账号授权卡片，忽略"}

        confirmation_id = int(confirmation_id)
        operator_open_id = operator.get("open_id", "")

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
                    reject_reason="超级管理员拒绝",
                )
                return {"toast": {"type": "info" if result else "error",
                                  "content": "已拒绝操作申请" if result else "拒绝失败（已处理或不存在）"}}
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("处理卡片回调失败")
        return {"toast": {"type": "error", "content": f"处理失败: {str(e)}"}}


async def _handle_dns_card_action(card_action: str, value: dict, operator: dict) -> dict:
    """专员点击 DNS 审批卡片后的处理（批准/拒绝）。"""
    import logging
    logger = logging.getLogger(__name__)

    request_id = value.get("request_id")
    if not request_id:
        return {"toast": {"type": "error", "content": "卡片数据异常，缺少 request_id"}}

    operator_open_id = operator.get("open_id", "")

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
            return {"toast": {"type": "info", "content": "已拒绝该申请"}}
    except Exception as e:
        logger.exception("处理 DNS 审批卡片失败")
        return {"toast": {"type": "error", "content": f"处理失败: {str(e)}"}}
    finally:
        db.close()
