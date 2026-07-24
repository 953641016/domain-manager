from types import SimpleNamespace

from app.api.v1 import domains as domains_api


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def make_service(provider_code):
    decrypted = SimpleNamespace(
        provider_code=provider_code,
        api_key="test-token",
        api_secret="test-secret",
    )
    service = SimpleNamespace(get_dns_account_decrypted=lambda account_id: decrypted)
    account = SimpleNamespace(
        id=3,
        name="test-dns-account",
        provider_code=provider_code,
    )
    return service, account


def test_cloudflare_self_check_rejects_empty_zone_list(monkeypatch):
    service, account = make_service("cloudflare")

    def fake_get(url, **kwargs):
        assert url.endswith("/zones")
        return FakeResponse({
            "success": True,
            "result": [],
            "result_info": {"total_count": 0},
        })

    monkeypatch.setattr(domains_api.requests, "get", fake_get)

    result = domains_api._self_check_dns_account(service, account)

    assert result["success"] is False
    assert result["details"]["zone_count"] == 0
    assert result["checks"][1]["success"] is False
    assert "未读取到任何 Zone" in result["checks"][1]["message"]


def test_cloudflare_self_check_requires_dns_record_read_access(monkeypatch):
    service, account = make_service("cloudflare")

    def fake_get(url, **kwargs):
        if url.endswith("/zones"):
            return FakeResponse({
                "success": True,
                "result": [{"id": "zone-1", "name": "example.com"}],
                "result_info": {"total_count": 1},
            })
        assert url.endswith("/zones/zone-1/dns_records")
        return FakeResponse({"success": True, "result": []})

    monkeypatch.setattr(domains_api.requests, "get", fake_get)

    result = domains_api._self_check_dns_account(service, account)

    assert result["success"] is True
    assert result["details"]["sample_zone"] == "example.com"
    assert result["checks"][-1]["name"] == "DNS 记录读取权限"
    assert result["checks"][-1]["success"] is True


def test_dnspod_self_check_rejects_empty_domain_list(monkeypatch):
    service, account = make_service("dnspod")

    class FakeDnsPodAdapter:
        def _request(self, action, payload):
            return {"DomainCountInfo": {"Total": 0}, "DomainList": []}

    monkeypatch.setattr(
        domains_api.RegistrarFactory,
        "create_dns_provider",
        lambda *args: FakeDnsPodAdapter(),
    )

    result = domains_api._self_check_dns_account(service, account)

    assert result["success"] is False
    assert result["details"]["domain_count"] == 0
    assert result["checks"][0]["success"] is False
