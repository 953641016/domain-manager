from types import SimpleNamespace

from app.services.backend_dns_profile import resolve_backend_dns_profile


def test_jinan_feishu_app_selects_jinan_profile():
    applicant = SimpleNamespace(
        feishu_app=SimpleNamespace(code="jinan"),
        name="林勇胜",
        department="",
        remark="",
    )

    profile = resolve_backend_dns_profile(applicant)

    assert profile.name == "jinan"
    assert profile.hostname == "art"
    assert profile.target == "20.9.240.31"


def test_text_matcher_remains_compatible_without_feishu_app():
    applicant = SimpleNamespace(
        feishu_app=None,
        name="济南业务同事",
        department="",
        remark="",
    )

    profile = resolve_backend_dns_profile(applicant)

    assert profile.name == "jinan"


def test_unknown_feishu_app_uses_default_profile():
    applicant = SimpleNamespace(
        feishu_app=SimpleNamespace(code="laiwu"),
        name="林勇胜",
        department="",
        remark="",
    )

    profile = resolve_backend_dns_profile(applicant)

    assert profile.name == "default"
    assert profile.hostname == "svc"
    assert profile.target == "54.89.199.228"
