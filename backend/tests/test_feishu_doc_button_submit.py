import pytest

from app.api.v1.feishu import (
    DocButtonSubmitBody,
    _requires_doc_url_for_doc_button,
    _resolve_register_domain_override,
)


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


def test_domain_purchase_with_register_domain_does_not_require_doc_url():
    body = DocButtonSubmitBody(
        action="domain_purchase",
        applicant_feishu_id="张立坤",
        register_domain="seedance25.studio",
    )

    assert body.doc_url is None
    assert _requires_doc_url_for_doc_button(body.action, body.register_domain) is False


def test_doc_url_required_without_domain_purchase_override():
    assert _requires_doc_url_for_doc_button("domain_purchase", "") is True
    assert _requires_doc_url_for_doc_button("backend_dns", "seedance25.studio") is True
