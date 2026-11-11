from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1 import www_redirects as api
from app.adapters.cloudflare import CloudflareDnsProviderAdapter
from app.core.database import Base, get_db
from app.models.domain import Domain, DnsAccount
from app.models.user import User
from app.services import www_redirect_service as svc


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(id=1, name="spec", feishu_open_id="ou_spec", role="domain_spec", is_active=True))
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(api.Config, "FEISHU_VERIFICATION_TOKEN", "test-only-token")
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("configured,supplied,status", [
    ("test-only-token", "test-only-token", 200),
    ("test-only-token", "wrong", 403),
    ("test-only-token", None, 200),
    ("test-only-token", "", 200),
    ("", "anything", 200),
    ("", None, 200),
])
@pytest.mark.parametrize("transport", ["json", "params"])
def test_token_matches_legacy_button_behavior(client, monkeypatch, configured, supplied, status, transport):
    monkeypatch.setattr(api.Config, "FEISHU_VERIFICATION_TOKEN", configured)
    monkeypatch.setattr(svc.WwwRedirectService, "configure", lambda *a: {"status": "configured"})
    payload = {"domain": "example.com", "applicant_feishu_id": "ou_spec"}
    if supplied is not None:
        payload["verification_token"] = supplied
    response = client.post("/api/v1/www-redirects", **{transport: payload})
    assert response.status_code == status


@pytest.mark.parametrize("role,active", [("business", True), ("admin", True), ("domain_spec", False)])
def test_route_rejects_unprivileged_or_disabled_actor(client, db, role, active):
    user = db.get(User, 1)
    user.role, user.is_active = role, active
    db.commit()
    response = client.post("/api/v1/www-redirects", json={"domain": "example.com", "applicant_feishu_id": "ou_spec"})
    assert response.status_code == 403


def test_missing_applicant_rejected(client):
    assert client.post("/api/v1/www-redirects", json={}).status_code == 422
    assert client.post("/api/v1/www-redirects", params={"domain": "example.com"}).status_code == 422


def test_unknown_applicant_rejected(client):
    response = client.post("/api/v1/www-redirects", json={"domain": "example.com", "applicant_feishu_id": "ou_unknown"})
    assert response.status_code == 403


def test_json_body_takes_precedence_over_query(client, monkeypatch):
    monkeypatch.setattr(svc.WwwRedirectService, "configure", lambda *a: {"status": "configured"})
    response = client.post("/api/v1/www-redirects", params={"verification_token": "test-only-token"},
                           json={"domain": "example.com", "applicant_feishu_id": "ou_spec", "verification_token": "wrong"})
    assert response.status_code == 403


def test_empty_inputs_rejected(client):
    response = client.post("/api/v1/www-redirects", json={"applicant_feishu_id": "ou_spec"})
    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.parametrize("value,expected", [
    ("HTTPS://WWW.Example.COM/a?q=1", "example.com"), ("www.example.co.uk.", "example.co.uk"),
    ("https://user:pass@example.com", None), ("127.0.0.1", None), ("http://[::1]", None),
    ("https://example.com:8443", None), ("bad..com", None), ("-bad.com", None), ("", None),
])
def test_normalize_domain(value, expected):
    assert svc.normalize_domain(value) == expected


def parser_for(content, title="项目"):
    parser = svc.FeishuDocParser(service=SimpleNamespace(app_id="test", app_secret="test"))
    parser.get_document_title = lambda token: title
    parser.get_raw_content = lambda token: content
    return parser


def test_document_domain_ignores_dns_targets():
    parser = parser_for("域名：example.com\nCNAME www cname.vercel-dns.com")
    assert svc.document_domain(parser, "https://x.feishu.cn/docx/abc") == "example.com"


def test_document_multiple_domains_rejected():
    with pytest.raises(ValueError, match="唯一"):
        svc.document_domain(parser_for("域名：one.com\n域名：two.com"), "https://x.feishu.cn/docx/abc")


def test_domain_precedence_and_document_fallback(monkeypatch):
    service = svc.WwwRedirectService(None)
    assert service.resolve_domain(None, "www.example.com", "invalid-doc") == ("example.com", "domain")
    monkeypatch.setattr(svc, "get_feishu_service_for_user", lambda *a: None)
    monkeypatch.setattr(svc, "FeishuDocParser", lambda **kw: parser_for_instance)
    assert service.resolve_domain(None, "", "https://x.feishu.cn/docx/abc") == ("example.com", "doc_url")
    assert service.resolve_domain(None, "invalid", "https://x.feishu.cn/docx/abc") == ("example.com", "doc_url")


