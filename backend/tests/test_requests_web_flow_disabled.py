import pytest
from fastapi import HTTPException, status

from app.api.v1 import requests


@pytest.mark.parametrize(
    "handler,args,kwargs",
    [
        (requests.create_request, (), {"data": None, "current_user": None, "db": None}),
        (requests.update_request, ("req-1",), {"data": None, "current_user": None, "db": None}),
        (requests.approve_request, ("req-1",), {"current_user": None, "db": None}),
        (requests.reject_request, ("req-1",), {"data": None, "current_user": None, "db": None}),
        (requests.complete_request, ("req-1",), {"execution_result": None, "current_user": None, "db": None}),
        (requests.fail_request, ("req-1",), {"error_message": "failed", "current_user": None, "db": None}),
    ],
)
def test_web_business_flow_write_handlers_are_disabled(handler, args, kwargs):
    with pytest.raises(HTTPException) as exc:
        handler(*args, **kwargs)

    assert exc.value.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert exc.value.detail == requests.WEB_FLOW_DISABLED_MESSAGE
