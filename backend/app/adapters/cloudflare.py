"""
Cloudflare注册商和DNS解析适配器
"""
import re
import time
from typing import Optional, List, Dict, Any

import requests
from app.adapters.base import BaseRegistrarAdapter, BaseDnsProviderAdapter


class CloudflareRegistrarAdapter(BaseRegistrarAdapter):
    """Cloudflare注册商适配器"""

    def __init__(self, api_key: str, account_id: Optional[str] = None):
        super().__init__(api_key)
        self.account_id = account_id
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.timeout = 4
        self.registration_submit_timeout = 15
        self.registration_poll_timeout = 60
        self.registration_poll_interval = 3

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @staticmethod
    def _format_cloudflare_errors(errors: Any, fallback: str = "Cloudflare API 调用失败") -> str:
        if not errors:
            return fallback
        return str(errors)

    @staticmethod
    def _workflow_state(result: Dict[str, Any]) -> str:
        return str(result.get("state") or result.get("status") or "").lower()

    @classmethod
    def _is_workflow_succeeded(cls, result: Dict[str, Any]) -> bool:
        state = cls._workflow_state(result)
        return state in {"succeeded", "success", "completed", "complete", "registered", "done"}

    @classmethod
    def _is_workflow_failed(cls, result: Dict[str, Any]) -> bool:
        state = cls._workflow_state(result)
        return state in {"failed", "failure", "errored", "error", "cancelled", "canceled"}

    @staticmethod
    def _registration_context(result: Dict[str, Any]) -> Dict[str, Any]:
        return ((result.get("context") or {}).get("registration") or {})

    def _registration_payload(
        self,
        domain: str,
        result: Optional[Dict[str, Any]],
        message: str,
        *,
        pending: bool = False,
        unknown: bool = False,
    ) -> Dict[str, Any]:
        result = result or {}
        registration = self._registration_context(result)
        return {
            "success": True,
            "domain": domain,
            "order_id": result.get("id") or result.get("workflow_id"),
            "registration_date": (
                registration.get("created_at")
                or result.get("created_at")
                or result.get("registration_date")
            ),
            "expiration_date": (
                registration.get("expires_at")
                or result.get("expires_at")
                or result.get("expiration_date")
            ),
            "registration_pending": pending,
            "registration_unknown": unknown,
            "workflow_state": self._workflow_state(result),
            "message": message,
        }

    def _get_registration_status(self, domain: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/registrations/{domain}/registration-status"
        response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
        data = response.json()
        if data.get("success"):
            return data.get("result") or {}
        return None

    def _get_registration_resource(self, domain: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/registrations/{domain}"
        response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
        data = response.json()
        if data.get("success"):
            return data.get("result") or {}
        return None

    def _wait_for_registration(self, domain: str, initial_result: Dict[str, Any]) -> Dict[str, Any]:
        return self.wait_for_registration_result(domain, initial_result, self.registration_poll_timeout)

    def wait_for_registration_result(
        self,
        domain: str,
        initial_result: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """轮询 Cloudflare 注册工作流，直到获取最终结果或超时。"""
        deadline = time.monotonic() + (timeout or self.registration_poll_timeout)
        last_result = initial_result or {}

        while time.monotonic() < deadline:
            try:
                status = self._get_registration_status(domain)
            except Exception:
                status = None

            if status is not None:
                last_result = status
                if self._is_workflow_failed(status):
                    return {
                        "success": False,
                        "domain": domain,
                        "message": f"注册工作流失败: {status}",
                    }
                if self._is_workflow_succeeded(status) or status.get("completed") is True:
                    try:
                        resource = self._get_registration_resource(domain)
                    except Exception:
                        resource = None
                    return self._registration_payload(
                        domain,
                        resource or status,
                        "注册成功",
                    )

                state = self._workflow_state(status)
                if state == "action_required":
                    return self._registration_payload(
                        domain,
                        status,
                        f"Cloudflare 注册工作流需要人工处理: {status}",
                        pending=True,
                    )

            try:
                resource = self._get_registration_resource(domain)
            except Exception:
                resource = None
            if resource:
                return self._registration_payload(domain, resource, "注册成功")

            time.sleep(self.registration_poll_interval)

        return self._registration_payload(
            domain,
            last_result,
            f"Cloudflare 已受理注册请求，仍在处理中: {last_result}",
            pending=True,
        )

    def _recover_uncertain_registration(self, domain: str, reason: str) -> Dict[str, Any]:
        try:
            resource = self._get_registration_resource(domain)
        except Exception:
            resource = None
        if resource:
            return self._registration_payload(domain, resource, "注册成功")

        try:
            status = self._get_registration_status(domain)
        except Exception:
            status = None
        if status:
            if self._is_workflow_failed(status):
                return {
                    "success": False,
                    "domain": domain,
                    "message": f"注册工作流失败: {status}",
                }
            return self._registration_payload(
                domain,
                status,
                f"注册请求已提交，等待 Cloudflare 完成。原始异常: {reason}",
                pending=True,
            )

        return self._registration_payload(
            domain,
            {},
            f"注册请求结果未确认，系统已避免自动重试，请到 Cloudflare Registrar 核对最终状态。原始异常: {reason}",
            pending=True,
            unknown=True,
        )

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

    def check_registration_permission(self) -> Dict[str, Any]:
        """检查 Registrar 写权限，不使用可购买域名。"""
        # example.com is reserved and cannot be registered. The API call is
        # used only to distinguish authentication failures from other checks.
        probe_domain = "example.com"
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/registrations"
        payload = {"domain_name": probe_domain}

        try:
            response = requests.post(
                url,
                headers={**self._get_headers(), "Prefer": "respond-async"},
                json=payload,
                timeout=self.timeout,
            )
            data = response.json()

            if data.get("success"):
                return {
                    "success": False,
                    "status": "unexpected_success",
                    "verified": False,
                    "probe_domain": probe_domain,
                    "message": "注册权限探测请求意外被接受，请勿继续重试并立即检查 Cloudflare 注册状态",
                }

            errors = data.get("errors") or []
            error_text = self._format_cloudflare_errors(errors, "Cloudflare 拒绝了注册权限探测请求")
            auth_error = any(
                str(error.get("code")) == "10000"
                and str(error.get("message", "")).lower() == "authentication error"
                for error in errors
                if isinstance(error, dict)
            )
            if auth_error:
                return {
                    "success": False,
                    "status": "permission_denied",
                    "verified": True,
                    "probe_domain": probe_domain,
                    "message": f"Cloudflare 注册写权限不足: {error_text}",
                }

            return {
                "success": True,
                "status": "verified",
                "verified": True,
                "probe_domain": probe_domain,
                "message": f"注册接口鉴权已通过；探测域名未成交: {error_text}",
            }
        except requests.exceptions.Timeout as e:
            return {
                "success": False,
                "status": "unknown",
                "verified": False,
                "probe_domain": probe_domain,
                "message": f"注册写权限暂时无法判断，Cloudflare 请求超时: {e}",
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "status": "unknown",
                "verified": False,
                "probe_domain": probe_domain,
                "message": f"注册写权限暂时无法判断: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "status": "unknown",
                "verified": False,
                "probe_domain": probe_domain,
                "message": f"注册写权限检测出错: {e}",
            }

    def register_domain(
        self,
        domain: str,
        registrant_info: Dict[str, Any],
        nameservers: Optional[List[str]] = None,
        years: int = 1,
    ) -> Dict[str, Any]:
        """注册域名"""
        if years != 1:
            return {
                "success": False,
                "domain": domain,
                "message": "Cloudflare Registrar API currently only supports the default 1-year registration flow"
            }

        url = f"{self.base_url}/accounts/{self.account_id}/registrar/registrations"

        payload = {
            "domain_name": domain
        }

        if registrant_info:
            payload["contacts"] = {"registrant": registrant_info}

        if nameservers:
            payload["nameservers"] = nameservers

        try:
            headers = {**self._get_headers(), "Prefer": "respond-async"}
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.registration_submit_timeout,
            )
            data = response.json()

            if data.get("success"):
                result = data.get("result", {})
                if self._is_workflow_failed(result):
                    return {
                        "success": False,
                        "domain": domain,
                        "message": f"注册工作流失败: {result}",
                    }
                if response.status_code == 201 or self._is_workflow_succeeded(result):
                    return self._registration_payload(domain, result, "注册成功")
                return self._registration_payload(
                    domain,
                    result,
                    f"Cloudflare 已受理注册请求，等待最终结果: {result}",
                    pending=True,
                )
            else:
                errors = data.get("errors", [])
                return {
                    "success": False,
                    "domain": domain,
                    "message": f"注册失败: {self._format_cloudflare_errors(errors)}"
                }
        except requests.exceptions.Timeout as e:
            return self._recover_uncertain_registration(domain, str(e))
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "domain": domain,
                "message": f"注册请求失败: {str(e)}"
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
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/registrations/{domain}"

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            data = response.json()

            if data.get("success"):
                result = data.get("result", {})
                return {
                    "domain": domain,
                    "status": result.get("status") or "active",
                    "registration_date": result.get("created_at") or result.get("registration_date"),
                    "expiration_date": result.get("expires_at") or result.get("expiration_date"),
                    "nameservers": result.get("nameservers", []),
                    "contacts": result.get("contacts", {}),
                    "auto_renew": result.get("auto_renew", False)
                }
        except Exception:
            pass

        legacy_url = f"{self.base_url}/accounts/{self.account_id}/registrar/domains/{domain}"
        try:
            response = requests.get(legacy_url, headers=self._get_headers(), timeout=self.timeout)
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
            return None
        except Exception:
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

    def _redirect_api(self, method, path, **kwargs):
        data = self._request_json(method, f"{self.base_url}{path}", **kwargs)
        if not data.get("success"):
            raise ValueError(self._format_cloudflare_errors(data.get("errors")))
        return data

    def find_redirect_zone(self, domain):
        data = self._redirect_api("GET", "/zones", params={"name": domain})
        zones = [z for z in data.get("result", []) if z.get("name") == domain]
        if not zones:
            return None
        if len(zones) != 1 or zones[0].get("status") != "active" or zones[0].get("paused"):
            raise ValueError("域名 Zone 未激活、已暂停或不唯一")
        return zones[0]

    def _www_dns_records(self, base, host):
        records, page = [], 1
        while True:
            data = self._redirect_api("GET", f"{base}/dns_records", params={"name": host, "page": page, "per_page": 100})
            records.extend(r for r in data.get("result", []) if r.get("name") == host)
            if page >= (data.get("result_info", {}).get("total_pages") or 1):
                return records
            page += 1

    def configure_www_redirect(self, domain, zone_id):
        """专用按钮：逐条更新规则，不覆盖其他规则；API 读回不等于公网验收。"""
        base = f"/zones/{zone_id}"
        host = f"www.{domain}"
        ref = self._redirect_ref(301, host)
        rule = {
            "ref": ref, "enabled": True,
            "description": f"Domain Manager: {host} 301 to {domain}",
            "expression": f'(http.host eq "{host}")',
            "action": "redirect",
            "action_parameters": {"from_value": {
                "target_url": {"expression": f'concat("https://{domain}", http.request.uri.path)'},
                "status_code": 301, "preserve_query_string": True,
            }},
        }
        stage = "preflight"
        try:
            dns = self._www_dns_records(base, host)
            address_records = [r for r in dns if r.get("type") in ("A", "AAAA", "CNAME")]
            if any(r.get("type") == "NS" for r in dns):
                raise ValueError("www 存在 NS 委派，请先处理冲突")
            if any(not r.get("proxiable", False) for r in address_records):
                raise ValueError("www 存在不支持代理的解析记录")
            rulesets = self._redirect_api("GET", f"{base}/rulesets").get("result", [])
            entries = [r for r in rulesets if r.get("kind") == "zone" and r.get("phase") == "http_request_dynamic_redirect"]
            if len(entries) > 1:
                raise ValueError("重定向入口规则集不唯一")
            stage = "rule_write"
            if entries:
                ruleset_id = entries[0]["id"]
                ruleset_path = f"{base}/rulesets/{ruleset_id}"
                existing = self._redirect_api("GET", ruleset_path)["result"]
                matches = [r for r in existing.get("rules", []) if r.get("ref") == ref]
                if len(matches) > 1:
                    raise ValueError("已有多个同标识规则，请先处理冲突")
                payload = {**rule, "position": {"index": 1}}
                if matches:
                    self._redirect_api("PATCH", f"{ruleset_path}/rules/{matches[0]['id']}", json=payload)
                else:
                    self._redirect_api("POST", f"{ruleset_path}/rules", json=payload)
            else:
                created = self._redirect_api("POST", f"{base}/rulesets", json={
                    "name": "Domain Manager Redirect Rules", "kind": "zone",
                    "phase": "http_request_dynamic_redirect", "rules": [rule],
                })["result"]
                ruleset_path = f"{base}/rulesets/{created['id']}"
            # 先写规则再打开代理；失败时报告可能存在的部分配置，重试复用 ref。
            stage = "dns_write"
            if not address_records:
                self._redirect_api("POST", f"{base}/dns_records", json={
                    "type": "A", "name": host, "content": "192.0.2.1", "proxied": True, "ttl": 1,
                })
            else:
                for record in address_records:
                    if not record.get("proxied"):
                        self._redirect_api("PATCH", f"{base}/dns_records/{record['id']}", json={"proxied": True, "ttl": 1})
            stage = "readback"
            read_rules = self._redirect_api("GET", ruleset_path)["result"].get("rules", [])
            matching = [r for r in read_rules if r.get("ref") == ref]
            if len(matching) != 1 or any(matching[0].get(k) != rule[k] for k in ("enabled", "expression", "action", "action_parameters")):
                raise ValueError("重定向规则读回不一致")
            read_dns = [r for r in self._www_dns_records(base, host) if r.get("type") in ("A", "AAAA", "CNAME")]
            if not read_dns or not all(r.get("proxied") for r in read_dns):
                raise ValueError("www 代理解析读回不一致")
            return {
                "status": "configured", "source_host": host, "target_url": f"https://{domain}",
                "status_code": 301, "preserve_path": True, "preserve_query_string": True,
                "rule_id": matching[0]["id"], "zone_id": zone_id,
                "is_config_verified": True, "is_live_verified": False,
                "message": "规则和代理解析已配置并读回；公网跳转及证书尚未验证",
            }
        except (ValueError, KeyError, TypeError) as exc:
            suffix = "未执行远程写入" if stage == "preflight" else "可能已部分写入，可用相同参数重试；请勿视为成功"
            raise ValueError(f"{stage}: {exc}；{suffix}") from exc

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

    @staticmethod
    def _format_cloudflare_errors(errors: Any, fallback: str = "Cloudflare API 调用失败") -> str:
        """保留 Cloudflare API 原始错误，便于排查权限和接口问题。"""
        if not errors:
            return fallback
        return str(errors)

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

        ref = self._redirect_ref(status_code, source_host)
        request_pattern = f"https://{source_host}/*"
        target_pattern = f"{target_base}/${{1}}" if preserve_path else target_base
        escaped_request_pattern = self._escape_ruleset_string(request_pattern)
        escaped_target_pattern = self._escape_ruleset_string(target_pattern)
        target_url = (
            {
                "expression": (
                    "wildcard_replace("
                    f'http.request.full_uri, r"{escaped_request_pattern}", r"{escaped_target_pattern}"'
                    ")"
                )
            }
            if preserve_path else
            {"value": target_base}
        )
        rule = {
            "ref": ref,
            "enabled": True,
            "expression": f'http.request.full_uri wildcard r"{escaped_request_pattern}"',
            "description": f"Domain Manager: {request_pattern} {status_code} redirect to {target_pattern}",
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
            return {"success": False, "message": f"创建重定向规则失败: {self._format_cloudflare_errors(data.get('errors'))}"}

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
        return {"success": False, "message": f"更新重定向规则失败: {self._format_cloudflare_errors(data.get('errors'))}"}

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

