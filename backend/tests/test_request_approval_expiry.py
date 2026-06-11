from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.domain import DnsAccount, Domain, RegAccount
from app.models.request import Request
from app.models.user import User
from app.services.request_service import REQUEST_APPROVAL_TIMEOUT_REASON, RequestService


def make_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def create_pending_request(db, created_at):
    db.add(User(id=1, name="申请人", role="business"))
    db.add(User(id=2, name="域名专员", role="domain_spec"))
    request = Request(
        id="expired-request",
        type="dns_record",
        requester_id=1,
        requester_name="申请人",
        domain_name="example.com",
        request_data={},
        status="pending",
        created_at=created_at,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def test_approve_request_expires_after_24_hours():
    db = make_db_session()
    request = create_pending_request(db, datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25))
    service = RequestService(db)

    with pytest.raises(ValueError, match="24小时"):
        service.approve_request(request.id, 2, "域名专员")

    db.refresh(request)
    assert request.status == "rejected"
    assert request.reject_reason == REQUEST_APPROVAL_TIMEOUT_REASON
    assert request.approver_id == 2


def test_reject_request_expires_after_24_hours_instead_of_manual_reason():
    db = make_db_session()
    request = create_pending_request(db, datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25))
    service = RequestService(db)

    with pytest.raises(ValueError, match="24小时"):
        service.reject_request(request.id, 2, "域名专员", reason="手动拒绝")

    db.refresh(request)
    assert request.status == "rejected"
    assert request.reject_reason == REQUEST_APPROVAL_TIMEOUT_REASON
