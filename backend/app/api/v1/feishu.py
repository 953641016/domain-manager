"""
飞书相关API路由
提供OAuth授权、用户信息获取、webhook事件处理等接口
"""
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.config import Config
from app.services.feishu_service import feishu_service
from app.bots.feishu import feishu_bot
from app.core.database import get_db


router = APIRouter(
    prefix="/feishu",
    tags=["飞书集成"],
)


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
    处理URL验证、消息接收等事件
    """
    try:
        # 解析请求体
        request_body = await request.json()
        
        # 验证签名
        if not feishu_service.verify_webhook_signature(request_body):
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
            return await _handle_card_action(request_body)

        # 默认响应
        return {"success": True, "message": "事件已接收"}
    
    except HTTPException:
        raise
    except Exception as e:
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
    扫码添加用户回调
    用户扫码授权后，自动获取信息并创建用户
    """
    try:
        from app.services.user_service import UserService
        user_info = feishu_service.get_user_info_by_code(code)
        if not user_info:
            raise HTTPException(status_code=400, detail="获取用户信息失败")

        user_service = UserService(db)
        feishu_user_id = user_info.get("user_id", "")
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
        new_user, _ = user_service.create_user(user_create)

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>添加成功</title></head>
<body style="text-align:center;padding:50px;font-family:sans-serif">
<h2>用户添加成功</h2>
<p>姓名：{new_user.name}</p>
<p>部门：{new_user.department or '未知'}</p>
<p>角色：业务人员</p>
<script>setTimeout(function(){{ window.close(); }}, 2000);</script>
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
