from app.services.feishu_doc_parser import FeishuDocParser


def test_parse_vercel_domains_records_json_block():
    parser = FeishuDocParser()
    lines = [
        "Vercel Dns解析",
        '"vercelDomainsRecords": [',
        "{",
        '"host": "joyai-echo.net",',
        '"name": "@",',
        '"type": "A",',
        '"value": "216.150.1.1"',
        "},",
        "{",
        '"host": "www.joyai-echo.net",',
        '"name": "www",',
        '"type": "CNAME",',
        '"value": "18845f95444f57c9.vercel-dns-016.com."',
        "}",
        "]",
        "joyai-echo.net 的 Clerk DNS 配置说明",
        '"domainsRecords": [',
        '{"host": "clerk.joyai-echo.net", "type": "CNAME", "value": "frontend-api.clerk.services"}',
        "]",
    ]

    records = parser._parse_vercel(lines, "joyai-echo.net")

    assert records == [
        {
            "hostname": "@",
            "type": "A",
            "target": "216.150.1.1",
            "provider_section": "vercel",
            "ttl": 300,
        },
        {
            "hostname": "www",
            "type": "CNAME",
            "target": "18845f95444f57c9.vercel-dns-016.com.",
            "provider_section": "vercel",
            "ttl": 300,
        },
    ]


def test_parse_clerk_domains_records_before_vercel_block():
    parser = FeishuDocParser()
    lines = [
        "Vercel Dns解析",
        '"domainsRecords": [',
        "{",
        '"host": "clerk.seedream5pro.co",',
        '"type": "CNAME",',
        '"value": "frontend-api.clerk.services"',
        "},",
        "{",
        '"host": "accounts.seedream5pro.co",',
        '"type": "CNAME",',
        '"value": "accounts.clerk.services"',
        "}",
        "],",
        '"vercelDomainsRecords": [',
        "{",
        '"host": "seedream5pro.co",',
        '"name": "@",',
        '"type": "A",',
        '"value": "216.150.1.1"',
        "}",
        "]",
        "seedream5pro.co 的 Clerk DNS 配置说明",
    ]

    records = parser._parse_clerk(lines, "seedream5pro.co")

    assert records == [
        {
            "hostname": "clerk",
            "type": "CNAME",
            "target": "frontend-api.clerk.services",
            "provider_section": "clerk",
            "ttl": 300,
        },
        {
            "hostname": "accounts",
            "type": "CNAME",
            "target": "accounts.clerk.services",
            "provider_section": "clerk",
            "ttl": 300,
        },
    ]


def test_clerk_domains_records_marker_does_not_match_vercel_key():
    parser = FeishuDocParser()
    lines = [
        "Vercel Dns解析",
        '"vercelDomainsRecords": [',
        '{"host": "www.example.com", "name": "www", "type": "CNAME", "value": "target.example.com."}',
        "]",
    ]

    records = parser._parse_clerk(lines, "example.com")

    assert records == []


def test_extract_domain_from_markdown_domain_heading():
    lines = [
        "Seedream 5.0 AI Image Generator",
        "### 2、域名",
        '<callout emoji="🌀">',
        "# seedream5pro.co",
        "</callout>",
    ]

    assert FeishuDocParser._extract_domain(lines, "Seedream 5.0 Pro") == "seedream5pro.co"


def test_first_domain_ignores_numeric_version():
    assert FeishuDocParser._first_domain("Seedream 5.0 Pro") == ""


def test_parse_metadata_does_not_require_dns_records(monkeypatch):
    parser = FeishuDocParser()
    monkeypatch.setattr(parser, "resolve_doc_token", lambda doc_url: "doc_token")
    monkeypatch.setattr(parser, "get_document_title", lambda doc_token: "GSC example.com 开发需求")
    monkeypatch.setattr(parser, "get_raw_content", lambda doc_token: "只有域名 example.com，没有 GSC 认证段落")

    parsed = parser.parse_metadata("https://z78zepeihr.feishu.cn/docx/example", "gsc_dns")

    assert parsed.doc_token == "doc_token"
    assert parsed.domain == "example.com"
    assert parsed.request_type == "dns_record"
    assert parsed.records == []
    assert parsed.raw_sections == {"metadata_only": True}
