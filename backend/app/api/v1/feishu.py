"""
飞书相关API路由
提供OAuth授权、用户信息获取、webhook事件处理等接口
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.config import Config
from app.services.feishu_service import feishu_service
from app.bots.feishu import feishu_bot


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
            # 处理消息接收事件
            event = request_body.get("event", {})
            
            # 调用机器人处理消息
            await feishu_bot.handle_message(event)
            
            return {
                "success": True,
                "message": "消息已接收"
            }
        
        # 默认响应
        return {
            "success": True,
            "message": "事件已接收"
        }
    
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
