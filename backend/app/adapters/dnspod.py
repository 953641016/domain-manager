import hashlib
import hmac
import json
import time
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.adapters.base import BaseDnsProviderAdapter


class DnspodDnsProviderAdapter(BaseDnsProviderAdapter):
    """DNSPod (腾讯云) DNS解析适配器"""

    ALGORITHM = "TC3-HMAC-SHA256"
    SERVICE = "dnspod"
    HOST = "dnspod.tencentcloudapi.com"
    ENDPOINT = f"https://{HOST}"
    API_VERSION = "2021-03-23"

    def __init__(self, api_key: str, api_secret: Optional[str] = None):
        super().__init__(api_key, api_secret)

    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _build_auth_headers(self, action: str, payload: str) -> Dict[str, str]:
        timestamp = int(time.time())
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")

        canonical_request = (
            "POST\n/\n\n"
            "content-type:application/json\n"
            f"host:{self.HOST}\n"
            f"x-tc-action:{action.lower()}\n\n"
            "content-type;host;x-tc-action\n"
            f"{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
        )
        credential_scope = f"{date}/{self.SERVICE}/tc3_request"
        string_to_sign = (
            f"{self.ALGORITHM}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        secret_date = self._sign(("TC3" + self.api_secret).encode("utf-8"), date)
        secret_service = self._sign(secret_date, self.SERVICE)
        secret_signing = self._sign(secret_service, "tc3_request")
        signature = hmac.new(
            secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        authorization = (
            f"{self.ALGORITHM} "
            f"Credential={self.api_key}/{credential_scope}, "
            f"SignedHeaders=content-type;host;x-tc-action, "
            f"Signature={signature}"
        )

        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": self.HOST,
            "X-TC-Action": action,
            "X-TC-Version": self.API_VERSION,
            "X-TC-Timestamp": str(timestamp),
        }

    def _request(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload)
        headers = self._build_auth_headers(action, body)
        resp = requests.post(self.ENDPOINT, headers=headers, data=body)
        result = resp.json()
        if "Response" in result:
            error = result["Response"].get("Error")
            if error:
                raise Exception(f"DNSPod API错误: {error.get('Code')} - {error.get('Message')}")
            return result["Response"]
        raise Exception(f"DNSPod请求失败: {result}")

    def _get_domain_id(self, domain: str) -> Optional[int]:
        try:
            resp = self._request("DescribeDomainList", {"Type": "1", "Offset": 0, "Limit": 3000})
            for d in resp.get("DomainList", []):
                if d.get("Name") == domain:
                    return d.get("DomainId")
        except Exception:
            pass
        return None

    def get_zone_id(self, domain: str) -> Optional[str]:
        domain_id = self._get_domain_id(domain)
        return str(domain_id) if domain_id else None

    def get_records(self, domain: str) -> List[Dict[str, Any]]:
        domain_id = self._get_domain_id(domain)
        if not domain_id:
            return []

        try:
            resp = self._request("DescribeRecordList", {
                "Domain": domain,
                "DomainId": domain_id,
                "Offset": 0,
                "Limit": 10000,
            })
            records = resp.get("RecordList", [])
            return [
                {
                    "id": str(r.get("RecordId")),
                    "type": r.get("Type"),
                    "host": r.get("Name", "@"),
                    "value": r.get("Value"),
                    "ttl": r.get("TTL", 300),
                    "priority": r.get("MX") if r.get("Type") == "MX" else None,
                    "line": r.get("Line", "default"),
                    "status": "active" if r.get("Status") == "ENABLE" else "disabled",
                }
                for r in records
            ]
        except Exception:
            return []

    def create_record(
        self,
        domain: str,
        record_type: str,
        host: str,
        value: str,
        ttl: int = 300,
        priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        domain_id = self._get_domain_id(domain)
        if not domain_id:
            return {"success": False, "record_id": None, "message": f"找不到域名 {domain}"}

        payload: Dict[str, Any] = {
            "Domain": domain,
            "DomainId": domain_id,
            "SubDomain": host if host != "@" else "",
            "RecordType": record_type,
            "RecordLine": "默认",
            "Value": value,
            "TTL": ttl,
        }
        if priority is not None and record_type == "MX":
            payload["MX"] = priority

        try:
            resp = self._request("CreateRecord", payload)
            record_id = resp.get("RecordId")
            return {
                "success": True,
                "record_id": str(record_id) if record_id else None,
                "message": "记录创建成功",
            }
        except Exception as e:
            return {"success": False, "record_id": None, "message": f"创建失败: {str(e)}"}

    def update_record(
        self,
        domain: str,
        record_id: str,
        record_type: str,
        host: str,
        value: str,
        ttl: int = 300,
        priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        domain_id = self._get_domain_id(domain)
        if not domain_id:
            return {"success": False, "message": f"找不到域名 {domain}"}

        payload: Dict[str, Any] = {
            "Domain": domain,
            "DomainId": domain_id,
            "RecordId": int(record_id),
            "SubDomain": host if host != "@" else "",
            "RecordType": record_type,
            "RecordLine": "默认",
            "Value": value,
            "TTL": ttl,
        }
        if priority is not None and record_type == "MX":
            payload["MX"] = priority

        try:
            self._request("ModifyRecord", payload)
            return {"success": True, "message": "记录更新成功"}
        except Exception as e:
            return {"success": False, "message": f"更新失败: {str(e)}"}

    def delete_record(self, domain: str, record_id: str) -> Dict[str, Any]:
        domain_id = self._get_domain_id(domain)
        if not domain_id:
            return {"success": False, "message": f"找不到域名 {domain}"}

        try:
            self._request("DeleteRecord", {
                "Domain": domain,
                "DomainId": domain_id,
                "RecordId": int(record_id),
            })
            return {"success": True, "message": "记录删除成功"}
        except Exception as e:
            return {"success": False, "message": f"删除失败: {str(e)}"}
