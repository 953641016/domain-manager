"""
飞书文档域名申请解析服务

将当前两类飞书 docx 文档解析成统一的域名购买/DNS 申请数据。
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests

from app.config import Config


ACTION_LABELS = {
    "domain_purchase": "购买域名",
    "clerk_dns": "Clerk 域名解析",
    "backend_dns": "后端接口服务域名解析",
    "vercel_dns": "Vercel 域名解析",
    "cf_dns": "CF 域名解析",
    "gsc_dns": "GSC 网站认证解析",
    "all_dns_except_gsc": "一键解析 Clerk + 后端 + Vercel + CF",
}

DNS_ACTIONS = {
    "clerk_dns",
    "backend_dns",
    "vercel_dns",
    "cf_dns",
    "gsc_dns",
    "all_dns_except_gsc",
}


@dataclass
class ParsedDocRequest:
    doc_token: str
    doc_url: str
    title: str
    domain: str
    action: str
    request_type: str
    records: List[Dict[str, Any]]
    raw_sections: Dict[str, Any]


class FeishuDocParser:
    """读取飞书 docx 并提取域名/DNS 申请数据。"""

    def __init__(self):
        self.base_url = "https://open.feishu.cn"
        self.app_id = Config.FEISHU_APP_ID
        self.app_secret = Config.FEISHU_APP_SECRET
        self._tenant_token: Optional[str] = None

    def parse(self, doc_url: str, action: str, doc_format: str = "standard_v1") -> ParsedDocRequest:
        if action not in ACTION_LABELS:
            raise ValueError(f"未知 action: {action}")
        if doc_format != "standard_v1":
            raise ValueError(f"暂不支持的文档格式: {doc_format}")

        doc_token = self.resolve_doc_token(doc_url)
        title = self.get_document_title(doc_token)
        content = self.get_raw_content(doc_token)
        lines = self._normal_lines(content)
        domain = self._extract_domain(lines, title)
        if not domain:
            raise ValueError("未能从文档中解析出主域名")

        sections = {
            "cf": self._parse_table_section(lines, "CF域名解析", ["Vercel域名解析"]),
            "vercel": self._parse_vercel(lines, domain),
            "clerk": self._parse_clerk(lines, domain),
            "gsc": self._parse_gsc(lines),
            "backend": self._parse_backend(lines, domain),
        }

        if action == "domain_purchase":
            records: List[Dict[str, Any]] = []
            request_type = "domain_register"
        elif action == "all_dns_except_gsc":
            records = sections["cf"] + sections["vercel"] + sections["clerk"] + sections["backend"]
            request_type = "dns_record"
        else:
            key = action.replace("_dns", "")
            if key == "backend":
                key = "backend"
            records = sections.get(key, [])
            request_type = "dns_record"

        if action in DNS_ACTIONS and not records:
            raise ValueError(f"文档中未解析到 {ACTION_LABELS[action]} 的有效记录")

        return ParsedDocRequest(
            doc_token=doc_token,
            doc_url=doc_url,
            title=title,
            domain=domain,
            action=action,
            request_type=request_type,
            records=records,
            raw_sections=sections,
        )

    @staticmethod
    def extract_doc_token(doc_url: str) -> str:
        doc_token = FeishuDocParser._extract_token_by_type(doc_url, "docx")
        if doc_token:
            return doc_token
        raw_token = FeishuDocParser._extract_direct_token(doc_url)
        if raw_token:
            return raw_token
        raise ValueError("无法从 doc_url 中解析 docx token，请传入飞书 docx 链接或 docx token")

    def resolve_doc_token(self, doc_url: str) -> str:
        doc_token = self._extract_token_by_type(doc_url, "docx")
        if doc_token:
            return doc_token
        wiki_token = self._extract_token_by_type(doc_url, "wiki")
        if wiki_token:
            return self.resolve_wiki_doc_token(wiki_token)
        raw_token = self._extract_direct_token(doc_url)
        if raw_token:
            return raw_token
        raise ValueError("无法从 doc_url 中解析 docx/wiki token，请传入飞书 docx 链接、wiki 链接或 docx token")

    def resolve_wiki_doc_token(self, wiki_token: str) -> str:
        data = self._get(f"/open-apis/wiki/v2/spaces/get_node?token={wiki_token}")
        node = data.get("node") or {}
        obj_type = node.get("obj_type")
        obj_token = node.get("obj_token")
        if obj_type != "docx" or not obj_token:
            raise ValueError(f"Wiki 节点不是新版文档 docx，无法解析内容: obj_type={obj_type or '未知'}")
        return obj_token

    @staticmethod
    def _doc_url_candidates(doc_url: str) -> List[str]:
        value = (doc_url or "").strip()
        if not value:
            return []

        candidates = [value]
        for _ in range(2):
            decoded = unquote(candidates[-1])
            if decoded == candidates[-1]:
                break
            candidates.append(decoded)

        for candidate in list(candidates):
            parsed = urlparse(candidate)
            query = parse_qs(parsed.query)
            for key in ("doc_url", "url", "href", "link", "target"):
                for nested in query.get(key, []):
                    if nested:
                        candidates.append(nested)
                        decoded_nested = unquote(nested)
                        if decoded_nested != nested:
                            candidates.append(decoded_nested)
        return candidates

    @staticmethod
    def _extract_token_by_type(doc_url: str, doc_type: str) -> Optional[str]:
        for candidate in FeishuDocParser._doc_url_candidates(doc_url):
            text = unquote(candidate)
            markdown_match = re.search(r"\]\((https?://[^)]+)\)", text)
            if markdown_match:
                text = markdown_match.group(1)
            match = re.search(rf"(?:^|/){re.escape(doc_type)}/([A-Za-z0-9]+)", urlparse(text).path or text)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _extract_direct_token(doc_url: str) -> Optional[str]:
        for candidate in FeishuDocParser._doc_url_candidates(doc_url):
            text = unquote(candidate)
            if re.fullmatch(r"[A-Za-z0-9]{16,}", text):
                return text
        return None

    def get_document_title(self, doc_token: str) -> str:
        data = self._get(f"/open-apis/docx/v1/documents/{doc_token}")
        return data.get("document", {}).get("title") or doc_token

    def get_raw_content(self, doc_token: str) -> str:
        data = self._get(f"/open-apis/docx/v1/documents/{doc_token}/raw_content")
        return data.get("content") or ""

    def _tenant_access_token(self) -> str:
        if self._tenant_token:
            return self._tenant_token
        response = requests.post(
            f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=15,
        )
        payload = response.json()
        if payload.get("code") != 0:
            raise ValueError(f"获取飞书文档访问令牌失败: {payload.get('msg') or payload}")
        self._tenant_token = payload["tenant_access_token"]
        return self._tenant_token

    def _get(self, path: str) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self._tenant_access_token()}"},
            timeout=20,
        )
        payload = response.json()
        if payload.get("code") != 0:
            raise ValueError(f"读取飞书文档失败: {payload.get('msg') or payload}")
        return payload.get("data") or {}

    @staticmethod
    def _normal_lines(content: str) -> List[str]:
        return [line.strip() for line in content.splitlines() if line.strip()]

    @staticmethod
    def _extract_domain(lines: List[str], title: str) -> str:
        for line in lines:
            match = re.search(r"域名[：:]\s*([A-Za-z0-9.-]+\.[A-Za-z]{2,})", line)
            if match:
                return match.group(1).lower().rstrip(".")
        for idx, line in enumerate(lines):
            if line == "域名购买" and idx + 1 < len(lines):
                candidate = FeishuDocParser._first_domain(lines[idx + 1])
                if candidate:
                    return candidate
        for idx, line in enumerate(lines):
            if re.fullmatch(r"(?:\d+[、.])?\s*域名\s*", line) and idx + 1 < len(lines):
                candidate = FeishuDocParser._first_domain(lines[idx + 1])
                if candidate:
                    return candidate
        return FeishuDocParser._first_domain(title) or ""

    @staticmethod
    def _first_domain(text: str) -> str:
        match = re.search(r"([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)", text)
        return match.group(1).lower().rstrip(".") if match else ""

    @staticmethod
    def _section_lines(lines: List[str], start_marker: str, stop_markers: List[str]) -> List[str]:
        start = None
        for idx, line in enumerate(lines):
            if start_marker in line:
                start = idx + 1
                break
        if start is None:
            return []
        end = len(lines)
        for idx in range(start, len(lines)):
            if any(marker in lines[idx] for marker in stop_markers):
                end = idx
                break
        return lines[start:end]

    def _parse_table_section(self, lines: List[str], start_marker: str, stop_markers: List[str]) -> List[Dict[str, Any]]:
        section = self._section_lines(lines, start_marker, stop_markers)
        if not section:
            return []
        records = []
        idx = 0
        while idx < len(section):
            try:
                header = next(i for i in range(idx, len(section)) if section[i].lower() == "hostname")
            except StopIteration:
                break
            start = header + 3
            end = len(section)
            for cursor in range(start, len(section)):
                line = section[cursor]
                if line.lower() == "hostname" or re.match(r"^\d+[.、]", line):
                    end = cursor
                    break
            values = [
                line for line in section[start:end]
                if line.lower() not in ("hostname", "type", "target")
            ]
            for value_idx in range(0, len(values) - 2, 3):
                host, rtype, target = values[value_idx], values[value_idx + 1], values[value_idx + 2]
                record = self._record(host, rtype, target, start_marker)
                if record:
                    records.append(record)
            idx = max(end, start)
        return records

    def _parse_vercel(self, lines: List[str], domain: str) -> List[Dict[str, Any]]:
        records = self._parse_table_section(lines, "Vercel域名解析", ["Clerk域名解析"])
        if records:
            return records

        records = self._parse_json_like_records_after_marker(
            lines,
            "vercelDomainsRecords",
            domain,
            "vercel",
            ["Clerk DNS", "Clerk域名解析", "后端接口", "GSC", "四、", "接口域名解析"],
        )
        if records:
            return records

        section = self._section_lines(lines, "Vercel Dns解析", ["Clerk DNS", "Clerk域名解析"])
        records = []
        for line in section:
            match = re.match(r"^(\S+)\s+IN\s+(\S+)\s+(.+)$", line, flags=re.I)
            if match:
                record = self._record(match.group(1), match.group(2), match.group(3), "vercel")
                if record:
                    records.append(record)
        return records

    def _parse_clerk(self, lines: List[str], domain: str) -> List[Dict[str, Any]]:
        records = self._parse_table_section(lines, "Clerk域名解析", ["GSC网站认证解析"])
        if records:
            return records

        section = self._section_lines(lines, "Clerk DNS", ["后端接口服务域名解析", "三、后端接口"])
        records = []
        idx = 0
        while idx < len(section):
            if section[idx].startswith("主机名"):
                host = section[idx].split("：", 1)[-1].strip()
                rtype = ""
                target = ""
                for lookahead in section[idx + 1:idx + 5]:
                    if lookahead.startswith("类型"):
                        rtype = lookahead.split("：", 1)[-1].strip()
                    elif lookahead.startswith("目标值"):
                        target = lookahead.split("：", 1)[-1].strip()
                record = self._record(self._relative_host(host, domain), rtype, target, "clerk")
                if record:
                    self._append_record_once(records, record)
            idx += 1
        for record in self._parse_json_like_records(section, domain, "clerk"):
            self._append_record_once(records, record)
        return records

    def _parse_gsc(self, lines: List[str]) -> List[Dict[str, Any]]:
        section = self._section_lines(lines, "GSC网站认证解析", ["接口域名解析", "后端接口服务域名解析"])
        for line in section:
            if "google-site-verification" in line:
                target = line.replace("TXT", "", 1).strip()
                return [self._record("@", "TXT", target, "gsc")]
        return []

    def _parse_backend(self, lines: List[str], domain: str) -> List[Dict[str, Any]]:
        section = self._section_lines(lines, "后端接口服务域名解析", ["网站邮箱支持解析", "三、开发需求", "四、"])
        if not section:
            section = self._section_lines(lines, "接口域名解析", ["网站邮箱支持解析", "三、开发需求", "四、"])
        for line in section:
            candidate = self._first_domain(line)
            if candidate and candidate.endswith(domain):
                target = Config.BACKEND_DNS_DEFAULT_TARGET
                return [self._record(self._relative_host(candidate, domain), "A", target, "backend")]
        return []

    @staticmethod
    def _relative_host(host: str, domain: str) -> str:
        host = host.strip().lower().rstrip(".")
        domain = domain.lower().rstrip(".")
        if host == domain:
            return "@"
        suffix = f".{domain}"
        if host.endswith(suffix):
            return host[:-len(suffix)] or "@"
        return host

    def _record(self, host: str, rtype: str, target: str, section: str) -> Optional[Dict[str, Any]]:
        host = (host or "").strip()
        rtype = self._normalize_type(rtype)
        target = (target or "").strip()
        if not host or not rtype:
            return None
        if rtype in ("CNAME", "A", "AAAA", "TXT", "MX", "NS") and not target:
            return None
        return {
            "hostname": host,
            "type": rtype,
            "target": target,
            "provider_section": section,
            "ttl": 300,
        }

    @staticmethod
    def _append_record_once(records: List[Dict[str, Any]], record: Dict[str, Any]) -> None:
        key = (
            str(record.get("hostname", "")).lower().rstrip("."),
            str(record.get("type", "")).upper(),
            str(record.get("target", "")).lower().rstrip("."),
        )
        for existing in records:
            existing_key = (
                str(existing.get("hostname", "")).lower().rstrip("."),
                str(existing.get("type", "")).upper(),
                str(existing.get("target", "")).lower().rstrip("."),
            )
            if existing_key == key:
                return
        records.append(record)

    def _parse_json_like_records(self, lines: List[str], domain: str, section: str) -> List[Dict[str, Any]]:
        """兼容飞书代码块中的 domainsRecords: host/type/value 结构。"""
        return self._parse_json_like_records_from_lines(lines, domain, section)

    def _parse_json_like_records_after_marker(
        self,
        lines: List[str],
        marker: str,
        domain: str,
        section: str,
        stop_markers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        start = None
        marker_lower = marker.lower()
        for idx, line in enumerate(lines):
            if marker_lower in line.lower():
                start = idx + 1
                break
        if start is None:
            return []

        scoped_lines = []
        stop_markers = stop_markers or []
        for line in lines[start:]:
            if scoped_lines and any(stop_marker in line for stop_marker in stop_markers):
                break
            scoped_lines.append(line)
        return self._parse_json_like_records_from_lines(scoped_lines, domain, section)

    def _parse_json_like_records_from_lines(self, lines: List[str], domain: str, section: str) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        current: Dict[str, str] = {}
        field_map = {
            "host": "host",
            "hostname": "host",
            "name": "name",
            "type": "type",
            "value": "value",
            "target": "value",
        }
        pattern = re.compile(
            r'["“”]?(host|hostname|name|type|value|target)["“”]?\s*[:：]\s*["“”]([^"“”]+)["“”]',
            flags=re.I,
        )
        for line in lines:
            matches = list(pattern.finditer(line))
            if not matches:
                continue
            for match in matches:
                current[field_map[match.group(1).lower()]] = match.group(2).strip()
            host = current.get("host") or current.get("name")
            if host and {"type", "value"}.issubset(current.keys()):
                record = self._record(
                    self._relative_host(host, domain),
                    current["type"],
                    current["value"],
                    section,
                )
                if record:
                    self._append_record_once(records, record)
                current = {}
        return records

    @staticmethod
    def _normalize_type(rtype: str) -> str:
        value = (rtype or "").strip().upper()
        if "301" in value and ("跳转" in value or "重定向" in value):
            return "REDIRECT_301"
        aliases = {
            "CNAME": "CNAME",
            "A": "A",
            "AAAA": "AAAA",
            "TXT": "TXT",
            "MX": "MX",
            "NS": "NS",
        }
        return aliases.get(value, value)
