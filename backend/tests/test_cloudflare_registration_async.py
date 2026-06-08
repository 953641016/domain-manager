import requests

from app.adapters.cloudflare import CloudflareRegistrarAdapter


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


def test_cloudflare_registration_timeout_reconciles_existing_registration(monkeypatch):
    adapter = CloudflareRegistrarAdapter("token", account_id="account-id")

    def fake_post(*args, **kwargs):
        raise requests.exceptions.ReadTimeout("read timed out")

    def fake_get(url, **kwargs):
        assert url.endswith("/registrar/registrations/joyai-echo.net")
        return FakeResponse({
            "success": True,
            "result": {
                "id": "registration-1",
                "domain_name": "joyai-echo.net",
                "created_at": "2026-06-08T08:56:07Z",
                "expires_at": "2027-06-08T08:56:07Z",
                "status": "active",
            },
        })

    monkeypatch.setattr("app.adapters.cloudflare.requests.post", fake_post)
    monkeypatch.setattr("app.adapters.cloudflare.requests.get", fake_get)

    result = adapter.register_domain("joyai-echo.net", {}, years=1)

    assert result["success"] is True
    assert result["registration_pending"] is False
    assert result["order_id"] == "registration-1"
    assert result["expiration_date"] == "2027-06-08T08:56:07Z"


def test_cloudflare_registration_accepted_polls_until_succeeded(monkeypatch):
    adapter = CloudflareRegistrarAdapter("token", account_id="account-id")

    def fake_post(url, headers, json, timeout):
        assert headers["Prefer"] == "respond-async"
        return FakeResponse({
            "success": True,
            "result": {
                "workflow_id": "workflow-1",
                "state": "pending",
                "completed": False,
            },
        }, status_code=202)

    def fake_get(url, **kwargs):
        if url.endswith("/registration-status"):
            return FakeResponse({
                "success": True,
                "result": {
                    "workflow_id": "workflow-1",
                    "state": "succeeded",
                    "completed": True,
                },
            })
        return FakeResponse({
            "success": True,
            "result": {
                "id": "registration-2",
                "domain_name": "steady-domain.net",
                "created_at": "2026-06-08T09:00:00Z",
                "expires_at": "2027-06-08T09:00:00Z",
                "status": "active",
            },
        })

    monkeypatch.setattr("app.adapters.cloudflare.requests.post", fake_post)
    monkeypatch.setattr("app.adapters.cloudflare.requests.get", fake_get)
    monkeypatch.setattr("app.adapters.cloudflare.time.sleep", lambda seconds: None)

    result = adapter.register_domain("steady-domain.net", {}, years=1)

    assert result["success"] is True
    assert result["registration_pending"] is False
    assert result["order_id"] == "registration-2"
    assert result["message"] == "注册成功"
