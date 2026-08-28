from types import SimpleNamespace

from app.services.site_deployment_service import SiteDeploymentService


def test_to_service_domain_prefixes_base_domain():
    assert SiteDeploymentService.to_service_domain("example.com") == "svc.example.com"


def test_to_service_domain_keeps_existing_svc_domain():
    assert SiteDeploymentService.to_service_domain("svc.example.com") == "svc.example.com"


def test_to_service_domain_uses_requested_backend_hostname():
    assert SiteDeploymentService.to_service_domain("svc.example.com", service_hostname="art") == "art.example.com"


def test_build_post_deploy_payload_leaves_future_fields_empty():
    payload = SiteDeploymentService.build_post_deploy_payload(
        base_domain="example.com",
        service_domain="svc.example.com",
        operator_name="Operator",
    )

    assert payload["website_name"] == "example"
    assert payload["url"] == "https://example.com"
    assert payload["api_url"] == "https://svc.example.com"
    assert payload["api_url_source"] == "explicit"
    assert payload["free_score"] is None
    assert payload["package_list"] == []
    assert payload["authors"] == ["Operator"]
    assert payload["appid"] == "example"


def test_build_post_deploy_payload_uses_payment_config():
    payload = SiteDeploymentService.build_post_deploy_payload(
        base_domain="example.com",
        service_domain="svc.example.com",
        operator_name="Operator",
        free_score=10,
        package_list=[{"price": 9.9, "score": 99}],
    )

    assert payload["free_score"] == 10
    assert payload["package_list"] == [{"price": 9.9, "score": 99}]


def test_build_post_deploy_payload_uses_explicit_site_fields():
    payload = SiteDeploymentService.build_post_deploy_payload(
        base_domain="abc-example.com",
        service_domain="svc.abc-example.com",
        operator_name="Operator",
        website_name="Custom Site",
        appid="domaxai",
        authors=["Alice", "  ", "Bob"],
    )

    assert payload["website_name"] == "Custom Site"
    assert payload["appid"] == "domaxai"
    assert payload["authors"] == ["Alice", "Bob"]


def test_infer_appid_avoids_blocked_initial_letters():
    assert SiteDeploymentService.infer_appid("abc-example.com").startswith("site")


def test_parse_stripe_payment_section():
    content = """
## Stripe\u652f\u4ed8\u914d\u7f6e

\u514d\u8d39\u9001 10 \u79ef\u5206\u3002

| \u540d\u79f0 | \u4ef7\u683c | \u79ef\u5206 | \u6bcf\u79ef\u5206\u91d1\u989d | \u7c7b\u578b |
|---|---:|---:|---:|---|
| Starter | $9.9 | 99 \u79ef\u5206 | $0.1 | \u4e00\u6b21\u6027 |
| Basic | $29.9 | 370 \u79ef\u5206 | $0.08 | \u4e00\u6b21\u6027 |
"""
    section = SiteDeploymentService._section(content, "Stripe\u652f\u4ed8\u914d\u7f6e")

    assert SiteDeploymentService.parse_free_score(section) == 10
    assert SiteDeploymentService.parse_markdown_packages(section) == [
        {"price": 9.9, "score": 99},
        {"price": 29.9, "score": 370},
    ]


def test_parse_sheet_payment_rows():
    rows = [
        ["\u5957\u9910", "\u5145\u503c\u79ef\u5206", "1\u79ef\u5206\u5355\u4ef7"],
        ["$9.90", "550", "$0.018"],
        ["$19.90", "1200", "$0.017"],
    ]

    assert SiteDeploymentService.parse_sheet_packages(rows) == [
        {"price": 9.9, "score": 550},
        {"price": 19.9, "score": 1200},
    ]


def test_parse_free_score_from_register_gift():
    assert SiteDeploymentService.parse_free_score("\u6ce8\u518c\u8d60\u900115\u79ef\u5206\uff0c\u53ef\u751f\u4ea73\u5f20") == 15


def test_resolve_service_domain_prefers_backend_record(monkeypatch):
    class FakeParser:
        def resolve_doc_token(self, doc_url):
            return "doc-token"

        def get_document_title(self, doc_token):
            return "Example"

        def get_raw_content(self, doc_token):
            return "content"

        def _normal_lines(self, content):
            return ["content"]

        def _extract_domain(self, lines, title):
            return "example.com"

        def _parse_backend(self, lines, domain):
            return [{"hostname": "svc", "type": "A", "target": "1.2.3.4"}]

    monkeypatch.setattr("app.services.site_deployment_service.FeishuDocParser", FakeParser)

    service_domain, resolution = SiteDeploymentService(deploy_api_token="token").resolve_service_domain(
        domain=None,
        doc_url="https://example.feishu.cn/docx/abc",
    )

    assert service_domain == "svc.example.com"
    assert resolution["source"] == "feishu_doc_backend_record"
    assert resolution["base_domain"] == "example.com"


def test_resolve_service_domain_uses_jinan_profile_for_request_domain():
    applicant = SimpleNamespace(department="\u6d4e\u5357\u7ec4")

    service_domain, resolution = SiteDeploymentService(deploy_api_token="token").resolve_service_domain(
        domain="nanobanana2lite.tools",
        doc_url=None,
        applicant=applicant,
    )

    assert service_domain == "art.nanobanana2lite.tools"
    assert resolution["source"] == "request_domain"
    assert resolution["base_domain"] == "nanobanana2lite.tools"
    assert resolution["backend_dns_profile"] == "jinan"
    assert resolution["backend_dns_hostname"] == "art"
    assert resolution["backend_dns_target"] == "20.9.240.31"


def test_deploy_and_notify_waits_and_skips_post_api(monkeypatch):
    service = SiteDeploymentService(
        deploy_api_url="http://deploy.example.test/deploy-nginx-site",
        deploy_api_token="deploy-token",
        post_deploy_api_url="http://business.example.test/api",
        post_deploy_api_token="post-token",
    )
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(("post", url, headers, json, timeout))
        if url == "http://deploy.example.test/deploy-nginx-site":
            return SimpleNamespace(status_code=202, json=lambda: {"task_id": "task-1", "status": "queued"}, text="")
        return SimpleNamespace(status_code=200, json=lambda: {"ok": True}, text="")

    def fake_get(url, headers=None, timeout=None):
        calls.append(("get", url, headers, None, timeout))
        return SimpleNamespace(status_code=200, json=lambda: {"task_id": "task-1", "status": "success"}, text="")

    monkeypatch.setattr("app.services.site_deployment_service.requests.post", fake_post)
    monkeypatch.setattr("app.services.site_deployment_service.requests.get", fake_get)

    result = service.deploy_and_notify(
        domain="example.com",
        doc_url=None,
        operator_name="Operator",
        timeout_seconds=10,
        poll_interval_seconds=1,
    )

    assert result["success"] is True
    assert result["service_domain"] == "svc.example.com"
    assert result["post_deploy_payload"]["url"] == "https://example.com"
    assert result["post_deploy_payload"]["api_url"] == "https://svc.example.com"
    assert result["post_deploy_payload"]["free_score"] is None
    assert result["post_deploy_payload"]["package_list"] == []
    assert result["post_deploy_result"]["skipped"] is True
    assert calls[0][0] == "post"
    assert calls[1][0] == "get"
    assert len(calls) == 2
    assert calls[2][0] == "post"
