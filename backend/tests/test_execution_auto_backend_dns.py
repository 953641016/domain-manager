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


def test_backend_dns_request_detection_matches_action_or_backend_record():
    by_action = SimpleNamespace(request_data={"action": "backend_dns", "records": []})
    by_record = SimpleNamespace(request_data={"records": [{"provider_section": "backend"}]})
    other = SimpleNamespace(request_data={"action": "clerk_dns", "records": [{"provider_section": "clerk"}]})

    assert ExecutionService._is_backend_dns_request(by_action) is True
    assert ExecutionService._is_backend_dns_request(by_record) is True
    assert ExecutionService._is_backend_dns_request(other) is False