parser_for_instance = parser_for("域名：example.com")


def test_other_owner_domain_denied(db):
    db.add(Domain(name="example.com", owner_id=2))
    db.commit()
    with pytest.raises(HTTPException) as exc:
        svc.WwwRedirectService(db).select_adapter(db.get(User, 1), "example.com")
    assert exc.value.status_code == 403


def test_accounts_scoped_and_secrets_not_rewritten(db, monkeypatch):
    db.add_all([DnsAccount(id=1, name="mine", owner_id=1, provider_code="cloudflare", api_key="encrypted"),
                DnsAccount(id=2, name="other", owner_id=2, provider_code="cloudflare", api_key="other")])
    db.commit()
    monkeypatch.setattr(svc, "_dec", lambda value: "decrypted" if value else None)
    adapters = []
    def make_adapter(*args):
        adapters.append(args)
        return SimpleNamespace(find_redirect_zone=lambda d: {"id": "zone"})
    monkeypatch.setattr(svc.RegistrarFactory, "create_dns_provider", make_adapter)
    selected = svc.WwwRedirectService(db).select_adapter(db.get(User, 1), "example.com")
    db.commit()
    db.expire_all()
    assert selected[0] == 1 and len(adapters) == 1
    assert db.get(DnsAccount, 1).api_key == "encrypted"


class FakeCloudflare:
    def __init__(self):
        self.rules = []
        self.dns = []
        self.exists = False
        self.writes = []
        self.fail = None

    def request(self, method, url, **kwargs):
        path = url.split("/zones/zone", 1)[-1]
        if self.fail and self.fail(method, path):
            return {"success": False, "errors": [{"message": "permission denied"}]}
        payload = kwargs.get("json", {})
        if method != "GET":
            self.writes.append((method, path))
        if path == "/dns_records" and method == "GET":
            result = self.dns
        elif path == "/dns_records" and method == "POST":
            self.dns.append({**payload, "id": "dns1", "proxiable": True})
            result = self.dns[-1]
        elif path.startswith("/dns_records/"):
            record = next(r for r in self.dns if r["id"] == path.rsplit("/", 1)[1])
            record.update(payload)
            result = record
        elif path == "/rulesets" and method == "GET":
            result = [{"id": "rs", "kind": "zone", "phase": "http_request_dynamic_redirect"}] if self.exists else []
        elif path == "/rulesets" and method == "POST":
            self.exists = True
            self.rules = [{**r, "id": "rule1"} for r in payload["rules"]]
            result = {"id": "rs", "rules": self.rules}
        elif path == "/rulesets/rs" and method == "GET":
            result = {"rules": self.rules}
        elif path == "/rulesets/rs/rules" and method == "POST":
            self.rules.insert(0, {**payload, "id": "rule1"})
            result = {"rules": self.rules}
        elif path.startswith("/rulesets/rs/rules/") and method == "PATCH":
            rule = next(r for r in self.rules if r["id"] == path.rsplit("/", 1)[1])
            rule.update(payload)
            result = {"rules": self.rules}
        else:
            raise AssertionError((method, path))
        return {"success": True, "result": deepcopy(result)}


def adapter_with_fake(monkeypatch):
    adapter = CloudflareDnsProviderAdapter("test-only-token")
    fake = FakeCloudflare()
    monkeypatch.setattr(adapter, "_request_json", fake.request)
    return adapter, fake


def test_configure_and_repeat_are_idempotent(monkeypatch):
    adapter, fake = adapter_with_fake(monkeypatch)
    first = adapter.configure_www_redirect("example.com", "zone")
    second = adapter.configure_www_redirect("example.com", "zone")
    assert first == second
    assert first["status"] == "configured" and first["is_live_verified"] is False
    assert len(fake.rules) == len(fake.dns) == 1
    assert fake.rules[0]["expression"] == '(http.host eq "www.example.com")'
    params = fake.rules[0]["action_parameters"]["from_value"]
    assert params["target_url"]["expression"] == 'concat("https://example.com", http.request.uri.path)'
    assert params["status_code"] == 301 and params["preserve_query_string"] is True


