import json
from datetime import datetime
from types import SimpleNamespace

from app.services.feishu_service import FeishuService
from app.services.execution_service import ExecutionService
from app.services.user_confirmation_service import UserOperationConfirmationService
from app.api.v1.feishu import _build_domain_purchase_approval_card


def test_update_card_message_serializes_interactive_card(monkeypatch):
    captured = {}

    class FakeResponse:
        def json(self):
            return {"code": 0, "data": {"message_id": "om_xxx"}}

    def fake_patch(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.services.feishu_service.requests.patch", fake_patch)
    service = FeishuService()
    monkeypatch.setattr(service, "get_app_access_token", lambda: "test-token")

    card = {
        "config": {"wide_screen_mode": True, "update_multi": True},
        "elements": [],
    }
    result = service.update_card_message("om_xxx", card)

    assert result["code"] == 0
    assert captured["url"].endswith("/open-apis/im/v1/messages/om_xxx")
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["payload"]["content"] == json.dumps(card)
    assert captured["timeout"] == 10


def test_processed_confirmation_card_marks_approved_and_removes_actions():
    service = UserOperationConfirmationService(db=None)
    confirmation = SimpleNamespace(
        operation_type="create_user",
        operation_details={
            "action": "create_user",
            "user_data": {"name": "段希宝", "role": "business"},
        },
        target_user_data={},
        requires_super_admin=True,
        initiator_name="张健",
        approver_name="徐勤杰",
        confirmed_at=datetime(2026, 6, 9, 16, 3, 2),
        reject_reason=None,
    )

    card = service._build_processed_confirmation_card(
        confirmation,
        approved=True,
        exec_error=None,
    )
    card_text = json.dumps(card, ensure_ascii=False)

    assert card["config"]["update_multi"] is True
    assert card["header"]["title"]["content"] == "✅ 已授权：用户管理授权申请"
    assert "**状态**：已授权" in card_text
    assert "段希宝" in card_text
    assert "form_submit" not in card_text
    assert "授权执行" not in card_text
    assert "拒绝申请" not in card_text


def test_domain_purchase_approval_card_is_updateable():
    request = SimpleNamespace(
        id="abcdef123456",
        type="domain_register",
        domain_name="example.com",
        created_at=datetime(2026, 6, 9, 16, 0, 0),
        request_data={"doc_title": "需求文档", "doc_url": "https://example.com/doc"},
    )
    applicant = SimpleNamespace(name="申请人")
    reviewer = SimpleNamespace(name="域名专员")
    account = SimpleNamespace(id=1, name="Cy1408569", registrar_code="cloudflare")

    card = _build_domain_purchase_approval_card(request, applicant, reviewer, [account])
    card_text = json.dumps(card, ensure_ascii=False)

    assert card["config"]["update_multi"] is True
    assert "approve_doc_request" in card_text
    assert "reject_doc_request" in card_text


def test_request_card_status_handles_pending_partial_and_failed():
    request = SimpleNamespace(type="domain_register")
    assert ExecutionService._request_card_status(
        request,
        {"success": True, "registration_pending": True},
        True,
    ) == "已提交，待确认"

    request = SimpleNamespace(type="dns_record")
    assert ExecutionService._request_card_status(
        request,
        {"total": 3, "success_count": 1},
        True,
    ) == "部分成功"
    assert ExecutionService._request_card_status(request, {}, False) == "执行失败"
