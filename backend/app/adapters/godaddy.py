"""
GoDaddy注册商适配器
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import requests
from app.adapters.base import BaseRegistrarAdapter


class GoDaddyRegistrarAdapter(BaseRegistrarAdapter):
    """GoDaddy注册商适配器"""

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.godaddy.com/v1"
        self.timeout = 4

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _format_api_error(self, data: Any, fallback: str) -> str:
        if isinstance(data, dict):
            code = data.get("code")
            message = data.get("message") or data.get("detail")
            if code and message:
                return f"{code}: {message}"
            if message:
                return str(message)
            if code:
                return str(code)
        return fallback

    def check_domain_availability(self, domain: str) -> Dict[str, Any]:
        """检查域名是否可注册"""
        url = f"{self.base_url}/domains/available"

        params = {"domain": domain}

        try:
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=self.timeout)
            data = response.json()

            if response.status_code == 200 and "available" in data:
                price = data.get("price")
                return {
                    "available": data.get("available", False),
                    "domain": domain,
                    "price": price / 1000000 if price is not None else None,
                    "currency": data.get("currency") or "USD",
                    "message": data.get("message", ""),
                    "period": data.get("period"),
                    "check_successful": True
                }
            else:
                return {
                    "available": None,
                    "domain": domain,
                    "message": self._format_api_error(data, "检查失败"),
                    "check_successful": False
                }
        except Exception as e:
            return {
                "available": None,
                "domain": domain,
                "message": f"检查出错: {str(e)}",
                "check_successful": False
            }

    def register_domain(
        self,
        domain: str,
        registrant_info: Dict[str, Any],
        nameservers: Optional[List[str]] = None,
        years: int = 1,
    ) -> Dict[str, Any]:
        """注册域名"""
        url = f"{self.base_url}/domains/purchase"
        registrant_info = registrant_info or {}
        agreed_by = (
            registrant_info.get("agreedBy")
            or registrant_info.get("agreed_by")
            or registrant_info.get("client_ip")
            or "127.0.0.1"
        )

        payload = {
            "domain": domain,
            "consent": {
                "agreedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "agreedBy": agreed_by,
                "agreementKeys": registrant_info.get("agreementKeys") or registrant_info.get("agreement_keys") or ["DNRA"]
            },
            "period": max(1, min(int(years or 1), 10)),
            "privacy": False,
            "renewAuto": False
        }

        contact_info = {k: v for k, v in registrant_info.items() if k not in {"agreedBy", "agreed_by", "client_ip", "agreementKeys", "agreement_keys"}}
        if contact_info:
            payload.update({
                "contactAdmin": contact_info,
                "contactBilling": contact_info,
                "contactRegistrant": contact_info,
                "contactTech": contact_info,
            })

        if nameservers:
            payload["nameServers"] = nameservers

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            data = response.json()

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "domain": domain,
                    "order_id": data.get("orderId"),
                    "registration_date": None,  # GoDaddy不返回此信息
                    "expiration_date": None,
                    "message": "注册成功"
                }
            else:
                return {
                    "success": False,
                    "domain": domain,
                    "message": f"注册失败: {self._format_api_error(data, '未知错误')}"
                }
        except Exception as e:
            return {
                "success": False,
                "domain": domain,
                "message": f"注册出错: {str(e)}"
            }

    def renew_domain(self, domain: str, years: int = 1) -> Dict[str, Any]:
        """续费域名"""
        url = f"{self.base_url}/domains/{domain}/renew"

        payload = {
            "period": years
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            data = response.json()

            if response.status_code in [200, 204]:
                return {
                    "success": True,
                    "domain": domain,
                    "expiration_date": None,
                    "message": "续费成功"
                }
            else:
                return {
                    "success": False,
                    "domain": domain,
                    "message": f"续费失败: {data.get('message', '未知错误')}"
                }
        except Exception as e:
            return {
                "success": False,
                "domain": domain,
                "message": f"续费出错: {str(e)}"
            }

    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """获取域名信息"""
        url = f"{self.base_url}/domains/{domain}"

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            data = response.json()

            if response.status_code == 200:
                return {
                    "domain": domain,
                    "status": data.get("status"),
                    "registration_date": data.get("created"),
                    "expiration_date": data.get("expires"),
                    "nameservers": data.get("nameServers", []),
                    "contacts": {
                        "registrant": data.get("contactRegistrant"),
                        "admin": data.get("contactAdmin"),
                        "tech": data.get("contactTech"),
                        "billing": data.get("contactBilling")
                    },
                    "auto_renew": data.get("renewAuto", False)
                }
            else:
                return None
        except Exception as e:
            return None

    def update_nameservers(self, domain: str, nameservers: List[str]) -> Dict[str, Any]:
        """更新域名NS服务器"""
        url = f"{self.base_url}/domains/{domain}/nameservers"

        payload = nameservers

        try:
            response = requests.put(url, headers=self._get_headers(), json=payload)

            if response.status_code in [200, 204]:
                return {
                    "success": True,
                    "message": "NS服务器更新成功"
                }
            else:
                data = response.json()
                return {
                    "success": False,
                    "message": f"更新失败: {data.get('message', '未知错误')}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"更新出错: {str(e)}"
            }

    def transfer_domain(self, domain: str, auth_code: str) -> Dict[str, Any]:
        """
        转入域名

        ⚠️ 已禁用：功能代码保留但API层未暴露
        如需启用请参考 base.py 中的说明
        """
        url = f"{self.base_url}/domains/transfer"

        payload = {
            "domain": domain,
            "authCode": auth_code
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            data = response.json()

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "domain": domain,
                    "message": "转移请求已提交"
                }
            else:
                return {
                    "success": False,
                    "domain": domain,
                    "message": f"转移失败: {data.get('message', '未知错误')}"
                }
        except Exception as e:
            return {
                "success": False,
                "domain": domain,
                "message": f"转移出错: {str(e)}"
            }

    def get_transfer_code(self, domain: str) -> Dict[str, Any]:
        """
        获取域名转移授权码

        ⚠️ 已禁用：功能代码保留但API层未暴露
        如需启用请参考 base.py 中的说明
        """
        url = f"{self.base_url}/domains/{domain}/authCode"

        try:
            response = requests.get(url, headers=self._get_headers())
            data = response.json()

            if response.status_code == 200:
                return {
                    "success": True,
                    "auth_code": data.get("authCode"),
                    "message": "获取成功"
                }
            else:
                return {
                    "success": False,
                    "message": f"获取失败: {data.get('message', '未知错误')}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取出错: {str(e)}"
            }

