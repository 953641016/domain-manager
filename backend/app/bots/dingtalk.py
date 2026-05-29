import json
import time
import hashlib
import hmac
import base64
import requests
from typing import Dict, Any, Optional

from config import Config


class DingTalkBot:
    def __init__(self):
        self.app_key = Config.DINGTALK_APP_KEY
        self.app_secret = Config.DINGTALK_APP_SECRET
        self.access_token = None
        self.token_expires_at = 0

    def get_access_token(self) -> str:
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        url = "https://oapi.dingtalk.com/gettoken"
        params = {"appkey": self.app_key, "appsecret": self.app_secret}
        response = requests.get(url, params=params)
        result = response.json()

        if result.get("errcode") == 0:
            self.access_token = result["access_token"]
            self.token_expires_at = time.time() + result["expires_in"] - 300
            return self.access_token
        else:
            raise Exception(f"获取 access_token 失败: {result}")

    def send_text_message(self, conversation_id: str, text: str, at_user_ids: Optional[list] = None):
        url = f"https://oapi.dingtalk.com/topapi/im/chat/send?access_token={self.get_access_token()}"
        msg = {
            "msgtype": "text",
            "text": {"content": text}
        }
        if at_user_ids:
            msg["at"] = {"atUserIds": at_user_ids}

        data = {
            "chatid": conversation_id,
            "msg": json.dumps(msg)
        }
        response = requests.post(url, json=data)
        return response.json()

    def send_card_message(self, conversation_id: str, title: str, content: str, buttons: Optional[list] = None):
        url = f"https://oapi.dingtalk.com/topapi/im/chat/send?access_token={self.get_access_token()}"

        markdown_text = f"### {title}\n\n{content}"

        msg = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown_text
            }
        }

        data = {
            "chatid": conversation_id,
            "msg": json.dumps(msg)
        }
        response = requests.post(url, json=data)
        return response.json()

    def send_private_message(self, user_id: str, text: str):
        url = f"https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2?access_token={self.get_access_token()}"

        msg = {
            "msgtype": "text",
            "text": {"content": text}
        }

        data = {
            "userid_list": user_id,
            "agent_id": self.app_key,
            "msg": json.dumps(msg)
        }
        response = requests.post(url, json=data)
        return response.json()

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        url = f"https://oapi.dingtalk.com/topapi/v2/user/get?access_token={self.get_access_token()}"
        data = {"userid": user_id}
        response = requests.post(url, json=data)
        return response.json()

    def notify_admins(self, text: str):
        for admin_id in Config.ADMIN_USER_IDS:
            try:
                self.send_private_message(admin_id, text)
            except Exception as e:
                print(f"通知管理员 {admin_id} 失败: {e}")


class ConversationContext:
    def __init__(self):
        self.contexts = {}

    def set(self, user_id: str, key: str, value: Any):
        if user_id not in self.contexts:
            self.contexts[user_id] = {}
        self.contexts[user_id][key] = value

    def get(self, user_id: str, key: str, default: Any = None):
        return self.contexts.get(user_id, {}).get(key, default)

    def clear(self, user_id: str):
        if user_id in self.contexts:
            del self.contexts[user_id]
