from types import SimpleNamespace

from app.services.execution_service import ExecutionService


def test_build_auto_backend_dns_request_data_uses_svc_a_record():
    request = SimpleNamespace(
        id="source-request-id",
        domain_name="example.com",
        request_data={
            "doc_url": "https://z78zepeihr.feishu.cn/docx/xxx",
            "doc_token": "doc_token",
            "doc_title": "Example Dev",
            "doc_format": "standard_v1",
        },
    )

    data = ExecutionService._build_auto_backend_dns_request_data(request, target="54.89.199.228")

    assert data["action"] == "backend_dns"
    assert data["action_label"] == "后端接口服务域名解析"
    assert data["auto_created"] is True
    assert data["backend_dns_profile"] == "default"
    assert data["source_request_id"] == "source-request-id"
    assert data["records"] == [
        {
            "hostname": "svc",
            "type": "A",
            "target": "54.89.199.228",
            "provider_section": "backend",
            "ttl": 300,
        }
    ]


def test_build_auto_backend_dns_request_data_uses_jinan_art_record():
    request = SimpleNamespace(
        id="source-request-id",
        domain_name="nanobanana2lite.tools",
        requester=SimpleNamespace(department="\u6d4e\u5357\u7ec4"),
        request_data={
            "doc_url": "https://z1d0kcqb3nl.feishu.cn/docx/STxEdgoTKowKqFxR58actq1Ynxf",
            "doc_token": "doc_token",
            "doc_title": "Nano Banana 2 Lite",
            "doc_format": "standard_v1",
        },
    )

    data = ExecutionService._build_auto_backend_dns_request_data(request)

    assert data["backend_dns_profile"] == "jinan"
    assert data["records"] == [
        {
            "hostname": "art",
            "type": "A",
            "target": "20.9.240.31",
            "provider_section": "backend",
            "ttl": 300,
        }
    ]


def test_backend_dns_request_detection_matches_action_or_backend_record():
    by_action = SimpleNamespace(request_data={"action": "backend_dns", "records": []})
    by_legacy_provider = SimpleNamespace(request_data={"dns_provider": "api_domain", "records": []})
    by_record = SimpleNamespace(request_data={"records": [{"provider_section": "backend"}]})
    other = SimpleNamespace(request_data={"action": "clerk_dns", "records": [{"provider_section": "clerk"}]})

    assert ExecutionService._is_backend_dns_request(by_action) is True
    assert ExecutionService._is_backend_dns_request(by_legacy_provider) is True
    assert ExecutionService._is_backend_dns_request(by_record) is True
    assert ExecutionService._is_backend_dns_request(other) is False


def test_backend_dns_deploy_record_uses_backend_record():
    request = SimpleNamespace(
        domain_name="example.com",
        request_data={
            "action": "backend_dns",
            "records": [
                {
                    "hostname": "svc",
                    "type": "A",
                    "target": "54.89.199.228",
                    "provider_section": "backend",
                }
            ],
        },
    )

    record = ExecutionService._backend_dns_deploy_record(request)

    assert record == {
        "service_domain": "svc.example.com",
        "hostname": "svc",
        "target": "54.89.199.228",
    }


def test_backend_dns_deploy_record_accepts_legacy_api_domain_without_provider_section():
    request = SimpleNamespace(
        domain_name="example.com",
        request_data={
            "dns_provider": "api_domain",
            "records": [
                {
                    "hostname": "svc",
                    "type": "A",
                    "target": "54.89.199.228",
                }
            ],
        },
    )

    record = ExecutionService._backend_dns_deploy_record(
        request,
        [
            {
                "record": {"host": "svc", "type": "A", "value": "54.89.199.228"},
                "status": "success",
            }
        ],
    )

    assert record == {
        "service_domain": "svc.example.com",
        "hostname": "svc",
        "target": "54.89.199.228",
    }


def test_backend_dns_deploy_record_allows_backend_success_when_other_records_fail():
    request = SimpleNamespace(
        domain_name="example.com",
        request_data={
            "action": "all_dns_except_gsc",
            "records": [
                {"hostname": "clerk", "type": "CNAME", "target": "bad.example", "provider_section": "clerk"},
                {"hostname": "svc", "type": "A", "target": "54.89.199.228", "provider_section": "backend"},
            ],
        },
    )

    record = ExecutionService._backend_dns_deploy_record(
        request,
        [
            {"record": {"host": "clerk", "type": "CNAME", "value": "bad.example"}, "status": "failed"},
            {"record": {"host": "svc", "type": "A", "value": "54.89.199.228"}, "status": "success"},
        ],
    )

    assert record["service_domain"] == "svc.example.com"


def test_backend_dns_deploy_record_rejects_failed_backend_record():
    request = SimpleNamespace(
        domain_name="example.com",
        request_data={
            "action": "backend_dns",
            "records": [
                {"hostname": "svc", "type": "A", "target": "54.89.199.228", "provider_section": "backend"},
            ],
        },
    )

    record = ExecutionService._backend_dns_deploy_record(
        request,
        [
            {"record": {"host": "svc", "type": "A", "value": "54.89.199.228"}, "status": "failed"},
        ],
    )

    assert record is None


def test_backend_dns_success_triggers_site_deploy_after_dns_check(monkeypatch):
    calls = []

    class FakeSiteDeploymentService:
        def deploy_and_notify(self, **kwargs):
            calls.append(kwargs)
            return {"success": True, "service_domain": kwargs["domain"]}

    service = ExecutionService.__new__(ExecutionService)
    service.db = None
    monkeypatch.setattr(
        service,
        "_wait_for_backend_dns_resolution",
        lambda service_domain, target: {
            "success": True,
            "service_domain": service_domain,
            "expected_target": target,
            "resolved_records": [target],
        },
    )
    monkeypatch.setattr("app.services.site_deployment_service.SiteDeploymentService", FakeSiteDeploymentService)
    request = SimpleNamespace(
        id="request-id",
        domain_name="example.com",
        requester_name="张三",
        requester=None,
        request_data={
            "action": "backend_dns",
            "doc_url": "https://z78zepeihr.feishu.cn/docx/xxx",
            "records": [
                {
                    "hostname": "svc",
                    "type": "A",
                    "target": "54.89.199.228",
                    "provider_section": "backend",
                }
            ],
        },
    )

    result = service._maybe_deploy_site_after_backend_dns(
        request,
        [
            {
                "record": {"host": "svc", "type": "A", "value": "54.89.199.228"},
                "status": "success",
            }
        ],
    )

    assert result["triggered"] is True
    assert result["success"] is True
    assert calls == [
        {
            "domain": "svc.example.com",
            "doc_url": "https://z78zepeihr.feishu.cn/docx/xxx",
            "operator_name": "张三",
            "applicant": None,
            "feishu_service": None,
        }
    ]
