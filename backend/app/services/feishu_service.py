"""
飞书API服务模块
提供飞书OAuth、用户信息获取等功能
"""
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.config import Config


class FeishuService:
    """飞书服务类"""
    
    def __init__(self):
        self.app_id = Config.FEISHU_APP_ID
        self.app_secret = Config.FEISHU_APP_SECRET
        self.base_url = "https://open.feishu.cn"
        
        # 缓存token
        self._app_access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def get_app_access_token(self) -> str:
        """
        获取应用访问令牌
        使用缓存机制避免频繁请求
        """
        # 检查缓存是否有效
        if (self._app_access_token and 
            self._token_expires_at and 
            datetime.now() < self._token_expires_at):
            return self._app_access_token
        
        # 请求新token
        url = f"{self.base_url}/open-apis/auth/v3/app_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取飞书访问令牌失败: {data}")
        
        self._app_access_token = data["app_access_token"]
        self._token_expires_at = datetime.now() + timedelta(seconds=data["expire"] - 300)
        
        return self._app_access_token
    
    def get_oauth_url(self, redirect_uri: str, state: str = "") -> str:
        """
        生成飞书OAuth授权URL
        用户扫码后会跳转到redirect_uri并附带code
        """
        base_url = "https://open.feishu.cn/open-apis/authen/v1/index"
        params = {
            "app_id": self.app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state
        }
        
        import urllib.parse
        query_string = urllib.parse.urlencode(params)
        return f"{base_url}?{query_string}"
    
    def get_user_info_by_code(self, code: str) -> Dict[str, Any]:
        """
        通过OAuth code获取用户信息
        """
        # 1. 使用code获取用户访问令牌
        token_url = f"{self.base_url}/open-apis/authen/v1/oidc/access_token"
        headers = {
            "Authorization": f"Bearer {self.get_app_access_token()}",
            "Content-Type": "application/json"
        }
        payload = {
            "grant_type": "authorization_code",
            "code": code
        }
        
        response = requests.post(token_url, headers=headers, json=payload)
        token_data = response.json()
        
        if token_data.get("code") != 0:
            raise Exception(f"获取用户访问令牌失败: {token_data}")
        
        user_access_token = token_data["data"]["access_token"]
        
        # 2. 使用用户访问令牌获取用户信息
        user_url = f"{self.base_url}/open-apis/authen/v1/user_info"
        user_headers = {
            "Authorization": f"Bearer {user_access_token}"
        }
        
        user_response = requests.get(user_url, headers=user_headers)
        user_data = user_response.json()
        
        if user_data.get("code") != 0:
            raise Exception(f"获取用户信息失败: {user_data}")
        
        return user_data["data"]
    
    def get_user_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        通过飞书用户ID获取用户详情
        使用通讯录API
        """
        url = f"{self.base_url}/open-apis/contact/v3/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {self.get_app_access_token()}"
        }
        params = {
            "user_id_type": "user_id"
        }
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if data.get("code") != 0:
            return None
        
        return data.get("data", {}).get("user")
    
    def search_users(self, query: str) -> list:
        """
        搜索飞书用户
        用于快速查找用户
        """
        url = f"{self.base_url}/open-apis/contact/v3/users/batch_get_id"
        headers = {
            "Authorization": f"Bearer {self.get_app_access_token()}",
            "Content-Type": "application/json"
        }
        payload = {
            "emails": [query],
            "mobiles": [query]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get("code") != 0:
            return []
        
        return data.get("data", {}).get("user_list", [])


# 单例实例
feishu_service = FeishuService()
