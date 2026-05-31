"""
飞书API服务模块
提供飞书OAuth、用户信息获取、机器人消息等功能
"""
import requests
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.config import Config


class FeishuService:
    """飞书服务类"""
    
    def __init__(self):
        self.app_id = Config.FEISHU_APP_ID
        self.app_secret = Config.FEISHU_APP_SECRET
        self.verification_token = Config.FEISHU_VERIFICATION_TOKEN
        self.encrypt_key = Config.FEISHU_ENCRYPT_KEY
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
    
    def search_users_by_name(self, keyword: str) -> List[Dict[str, Any]]:
        """
        按姓名搜索飞书用户
        使用通讯录搜索API
        """
        url = f"{self.base_url}/open-apis/search/v1/user"
        headers = {
            "Authorization": f"Bearer {self.get_app_access_token()}",
            "Content-Type": "application/json"
        }
        params = {
            "query": keyword,
            "page_size": 10,
            "user_id_type": "user_id"
        }
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if data.get("code") != 0:
            return []
        
        users = data.get("data", {}).get("users", [])
        result = []
        for u in users:
            result.append({
                "user_id": u.get("open_id", ""),
                "name": u.get("name", ""),
                "en_name": u.get("en_name", ""),
                "email": u.get("email", ""),
                "mobile": u.get("mobile", ""),
                "avatar_url": u.get("avatar", {}).get("avatar_72", ""),
                "department_name": u.get("department_name", ""),
            })
        return result
    
    def send_text_message(
        self, 
        receive_id: str, 
        content: str, 
        receive_id_type: str = "open_id"
    ) -> Dict[str, Any]:
        """
        发送文本消息
        
        Args:
            receive_id: 接收者ID
            content: 消息内容
            receive_id_type: 接收者ID类型 (open_id/user_id/union_id/email/chat_id)
        
        Returns:
            飞书API响应
        """
        url = f"{self.base_url}/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.get_app_access_token()}",
            "Content-Type": "application/json"
        }
        params = {
            "receive_id_type": receive_id_type
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }
        
        response = requests.post(url, headers=headers, params=params, json=payload)
        return response.json()
    
    def send_card_message(
        self,
        receive_id: str,
        card_content: Dict[str, Any],
        receive_id_type: str = "open_id"
    ) -> Dict[str, Any]:
        """
        发送交互式卡片消息
        
        Args:
            receive_id: 接收者ID
            card_content: 卡片内容
            receive_id_type: 接收者ID类型
        
        Returns:
            飞书API响应
        """
        url = f"{self.base_url}/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.get_app_access_token()}",
            "Content-Type": "application/json"
        }
        params = {
            "receive_id_type": receive_id_type
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }
        
        response = requests.post(url, headers=headers, params=params, json=payload)
        return response.json()
    
    def send_domain_alert_card(
        self,
        receive_id: str,
        domain_name: str,
        expire_days: int,
        expiration_date: str = "",
        registrar: str = "",
        receive_id_type: str = "open_id",
    ) -> Dict[str, Any]:
        """发送域名到期提醒卡片（按紧急程度分级）"""
        if expire_days <= 7:
            title = "🚨 域名即将到期"
            color = "red"
            urgency = f"**仅剩 {expire_days} 天**，请立即联系注册商续费！"
        elif expire_days <= 30:
            title = "⚠️ 域名到期提醒"
            color = "orange"
            urgency = f"剩余 **{expire_days}** 天，请尽快安排续费。"
        else:
            title = "📅 域名到期提醒"
            color = "yellow"
            urgency = f"剩余 {expire_days} 天，请适时安排续费。"

        info_lines = [f"**域名**：{domain_name}"]
        if expiration_date:
            info_lines.append(f"**到期日期**：{expiration_date}")
        if registrar:
            info_lines.append(f"**注册商**：{registrar}")
        info_lines.append(f"\n{urgency}")

        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "\n".join(info_lines)},
                },
            ],
        }
        return self.send_card_message(receive_id, card_content, receive_id_type)

    # ──────────────────────────────────────────────
    # 多维表格（Bitable）
    # ──────────────────────────────────────────────

    def read_bitable_records(self, app_token: str, table_id: str) -> List[Dict[str, Any]]:
        """读取多维表格所有记录，返回非空数据行列表。"""
        url = f"{self.base_url}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        headers = {"Authorization": f"Bearer {self.get_app_access_token()}"}
        rows = []
        page_token = None
        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=headers, params=params).json()
            items = resp.get("data", {}).get("items") or []
            rows.extend(items)
            page_token = resp.get("data", {}).get("page_token")
            if not page_token:
                break
        return rows

    def send_dns_approval_card(
        self,
        receive_id: str,
        request_id: str,
        requester_name: str,
        domain: str,
        dns_provider: str,
        records: List[Dict[str, Any]],
        receive_id_type: str = "open_id",
    ) -> Dict[str, Any]:
        """向专员发送 DNS 解析批量审批卡片。"""
        record_lines = "\n".join(
            f"• **{r.get('hostname', r.get('Hostname', ''))}**  "
            f"{r.get('type', r.get('Type', ''))}  →  "
            f"{r.get('target', r.get('Target', ''))}"
            for r in records
        )
        provider_label = {
            "cloudflare": "Cloudflare",
            "vercel": "Vercel",
            "clerk": "Clerk",
        }.get(dns_provider.lower(), dns_provider)

        card = {
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
                            f"**申请人**：{requester_name}\n"
                            f"**域名**：{domain}\n"
                            f"**解析平台**：{provider_label}\n"
                            f"**记录数**：{len(records)} 条"
                        ),
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": record_lines},
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 批准执行"},
                            "type": "primary",
                            "value": {"action": "approve_dns_request", "request_id": request_id},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 拒绝申请"},
                            "type": "danger",
                            "value": {"action": "reject_dns_request", "request_id": request_id},
                        },
                    ],
                },
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": f"申请编号：#{str(request_id)[:8]}"}],
                },
            ],
        }
        return self.send_card_message(receive_id, card, receive_id_type)

    def verify_webhook_signature(self, request_body: Dict[str, Any]) -> bool:
        """
        验证webhook请求签名（旧接口，兼容保留）
        """
        if not self.verification_token:
            return True
        token = request_body.get("token") or request_body.get("header", {}).get("token")
        return token == self.verification_token

    def verify_webhook_signature_token(self, token: Optional[str]) -> bool:
        """
        验证 token 字符串（webhook / card 回调通用）。
        未配置 verification_token 时直接放行（开发/测试场景）。
        """
        if not self.verification_token:
            return True
        return token == self.verification_token
    
    def handle_url_verification(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理URL验证请求
        
        Args:
            request_body: 请求体
        
        Returns:
            验证响应
        """
        return {
            "challenge": request_body.get("challenge")
        }


# 单例实例
feishu_service = FeishuService()
