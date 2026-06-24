import pytest

from app.api.v1.feishu import (
    DocButtonSubmitBody,
    _build_gsc_verification_record,
    _normalize_gsc_verification,
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


def test_gsc_verification_accepts_direct_value():
    assert _normalize_gsc_verification(
        "google-site-verification=6BUD50tqa1HftbPi51zWqGo4vosFqyt7r7FAOMfFdHY"
    ) == "google-site-verification=6BUD50tqa1HftbPi51zWqGo4vosFqyt7r7FAOMfFdHY"


def test_gsc_verification_accepts_txt_prefix():
    assert _normalize_gsc_verification(
        "TXT google-site-verification=abc123"
    ) == "google-site-verification=abc123"


def test_gsc_verification_empty_keeps_doc_parse_flow():
    assert _normalize_gsc_verification("  ") is None
    assert _normalize_gsc_verification(None) is None


def test_gsc_verification_rejects_invalid_value():
    with pytest.raises(ValueError, match="gsc_verification 格式不正确"):
        _normalize_gsc_verification("abc123")


def test_build_gsc_verification_record():
    assert _build_gsc_verification_record("google-site-verification=abc123") == {
        "hostname": "@",
        "type": "TXT",
        "target": "google-site-verification=abc123",
        "provider_section": "gsc",
        "ttl": 300,
    }
