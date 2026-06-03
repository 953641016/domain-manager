"""
Cloudflare注册商和DNS解析适配器
"""
import requests
import re
from typing import Optional, List, Dict, Any
from app.adapters.base import BaseRegistrarAdapter, BaseDnsProviderAdapter


class CloudflareRegistrarAdapter(BaseRegistrarAdapter):
    """Cloudflare注册商适配器"""

    def __init__(self, api_key: str, account_id: Optional[str] = None):
        super().__init__(api_key)
        self.account_id = account_id
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.timeout = 4

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def check_domain_availability(self, domain: str) -> Dict[str, Any]:
        """检查域名是否可注册"""
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/domain-check"
        payload = {"domains": [domain]}

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            data = response.json()

            if data.get("success"):
                domains = (data.get("result") or {}).get("domains") or []
                result = domains[0] if domains else {}
                pricing = result.get("pricing") or {}
                price = pricing.get("registration_cost") or result.get("price")
                return {
                    "available": result.get("registrable", result.get("available", False)),
                    "domain": domain,
                    "price": float(price) if price is not None else None,
                    "currency": pricing.get("currency") or result.get("currency", "USD"),
                    "message": result.get("reason") or result.get("message", ""),
                    "tier": result.get("tier"),
                    "check_successful": True
                }
            else:
                errors = data.get("errors") or []
                return {
                    "available": None,
                    "domain": domain,
                    "message": errors[0].get("message", "检查失败") if errors else "检查失败",
                    "check_successful": False
                }
        except Exception as e:
            return {
                "available": None,
                "domain": domain,
                "message": f"检查出错: {str(e)}",
                "check_successful": False
            }

    def register_domain(self, domain: str, registrant_info: Dict[str, Any], nameservers: Optional[List[str]] = None) -> Dict[str, Any]:
        """注册域名"""
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/domains"

        payload = {
            "domain": domain,
            "contacts": {
                "registrant": registrant_info,
                "admin": registrant_info,
                "tech": registrant_info
            }
        }

        if nameservers:
            payload["nameservers"] = nameservers

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            data = response.json()

            if data.get("success"):
                result = data.get("result", {})
                return {
                    "success": True,
                    "domain": domain,
                    "order_id": result.get("order_id"),
                    "registration_date": result.get("registration_date"),
                    "expiration_date": result.get("expiration_date"),
                    "message": "注册成功"
                }
            else:
                errors = data.get("errors", [])
                return {
                    "success": False,
                    "domain": domain,
                    "message": f"注册失败: {errors}"
                }
        except Exception as e:
            return {
                "success": False,
                "domain": domain,
                "message": f"注册出错: {str(e)}"
            }

    def renew_domain(self, domain: str, years: int = 1) -> Dict[str, Any]:
        """续费域名"""
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/domains/{domain}/renew"

        payload = {
            "years": years
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            data = response.json()

            if data.get("success"):
                result = data.get("result", {})
                return {
                    "success": True,
                    "domain": domain,
                    "expiration_date": result.get("expiration_date"),
                    "message": "续费成功"
                }
            else:
                errors = data.get("errors", [])
                return {
                    "success": False,
                    "domain": domain,
                    "message": f"续费失败: {errors}"
                }
        except Exception as e:
            return {
                "success": False,
                "domain": domain,
                "message": f"续费出错: {str(e)}"
            }

    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """获取域名信息"""
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/domains/{domain}"

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            data = response.json()

            if data.get("success"):
                result = data.get("result", {})
                return {
                    "domain": domain,
                    "status": result.get("status"),
                    "registration_date": result.get("registration_date"),
                    "expiration_date": result.get("expiration_date"),
                    "nameservers": result.get("nameservers", []),
                    "contacts": result.get("contacts", {}),
                    "auto_renew": result.get("auto_renew", False)
                }
            else:
                return None
        except Exception as e:
            return None

    def update_nameservers(self, domain: str, nameservers: List[str]) -> Dict[str, Any]:
        """更新域名NS服务器"""
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/domains/{domain}"

        payload = {
            "nameservers": nameservers
        }

        try:
            response = requests.patch(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            data = response.json()

            if data.get("success"):
                return {
                    "success": True,
                    "message": "NS服务器更新成功"
                }
            else:
                errors = data.get("errors", [])
                return {
                    "success": False,
                    "message": f"更新失败: {errors}"
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
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/domains/transfer"

        payload = {
            "domain": domain,
            "auth_code": auth_code
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            data = response.json()

            if data.get("success"):
                return {
                    "success": True,
                    "domain": domain,
                    "message": "转移请求已提交"
                }
            else:
                errors = data.get("errors", [])
                return {
                    "success": False,
                    "domain": domain,
                    "message": f"转移失败: {errors}"
                }
        except Exception as e:
            return {
                "success": False,
                "domain": domain,
                "message": f"转移出错: {str(e)}"
            }


class CloudflareDnsProviderAdapter(BaseDnsProviderAdapter):
    """Cloudflare DNS解析适配器"""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.cloudflare.com/client/v4"

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_zone_id(self, domain: str) -> Optional[str]:
        """获取域名的Zone ID"""
        url = f"{self.base_url}/zones"
        params = {"name": domain}

        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            data = response.json()

            if data.get("success"):
                zones = data.get("result", [])
                if zones:
                    return zones[0].get("id")
            return None
        except Exception:
            return None

    def _request_json(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """发送 Cloudflare API 请求并返回 JSON，统一处理异常。"""
        try:
            response = requests.request(method, url, headers=self._get_headers(), timeout=10, **kwargs)
            return response.json()
        except Exception as e:
            return {"success": False, "errors": [str(e)]}

    def _get_redirect_ruleset(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """获取 URL Redirect Rules 的 zone phase entrypoint ruleset。"""
        url = f"{self.base_url}/zones/{zone_id}/rulesets/phases/http_request_dynamic_redirect/entrypoint"
        data = self._request_json("GET", url)
        if data.get("success") and data.get("result"):
            return data["result"]
        return None

    @staticmethod
    def _escape_ruleset_string(value: str) -> str:
        """转义 Cloudflare Ruleset 表达式中的字符串字面量。"""
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _redirect_ref(status_code: int, host: str) -> str:
        raw = f"dm_redirect_{status_code}_{host}".lower()
        return re.sub(r"[^a-z0-9_]+", "_", raw).strip("_")[:120]

    @staticmethod
    def _serialize_ruleset_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
        """保留 Rulesets PUT 支持的规则字段，避免回传只读字段。"""
        allowed_keys = {"id", "ref", "enabled", "expression", "description", "action", "action_parameters"}
        return {key: value for key, value in rule.items() if key in allowed_keys and value is not None}

    @staticmethod
    def _normalize_redirect_target(value: str) -> str:
        target = str(value or "").strip()
        if not target:
            return ""
        if not target.startswith(("http://", "https://")):
            target = f"https://{target}"
        return target.rstrip("/")

    def create_redirect_rule(
        self,
        domain: str,
        host: str,
        target: str,
        status_code: int = 301,
        preserve_path: bool = True,
        preserve_query_string: bool = True,
    ) -> Dict[str, Any]:
        """创建或更新 Cloudflare Single Redirect 规则。"""
        zone_id = self.get_zone_id(domain)
        if not zone_id:
            return {"success": False, "message": "无法获取Zone ID"}

        status_code = 302 if int(status_code) == 302 else 301
        source_host = domain if host in ("@", "") else f"{host}.{domain}"
        target_base = self._normalize_redirect_target(target)
        if not target_base:
            return {"success": False, "message": "重定向目标为空"}

        escaped_host = self._escape_ruleset_string(source_host)
        escaped_target = self._escape_ruleset_string(target_base)
        ref = self._redirect_ref(status_code, source_host)
        target_url = (
            {"expression": f'concat("{escaped_target}", http.request.uri.path)'}
            if preserve_path else
            {"value": target_base}
        )
        rule = {
            "ref": ref,
            "enabled": True,
            "expression": f'http.host eq "{escaped_host}"',
            "description": f"Domain Manager: {source_host} {status_code} redirect to {target_base}",
            "action": "redirect",
            "action_parameters": {
                "from_value": {
                    "target_url": target_url,
                    "status_code": status_code,
                    "preserve_query_string": preserve_query_string,
                }
            },
        }

        ruleset = self._get_redirect_ruleset(zone_id)
        if not ruleset:
            payload = {
                "name": "Domain Manager Redirect Rules",
                "kind": "zone",
                "phase": "http_request_dynamic_redirect",
                "rules": [rule],
            }
            data = self._request_json("POST", f"{self.base_url}/zones/{zone_id}/rulesets", json=payload)
            if data.get("success"):
                created = (data.get("result", {}).get("rules") or [{}])[-1]
                return {"success": True, "record_id": created.get("id") or ref, "message": "重定向规则创建成功"}
            return {"success": False, "message": f"创建重定向规则失败: {data.get('errors', [])}"}

        existing_rules = ruleset.get("rules") or []
        updated_rules = []
        matched = False
        for existing in existing_rules:
            if existing.get("ref") == ref:
                matched = True
                existing_id = existing.get("id")
                merged = {**rule}
                if existing_id:
                    merged["id"] = existing_id
                updated_rules.append(merged)
            else:
                updated_rules.append(self._serialize_ruleset_rule(existing))
        if not matched:
            updated_rules.append(rule)

        payload = {
            "name": ruleset.get("name") or "Domain Manager Redirect Rules",
            "description": ruleset.get("description", ""),
            "kind": ruleset.get("kind") or "zone",
            "phase": "http_request_dynamic_redirect",
            "rules": updated_rules,
        }
        data = self._request_json(
            "PUT",
            f"{self.base_url}/zones/{zone_id}/rulesets/{ruleset.get('id')}",
            json=payload,
        )
        if data.get("success"):
            return {
                "success": True,
                "record_id": ref,
                "message": "重定向规则更新成功" if matched else "重定向规则创建成功",
            }
        return {"success": False, "message": f"更新重定向规则失败: {data.get('errors', [])}"}

    def get_records(self, domain: str) -> List[Dict[str, Any]]:
        """获取域名的所有DNS记录"""
        zone_id = self.get_zone_id(domain)
        if not zone_id:
            return []

        url = f"{self.base_url}/zones/{zone_id}/dns_records"
        params = {"type": "A,AAAA,CNAME,MX,TXT,SRV,NS"}

        try:
            response = requests.get(url, headers=self._get_headers(), params=params)
            data = response.json()

            if data.get("success"):
                records = data.get("result", [])
                return [
                    {
                        "id": r.get("id"),
                        "type": r.get("type"),
                        "host": r.get("name").replace(f".{domain}", "") if r.get("name") != domain else "@",
                        "value": r.get("content"),
                        "ttl": r.get("ttl", 300),
                        "priority": r.get("priority"),
                        "proxied": r.get("proxied", False)
                    }
                    for r in records
                ]
            return []
        except Exception:
            return []

    def create_record(self, domain: str, record_type: str, host: str, value: str, ttl: int = 300, priority: Optional[int] = None) -> Dict[str, Any]:
        """创建DNS记录"""
        zone_id = self.get_zone_id(domain)
        if not zone_id:
            return {"success": False, "message": "无法获取Zone ID"}

        url = f"{self.base_url}/zones/{zone_id}/dns_records"

        name = f"{host}.{domain}" if host != "@" and host != "" else domain

        payload = {
            "type": record_type,
            "name": name,
            "content": value,
            "ttl": ttl
        }

        if priority is not None:
            payload["priority"] = priority

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            data = response.json()

            if data.get("success"):
                result = data.get("result", {})
                return {
                    "success": True,
                    "record_id": result.get("id"),
                    "message": "记录创建成功"
                }
            else:
                errors = data.get("errors", [])
                return {
                    "success": False,
                    "message": f"创建失败: {errors}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"创建出错: {str(e)}"
            }

    def update_record(self, domain: str, record_id: str, record_type: str, host: str, value: str, ttl: int = 300, priority: Optional[int] = None) -> Dict[str, Any]:
        """更新DNS记录"""
        zone_id = self.get_zone_id(domain)
        if not zone_id:
            return {"success": False, "message": "无法获取Zone ID"}

        url = f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}"

        name = f"{host}.{domain}" if host != "@" and host != "" else domain

        payload = {
            "type": record_type,
            "name": name,
            "content": value,
            "ttl": ttl
        }

        if priority is not None:
            payload["priority"] = priority

        try:
            response = requests.put(url, headers=self._get_headers(), json=payload)
            data = response.json()

            if data.get("success"):
                return {
                    "success": True,
                    "message": "记录更新成功"
                }
            else:
                errors = data.get("errors", [])
                return {
                    "success": False,
                    "message": f"更新失败: {errors}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"更新出错: {str(e)}"
            }

    def delete_record(self, domain: str, record_id: str) -> Dict[str, Any]:
        """删除DNS记录"""
        zone_id = self.get_zone_id(domain)
        if not zone_id:
            return {"success": False, "message": "无法获取Zone ID"}

        url = f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}"

        try:
            response = requests.delete(url, headers=self._get_headers())
            data = response.json()

            if data.get("success"):
                return {
                    "success": True,
                    "message": "记录删除成功"
                }
            else:
                errors = data.get("errors", [])
                return {
                    "success": False,
                    "message": f"删除失败: {errors}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"删除出错: {str(e)}"
            }

