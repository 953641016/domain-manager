import pytest

from app.api.v1.feishu import _resolve_register_domain_override


def test_domain_purchase_accepts_register_domain_override():
    assert _resolve_register_domain_override(
        "domain_purchase",
        "https://www.Example-Domain.com/path?x=1",
    ) == "example-domain.com"


def test_domain_purchase_empty_register_domain_keeps_doc_parse_flow():
    assert _resolve_register_domain_override("domain_purchase", "  ") is None


def test_domain_purchase_rejects_invalid_register_domain():
    with pytest.raises(ValueError, match="register_domain 格式不正确"):
        _resolve_register_domain_override("domain_purchase", "not-a-domain")


def test_dns_actions_ignore_register_domain_override():
    assert _resolve_register_domain_override("clerk_dns", "not-a-domain") is None
