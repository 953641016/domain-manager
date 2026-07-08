from dataclasses import dataclass
from typing import Any

from app.config import Config


@dataclass(frozen=True)
class BackendDnsProfile:
    name: str
    hostname: str
    target: str


def resolve_backend_dns_profile(applicant: Any = None) -> BackendDnsProfile:
    if _matches_jinan_applicant(applicant):
        return BackendDnsProfile(
            name="jinan",
            hostname=Config.BACKEND_DNS_JINAN_HOSTNAME,
            target=Config.BACKEND_DNS_JINAN_TARGET,
        )
    return BackendDnsProfile(
        name="default",
        hostname=Config.BACKEND_DNS_DEFAULT_HOSTNAME,
        target=Config.BACKEND_DNS_DEFAULT_TARGET,
    )


def known_backend_hostnames() -> set[str]:
    return {
        hostname
        for hostname in (
            Config.BACKEND_DNS_DEFAULT_HOSTNAME,
            Config.BACKEND_DNS_JINAN_HOSTNAME,
        )
        if hostname
    }


def _matches_jinan_applicant(applicant: Any = None) -> bool:
    if not applicant:
        return False
    matchers = [item.lower() for item in Config.BACKEND_DNS_JINAN_APPLICANT_MATCHERS if item]
    if not matchers:
        return False
    fields = (
        "department",
        "remark",
        "name",
        "en_name",
        "email",
        "feishu_user_id",
        "feishu_open_id",
        "feishu_union_id",
    )
    values = [
        str(getattr(applicant, field, "") or "").strip().lower()
        for field in fields
    ]
    values = [value for value in values if value]
    return any(matcher in value for matcher in matchers for value in values)