def test_existing_records_and_unrelated_rules_preserved(monkeypatch):
    adapter, fake = adapter_with_fake(monkeypatch)
    fake.exists = True
    unrelated = {"id": "other", "ref": "other", "action": "redirect"}
    fake.rules = [deepcopy(unrelated)]
    fake.dns = [{"id": "dns1", "name": "www.example.com", "type": "CNAME", "content": "existing.example.net", "proxiable": True, "proxied": False}]
    adapter.configure_www_redirect("example.com", "zone")
    assert fake.rules[1] == unrelated
    assert fake.dns[0]["content"] == "existing.example.net" and fake.dns[0]["proxied"]
    assert all(method != "PUT" for method, _ in fake.writes)


def test_read_permission_failure_does_not_write(monkeypatch):
    adapter, fake = adapter_with_fake(monkeypatch)
    fake.fail = lambda method, path: path == "/rulesets"
    with pytest.raises(ValueError, match="未执行远程写入"):
        adapter.configure_www_redirect("example.com", "zone")
    assert fake.writes == []


def test_partial_failure_can_be_retried(monkeypatch):
    adapter, fake = adapter_with_fake(monkeypatch)
    fake.fail = lambda method, path: path == "/dns_records" and method == "POST"
    with pytest.raises(ValueError, match="可能已部分写入"):
        adapter.configure_www_redirect("example.com", "zone")
    assert len(fake.rules) == 1 and not fake.dns
    fake.fail = None
    adapter.configure_www_redirect("example.com", "zone")
    assert len(fake.rules) == len(fake.dns) == 1


def test_http_endpoint_result_and_audit(client, db, monkeypatch):
    adapter, _ = adapter_with_fake(monkeypatch)
    monkeypatch.setattr(svc.WwwRedirectService, "select_adapter", lambda *a: (1, adapter, {"id": "zone"}))
    response = client.post("/api/v1/www-redirects", json={"domain": "www.example.com", "applicant_feishu_id": "ou_spec"})
    assert response.status_code == 200
    assert response.json()["domain"] == "example.com"
    from app.models.audit import AuditLog
    assert db.query(AuditLog).count() == 2


@pytest.mark.parametrize("status,paused", [("pending", False), ("active", True)])
def test_zone_must_be_active_and_not_paused(monkeypatch, status, paused):
    adapter = CloudflareDnsProviderAdapter("test-only-token")
    monkeypatch.setattr(adapter, "_request_json", lambda *a, **kw: {
        "success": True, "result": [{"id": "zone", "name": "example.com", "status": status, "paused": paused}],
    })
    with pytest.raises(ValueError):
        adapter.find_redirect_zone("example.com")


def test_readback_failure_is_not_success(monkeypatch):
    adapter, fake = adapter_with_fake(monkeypatch)
    original = fake.request
    def corrupt_readback(method, url, **kwargs):
        result = original(method, url, **kwargs)
        if method == "GET" and url.endswith("/rulesets/rs") and fake.dns:
            result["result"]["rules"][0]["enabled"] = False
        return result
    monkeypatch.setattr(adapter, "_request_json", corrupt_readback)
    with pytest.raises(ValueError, match="读回不一致"):
        adapter.configure_www_redirect("example.com", "zone")


def test_ns_delegation_blocks_writes(monkeypatch):
    adapter, fake = adapter_with_fake(monkeypatch)
    fake.dns = [{"id": "ns1", "name": "www.example.com", "type": "NS"}]
    with pytest.raises(ValueError, match="NS 委派"):
        adapter.configure_www_redirect("example.com", "zone")
    assert not fake.writes


def test_ambiguous_accounts_require_binding(db, monkeypatch):
    db.add_all([DnsAccount(name="a", owner_id=1, provider_code="cloudflare", api_key="test"),
                DnsAccount(name="b", owner_id=1, provider_code="cloudflare", api_key="test")])
    db.commit()
    monkeypatch.setattr(svc.RegistrarFactory, "create_dns_provider", lambda *a: SimpleNamespace(find_redirect_zone=lambda d: {"id": "zone"}))
    with pytest.raises(HTTPException) as exc:
        svc.WwwRedirectService(db).select_adapter(db.get(User, 1), "example.com")
    assert exc.value.status_code == 409
