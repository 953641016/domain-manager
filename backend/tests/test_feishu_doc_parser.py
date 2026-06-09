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
