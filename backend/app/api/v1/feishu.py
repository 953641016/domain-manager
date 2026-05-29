"""
飞书相关API路由
提供OAuth授权、用户信息获取等接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.config import Config
from app.services.feishu_service import feishu_service


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
