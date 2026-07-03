import re
import time
from typing import Any, Optional, Sequence
from urllib.parse import urlparse

import requests

from app.config import Config
from app.services.feishu_doc_parser import FeishuDocParser


DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
APPID_RE = re.compile(r"^[a-zA-Z0-9]{1,64}$")
TERMINAL_DEPLOY_STATUSES = {"success", "failed"}
ZH_STRIPE_PAYMENT = "\u0053\u0074\u0072\u0069\u0070\u0065\u652f\u4ed8\u914d\u7f6e"
ZH_PAYMENT_PACKAGE = "\u652f\u4ed8\u5957\u9910"
ZH_REGISTER_GIFT = "\u6ce8\u518c\u8d60\u9001"
ZH_FREE_GIFT = "\u514d\u8d39\u9001"
ZH_GIFT = "\u8d60\u9001"
ZH_SCORE = "\u79ef\u5206"
ZH_POINT = "\u70b9"
ZH_NAME = "\u540d\u79f0"
ZH_PRICE = "\u4ef7\u683c"
ZH_PACKAGE = "\u5957\u9910"
ZH_AMOUNT = "\u91d1\u989d"


class SiteDeploymentError(Exception):
    pass


class SiteDeploymentService:
    def __init__(
        self,
        deploy_api_url: Optional[str] = None,
        deploy_api_token: Optional[str] = None,
        post_deploy_api_url: Optional[str] = None,
        post_deploy_api_token: Optional[str] = None,
    ) -> None:
        self.deploy_api_url = (deploy_api_url or Config.SITE_DEPLOY_API_URL).rstrip("/")
        self.deploy_api_token = deploy_api_token if deploy_api_token is not None else Config.SITE_DEPLOY_API_TOKEN
        self.post_deploy_api_url = post_deploy_api_url if post_deploy_api_url is not None else Config.SITE_POST_DEPLOY_API_URL
        self.post_deploy_api_token = (
            post_deploy_api_token if post_deploy_api_token is not None else Config.SITE_POST_DEPLOY_API_TOKEN
        )

    @staticmethod
    def normalize_domain(value: str) -> str:
        raw = (value or "").strip().lower().rstrip(".")
        if not raw:
            raise ValueError("domain is required")
        if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in raw):
            raise ValueError("domain must not contain whitespace or control characters")
        if "://" in raw:
            parsed = urlparse(raw)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("domain URL scheme must be http or https")
            if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
                raise ValueError("domain URL must only contain scheme and host")
            raw = (parsed.hostname or "").lower().rstrip(".")
        if not DOMAIN_RE.fullmatch(raw):
            raise ValueError("domain must be a valid domain name")
        return raw

    @classmethod
    def to_service_domain(cls, domain: str) -> str:
        normalized = cls.normalize_domain(domain)
        if normalized.startswith("svc."):
            return normalized
        return f"svc.{normalized}"

    @classmethod
    def to_base_domain(cls, domain: str) -> str:
        normalized = cls.normalize_domain(domain)
        if normalized.startswith("svc."):
            return normalized[4:]
        return normalized

    @staticmethod
    def infer_website_name(base_domain: str) -> str:
        return base_domain.split(".", 1)[0]

    @staticmethod
    def infer_appid(base_domain: str) -> str:
        candidate = re.sub(r"[^a-z0-9]", "", base_domain.split(".", 1)[0].lower())
        if not candidate:
            candidate = "site"
        if not candidate[0].isalpha() or candidate[0] in {"a", "b", "c"}:
            candidate = f"site{candidate}"
        return candidate[:64]

    @staticmethod
    def normalize_appid(appid: str) -> str:
        value = (appid or "").strip()
        if not APPID_RE.fullmatch(value):
            raise ValueError("appid must be 1-64 letters or digits")
        if value[0].lower() in {"a", "b", "c"}:
            raise ValueError("appid must not start with a, b, or c")
        return value

    @staticmethod
    def with_https(domain: str) -> str:
        return f"https://{domain}"

    @staticmethod
    def _compact_text(content: str) -> str:
        text = re.sub(r"<[^>]+>", " ", content or "")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _section(content: str, marker: str) -> str:
        match = re.search(re.escape(marker), content or "", flags=re.I)
        if not match:
            return ""
        section = content[match.start():]
        next_heading = re.search(r"\n#{1,6}\s+", section[20:])
        if next_heading:
            return section[:20 + next_heading.start()]
        return section

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        match = re.search(r"(\d+(?:\.\d+)?)", str(value or "").replace(",", ""))
        return float(match.group(1)) if match else None

    @classmethod
    def _money(cls, value: Any) -> Optional[float]:
        return cls._number(value)

    @staticmethod
    def _clean_score(value: Any) -> Optional[int | float]:
        number = SiteDeploymentService._number(value)
        if number is None:
            return None
        return int(number) if number.is_integer() else number

    @staticmethod
    def _looks_price_header(value: Any) -> bool:
        text = str(value or "").strip().lower()
        return any(part in text for part in (ZH_PRICE, ZH_PACKAGE, "price", ZH_AMOUNT))

    @staticmethod
    def _looks_score_header(value: Any) -> bool:
        text = str(value or "").strip().lower()
        return any(part in text for part in (ZH_SCORE, "credit", "score"))

    @classmethod
    def parse_free_score(cls, content: str) -> Optional[int | float]:
        compact = cls._compact_text(content)
        patterns = [
            rf"{ZH_REGISTER_GIFT}.{{0,30}}?(\d+(?:\.\d+)?)\s*(?:{ZH_SCORE}|{ZH_POINT}|credits?|score)",
            rf"{ZH_FREE_GIFT}\s*(\d+(?:\.\d+)?)\s*(?:{ZH_SCORE}|{ZH_POINT}|credits?|score)",
            rf"{ZH_GIFT}\s*(\d+(?:\.\d+)?)\s*(?:{ZH_SCORE}|{ZH_POINT}|credits?|score)",
            r"free[_\s-]*score[^0-9]{0,20}(\d+(?:\.\d+)?)",
            r"Free\s*\|\s*0\s*\|\s*(\d+(?:\.\d+)?)",
            rf"Free\s+0\s+(\d+(?:\.\d+)?)\s*(?:{ZH_SCORE}|credits?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, compact, flags=re.I)
            if match:
                value = float(match.group(1))
                return int(value) if value.is_integer() else value
        return None

    @classmethod
    def parse_markdown_packages(cls, section: str) -> list[dict[str, Any]]:
        packages: list[dict[str, Any]] = []
        for line in (section or "").splitlines():
            line = line.strip()
            if not line.startswith("|") or "---" in line:
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            header = [cell.lower() for cell in cells]
            if any(ZH_NAME in cell or cls._looks_price_header(cell) for cell in header):
                continue
            if len(cells) < 3:
                continue
            name, price_text, score_text = cells[0], cells[1], cells[2]
            if name.strip().lower() == "free":
                continue
            price = cls._money(price_text)
            score = cls._clean_score(score_text)
            if price is not None and price >= 1 and score:
                packages.append({"price": price, "score": score})

        if packages:
            return cls._dedupe_packages(packages)

        compact = cls._compact_text(section)
        pattern = re.compile(
            rf"\b(Starter|Basic|Plus|Professional|Pro|Premium|Creator|Business)\b"
            rf"\s+\$?\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*(?:{ZH_SCORE}|credits?)",
            flags=re.I,
        )
        for match in pattern.finditer(compact):
            price = float(match.group(2))
            score_value = float(match.group(3))
            score = int(score_value) if score_value.is_integer() else score_value
            if price >= 1 and score:
                packages.append({"price": price, "score": score})
        return cls._dedupe_packages(packages)

    @classmethod
    def parse_sheet_packages(cls, rows: Sequence[Sequence[Any]]) -> list[dict[str, Any]]:
        header_index = None
        price_index = None
        score_index = None
        for idx, row in enumerate(list(rows)[:12]):
            price_candidates = [i for i, value in enumerate(row) if cls._looks_price_header(value)]
            score_candidates = [i for i, value in enumerate(row) if cls._looks_score_header(value)]
            if price_candidates and score_candidates:
                header_index = idx
                price_index = price_candidates[0]
                score_index = score_candidates[0]
                break
        if header_index is None or price_index is None or score_index is None:
            return []

        packages: list[dict[str, Any]] = []
        for row in list(rows)[header_index + 1:]:
            price_value = row[price_index] if price_index < len(row) else None
            score_value = row[score_index] if score_index < len(row) else None
            price = cls._money(price_value)
            score = cls._clean_score(score_value)
            if price is not None and price >= 1 and score:
                packages.append({"price": price, "score": score})
        return cls._dedupe_packages(packages)

    @staticmethod
    def _dedupe_packages(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        seen = set()
        for package in packages:
            key = (package.get("price"), package.get("score"))
            if key in seen:
                continue
            seen.add(key)
            result.append(package)
        return result

    def parse_payment_config(self, doc_url: Optional[str]) -> dict[str, Any]:
        if not doc_url:
            return {"free_score": None, "package_list": [], "source": "empty"}

        try:
            parser = FeishuDocParser()
            doc_token = parser.resolve_doc_token(doc_url)
            content = parser.get_raw_content(doc_token)

            stripe_section = self._section(content, ZH_STRIPE_PAYMENT)
            payment_section = self._section(content, ZH_PAYMENT_PACKAGE)
            free_score = self.parse_free_score(stripe_section) if stripe_section else None
            package_list = self.parse_markdown_packages(stripe_section) if stripe_section else []
            source = "stripe_section" if free_score is not None or package_list else "empty"

            if free_score is None:
                free_score = self.parse_free_score(payment_section or content)
                if free_score is not None and source == "empty":
                    source = "payment_text"

            if not package_list and payment_section:
                for ref in parser.list_document_sheet_refs(doc_token):
                    try:
                        rows = parser.get_sheet_values(ref["token"], ref["sheet_id"])
                    except Exception:
                        continue
                    package_list = self.parse_sheet_packages(rows)
                    if package_list:
                        source = "payment_sheet"
                        break
        except Exception as exc:
            return {
                "free_score": None,
                "package_list": [],
                "source": "parse_error",
                "error": str(exc),
            }

        return {
            "free_score": free_score,
            "package_list": package_list,
            "source": source,
        }

    def resolve_service_domain(self, domain: Optional[str], doc_url: Optional[str]) -> tuple[str, dict[str, Any]]:
        if domain and domain.strip():
            service_domain = self.to_service_domain(domain)
            return service_domain, {
                "source": "request_domain",
                "base_domain": self.to_base_domain(service_domain),
            }
        if not doc_url or not doc_url.strip():
            raise ValueError("domain or doc_url is required")

        parser = FeishuDocParser()
        doc_token = parser.resolve_doc_token(doc_url)
        title = parser.get_document_title(doc_token)
        content = parser.get_raw_content(doc_token)
        lines = parser._normal_lines(content)
        raw_base_domain = parser._extract_domain(lines, title)
        if not raw_base_domain:
            raise ValueError("failed to parse base domain from Feishu doc")
        base_domain = self.normalize_domain(raw_base_domain)

        backend_records = parser._parse_backend(lines, base_domain)
        for record in backend_records:
            hostname = str(record.get("hostname") or "").strip().lower().rstrip(".")
            if hostname:
                if hostname == "@":
                    service_domain = self.to_service_domain(base_domain)
                    return service_domain, {
                        "source": "feishu_doc_backend_fallback",
                        "doc_token": doc_token,
                        "doc_title": title,
                        "base_domain": base_domain,
                    }
                service_domain = hostname if hostname.endswith(f".{base_domain}") else f"{hostname}.{base_domain}"
                service_domain = self.normalize_domain(service_domain)
                return service_domain, {
                    "source": "feishu_doc_backend_record",
                    "doc_token": doc_token,
                    "doc_title": title,
                    "base_domain": base_domain,
                }

        service_domain = self.to_service_domain(base_domain)
        return service_domain, {
            "source": "feishu_doc_base_domain",
            "doc_token": doc_token,
            "doc_title": title,
            "base_domain": base_domain,
        }

    def submit_deploy_task(self, service_domain: str) -> dict[str, Any]:
        if not self.deploy_api_token:
            raise SiteDeploymentError("SITE_DEPLOY_API_TOKEN is not configured")
        response = requests.post(
            self.deploy_api_url,
            headers={
                "X-Deploy-Token": self.deploy_api_token,
                "Content-Type": "application/json",
            },
            json={"api_url": service_domain},
            timeout=20,
        )
        if response.status_code >= 400:
            raise SiteDeploymentError(f"deploy API submit failed: HTTP {response.status_code} {response.text}")
        payload = response.json()
        if not payload.get("task_id"):
            raise SiteDeploymentError(f"deploy API response missing task_id: {payload}")
        return payload

    def wait_deploy_task(
        self,
        task_id: str,
        timeout_seconds: Optional[int] = None,
        poll_interval_seconds: Optional[float] = None,
    ) -> dict[str, Any]:
        if not self.deploy_api_token:
            raise SiteDeploymentError("SITE_DEPLOY_API_TOKEN is not configured")
        timeout_seconds = timeout_seconds or Config.SITE_DEPLOY_TIMEOUT_SECONDS
        poll_interval_seconds = poll_interval_seconds or Config.SITE_DEPLOY_POLL_INTERVAL_SECONDS
        deadline = time.monotonic() + timeout_seconds
        last_payload: dict[str, Any] = {}

        while True:
            response = requests.get(
                f"{self.deploy_api_url}/{task_id}",
                headers={"X-Deploy-Token": self.deploy_api_token},
                timeout=20,
            )
            if response.status_code >= 400:
                raise SiteDeploymentError(f"deploy API query failed: HTTP {response.status_code} {response.text}")
            last_payload = response.json()
            if last_payload.get("status") in TERMINAL_DEPLOY_STATUSES:
                return last_payload
            if time.monotonic() >= deadline:
                last_payload["status"] = "timeout"
                last_payload["error"] = f"deploy task did not finish within {timeout_seconds} seconds"
                return last_payload
            time.sleep(poll_interval_seconds)

    @staticmethod
    def build_post_deploy_payload(
        base_domain: str,
        service_domain: str,
        operator_name: str,
        website_name: Optional[str] = None,
        appid: Optional[str] = None,
        authors: Optional[list[str]] = None,
        free_score: Optional[int | float] = None,
        package_list: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        resolved_website_name = (website_name or SiteDeploymentService.infer_website_name(base_domain)).strip()
        if not resolved_website_name:
            raise ValueError("website_name is required")

        resolved_authors = [author.strip() for author in authors or [] if author and author.strip()]
        if not resolved_authors:
            operator = operator_name.strip()
            if not operator:
                raise ValueError("operator_name or authors is required")
            resolved_authors = [operator]

        resolved_appid = SiteDeploymentService.normalize_appid(appid or SiteDeploymentService.infer_appid(base_domain))
        return {
            "website_name": resolved_website_name,
            "url": SiteDeploymentService.with_https(base_domain),
            "api_url": SiteDeploymentService.with_https(service_domain),
            "api_url_source": "explicit",
            "free_score": free_score,
            "package_list": package_list or [],
            "authors": resolved_authors,
            "appid": resolved_appid,
        }

    def call_post_deploy_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.post_deploy_api_url:
            return {"skipped": True, "reason": "SITE_POST_DEPLOY_API_URL is not configured"}

        headers = {"Content-Type": "application/json"}
        if self.post_deploy_api_token:
            header_name = Config.SITE_POST_DEPLOY_API_TOKEN_HEADER or "Authorization"
            token_value = self.post_deploy_api_token
            if header_name.lower() == "authorization" and not token_value.lower().startswith(("bearer ", "basic ")):
                token_value = f"Bearer {token_value}"
            headers[header_name] = token_value

        response = requests.post(self.post_deploy_api_url, headers=headers, json=payload, timeout=30)
        result: dict[str, Any] = {
            "skipped": False,
            "status_code": response.status_code,
        }
        try:
            result["body"] = response.json()
        except Exception:
            result["body"] = response.text
        if response.status_code >= 400:
            raise SiteDeploymentError(f"post-deploy API failed: HTTP {response.status_code} {response.text}")
        return result

    def deploy_and_notify(
        self,
        domain: Optional[str],
        doc_url: Optional[str],
        operator_name: str,
        website_name: Optional[str] = None,
        appid: Optional[str] = None,
        authors: Optional[list[str]] = None,
        timeout_seconds: Optional[int] = None,
        poll_interval_seconds: Optional[float] = None,
    ) -> dict[str, Any]:
        service_domain, resolution = self.resolve_service_domain(domain, doc_url)
        base_domain = str(resolution.get("base_domain") or self.to_base_domain(service_domain))
        payment_config = self.parse_payment_config(doc_url)
        post_payload = self.build_post_deploy_payload(
            base_domain=base_domain,
            service_domain=service_domain,
            operator_name=operator_name,
            website_name=website_name,
            appid=appid,
            authors=authors,
            free_score=payment_config.get("free_score"),
            package_list=payment_config.get("package_list"),
        )
        submit_result = self.submit_deploy_task(service_domain)
        deploy_result = self.wait_deploy_task(
            submit_result["task_id"],
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        post_result = None
        if deploy_result.get("status") == "success":
            post_result = self.call_post_deploy_api(post_payload)
        return {
            "success": deploy_result.get("status") == "success",
            "service_domain": service_domain,
            "resolution": resolution,
            "deploy_submit": submit_result,
            "deploy_result": deploy_result,
            "payment_config": payment_config,
            "post_deploy_payload": post_payload,
            "post_deploy_result": post_result,
        }
