"""专用 apex -> www 配置流程；输入 URL 仅解析，绝不向用户指定地址发请求。"""
import ipaddress
import re
from urllib.parse import urlsplit

from fastapi import HTTPException

from app.adapters.registrar_factory import RegistrarFactory
from app.models.domain import Domain, DnsAccount
from app.services.audit_service import AuditService
from app.services.domain_service import _dec
from app.services.feishu_app_service import get_feishu_service_for_user
from app.services.feishu_doc_parser import FeishuDocParser


def normalize_domain(value):
    text = (value or "").strip()
    if not text or any(c.isspace() for c in text):
        return None
    try:
        parsed = urlsplit(text if "://" in text else "//" + text)
        if parsed.scheme not in ("", "http", "https") or parsed.username or parsed.password or parsed.port:
            return None
        host = (parsed.hostname or "").rstrip(".").encode("idna").decode().lower()
        if host.startswith("www."):
            host = host[4:]
        if len(host) > 253 or "." not in host:
            return None
        if not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in host.split(".")):
            return None
        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            return host if not host.split(".")[-1].isdigit() else None
    except (ValueError, UnicodeError):
        return None


def document_domain(parser, doc_url):
    token = parser.resolve_doc_token(doc_url)
    title = parser.get_document_title(token)
    lines = parser._normal_lines(parser.get_raw_content(token))
    # 仅从主域名字段/域名购买章节/标题取值，避免把 DNS 目标服务商当作目标域名。
    candidates = []
    for i, line in enumerate(lines):
        match = re.match(r"^(?:#+\s*)?(?:主域名|域名)[：:]\s*(.+)$", line)
        if match:
            candidates.extend(re.findall(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", match.group(1)))
        elif line == "域名购买" or re.fullmatch(r"(?:#+\s*)?(?:\d+[、.])?\s*域名\s*", line):
            candidates.append(parser._first_domain_near(lines, i + 1))
    if not candidates:
        candidates = re.findall(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", title)
    domains = {normalize_domain(value) for value in candidates} - {None}
    if len(domains) != 1:
        raise ValueError("文档未提供唯一主域名，请填写 domain 或明确文档中的“域名：”字段")
    return domains.pop()


class WwwRedirectService:
    def __init__(self, db):
        self.db = db

    def resolve_domain(self, actor, domain, doc_url):
        normalized = normalize_domain(domain)
        if normalized:
            return normalized, "domain"
        if not (doc_url or "").strip():
            raise HTTPException(400, "请提供有效的 domain 或可读取的飞书 doc_url")
        try:
            parser = FeishuDocParser(service=get_feishu_service_for_user(self.db, actor))
            return document_domain(parser, doc_url), "doc_url"
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(502, "读取飞书文档失败，请检查应用授权或稍后重试") from exc

    def select_adapter(self, actor, domain):
        local = self.db.query(Domain).filter(Domain.name == domain).first()
        if local and actor.role != "super_admin" and local.owner_id != actor.id:
            raise HTTPException(403, "无权配置此域名")
        query = self.db.query(DnsAccount).filter(
            DnsAccount.is_active.is_(True), DnsAccount.provider_code == "cloudflare"
        )
        if actor.role != "super_admin":
            query = query.filter(DnsAccount.owner_id == actor.id)
        if local and local.dns_account_id:
            query = query.filter(DnsAccount.id == local.dns_account_id)
        accounts = query.all()
        if not accounts:
            raise HTTPException(400, "没有可用且有权限的 Cloudflare DNS 账号")
        matches = []
        for account in accounts:
            api_key = _dec(account.api_key)
            if not api_key:
                raise HTTPException(400, f"DNS 账号 {account.id} 未配置凭据")
            # 不修改 ORM 账号对象，防止随后审计 commit 把解密后的密钥回写到账号表。
            adapter = RegistrarFactory.create_dns_provider("cloudflare", api_key, _dec(account.api_secret))
            try:
                zone = adapter.find_redirect_zone(domain)
            except ValueError as exc:
                raise HTTPException(502, f"DNS 账号 {account.id} 查询失败：{exc}") from exc
            if zone:
                matches.append((account.id, adapter, zone))
        if not matches:
            raise HTTPException(400, "未找到该裸域名的有效 Cloudflare Zone，请检查域名、NS 接入和账号权限")
        if len(matches) != 1:
            raise HTTPException(409, "多个 DNS 账号可访问该域名，请先在域名管理中绑定唯一 DNS 账号")
        return matches[0]

    def configure(self, actor, domain, doc_url):
        domain, source = self.resolve_domain(actor, domain, doc_url)
        account_id, adapter, zone = self.select_adapter(actor, domain)
        audit = AuditService(self.db)
        context = dict(resource_type="domain", resource_name=domain, user_id=actor.id, user_name=actor.name)
        # 在任何远程写入前留下执行记录；审计不可用时不执行。
        audit.log(action="www_redirect_start", after_state={"dns_account_id": account_id, "domain_source": source}, **context)
        try:
            result = adapter.configure_www_redirect(domain, zone["id"])
        except ValueError as exc:
            audit.log(action="www_redirect", status="failed", error_message=str(exc), **context)
            raise HTTPException(502, str(exc)) from exc
        result.update(domain=domain, domain_source=source, dns_account_id=account_id)
        audit.log(action="www_redirect", after_state=result, **context)
        return result
