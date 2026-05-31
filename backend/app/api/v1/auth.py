"""
认证API路由
处理飞书OAuth登录、用户信息获取、登出等
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.services.auth_service import AuthService
from app.models.user import User
from app.config import Config

router = APIRouter(
    prefix="/auth",
    tags=["认证"],
)


class OAuthUrlResponse(BaseModel):
    """OAuth URL响应"""
    success: bool
    oauth_url: str


class LoginRequest(BaseModel):
    """登录请求"""
    code: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    access_token: str
    token_type: str
    user: dict


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    id: int
    name: str
    en_name: Optional[str] = None
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    feishu_user_id: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None


class LogoutResponse(BaseModel):
    """登出响应"""
    success: bool
    message: str


@router.get("/oauth-url", response_model=OAuthUrlResponse)
async def get_oauth_url(
    redirect_uri: str = Query(..., description="回调地址"),
):
    """
    获取飞书OAuth授权URL

    前端使用此URL生成二维码，用户扫码后会跳转到redirect_uri
    """
    try:
        auth_service = AuthService(None)
        oauth_url = auth_service.get_oauth_url(redirect_uri)
        return OAuthUrlResponse(success=True, oauth_url=oauth_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成OAuth URL失败: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    飞书OAuth登录

    用户扫码后，前端获取code，调用此接口完成登录
    """
    try:
        auth_service = AuthService(db)
        result = auth_service.login_with_feishu_code(request.code)

        return LoginResponse(
            success=True,
            access_token=result["access_token"],
            token_type=result["token_type"],
            user=result["user"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"登录失败: {str(e)}"
        )


@router.get("/callback", response_class=HTMLResponse)
async def auth_callback(
    code: str = Query(..., description="飞书授权码"),
    db: Session = Depends(get_db),
):
    """
    飞书OAuth回调接口

    飞书用户授权后会重定向到此接口，携带code参数
    """
    try:
        auth_service = AuthService(db)
        result = auth_service.login_with_feishu_code(code)
        
        import json
        user_json = json.dumps(result['user'], ensure_ascii=False)
        user_json_escaped = user_json.replace("'", "\\'")
        access_token = result["access_token"]
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>登录成功</title>
    <script>
        localStorage.setItem('access_token', '{access_token}');
        localStorage.setItem('user', '{user_json_escaped}');
        var redirect = localStorage.getItem('post_login_redirect') || '/dm/dashboard';
        localStorage.removeItem('post_login_redirect');
        window.location.href = redirect.startsWith('/') ? redirect : '/dm/dashboard';
    </script>
</head>
<body>
    <p>登录成功，正在跳转...</p>
</body>
</html>"""
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"登录失败: {str(e)}"
        )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前登录用户信息

    需要在请求头中携带Authorization: Bearer {token}
    """
    return UserInfoResponse(
        id=current_user.id,
        name=current_user.name,
        en_name=current_user.en_name,
        role=current_user.role,
        email=current_user.email,
        phone=current_user.phone,
        avatar_url=current_user.avatar_url,
        feishu_user_id=current_user.feishu_user_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
    )


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_active_user),
):
    """
    刷新访问令牌

    用于在令牌过期前主动刷新
    """
    from app.core.security import create_access_token

    new_token = create_access_token(
        data={"sub": str(current_user.id), "role": current_user.role}
    )

    return {
        "success": True,
        "access_token": new_token,
        "token_type": "bearer"
    }


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_active_user),
):
    """
    登出

    客户端应删除本地存储的token
    """
    return LogoutResponse(
        success=True,
        message="已成功登出"
    )
