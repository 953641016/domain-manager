from app.api.v1.feishu import (
    _extract_operator_ids,
    _is_direct_register_menu_key,
    _message_target_from_menu_context,
    _normalize_domain_name,
    _resolve_dns_account_id,
)


def test_direct_register_menu_keys():
    assert _is_direct_register_menu_key("direct_domain_register")
    assert _is_direct_register_menu_key("domain_direct_register")
    assert not _is_direct_register_menu_key("domain_list")


def test_extract_operator_ids_supports_nested_event_shape():
    operator = {
        "operator_id": {
            "open_id": "ou_xxx",
            "user_id": "u_xxx",
        }
    }

    ids = _extract_operator_ids(operator)

    assert ids["open_id"] == "ou_xxx"
    assert ids["user_id"] == "u_xxx"


def test_message_target_prefers_user_over_chat():
    receive_id, receive_type = _message_target_from_menu_context({
        "open_id": "ou_xxx",
        "chat_id": "oc_xxx",
    })

    assert receive_id == "ou_xxx"
    assert receive_type == "open_id"


def test_normalize_domain_name_accepts_url_and_strips_www():
    assert _normalize_domain_name("https://www.Example.COM/path?a=1") == "example.com"
    assert _normalize_domain_name("*.demo.app") == "demo.app"
    assert _normalize_domain_name("not a domain") == ""


def test_resolve_dns_account_id_falls_back_to_request_default():
    request = type("RequestStub", (), {
        "request_data": {"default_dns_account_id": 7},
        "selected_dns_account_id": None,
    })()

    assert _resolve_dns_account_id({}, request) == 7
    assert _resolve_dns_account_id({"selected_dns_account_id": {"value": "9"}}, request) == 9
