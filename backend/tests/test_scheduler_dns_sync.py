from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.dns import DnsRecord
from app.models.domain import DnsAccount, Domain
from app.models.user import User
from app.tasks.scheduler import TaskScheduler


def make_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def test_merge_remote_dns_records_creates_updates_and_soft_deletes():
    db = make_db_session()
    db.add(User(id=1, name="专员", role="domain_spec"))
    db.add(DnsAccount(id=1, name="CF", provider_code="cloudflare", api_key="token", owner_id=1))
    domain = Domain(id=1, name="example.com", dns_provider_code="cloudflare", dns_account_id=1, owner_id=1)
    db.add(domain)
    db.add(
        DnsRecord(
            domain_id=1,
            record_type="A",
            host="@",
            value="1.1.1.1",
            ttl=300,
            status="active",
            sync_status="synced",
            external_id="same-id",
        )
    )
    db.add(
        DnsRecord(
            domain_id=1,
            record_type="CNAME",
            host="old",
            value="old.example.com",
            ttl=300,
            status="active",
            sync_status="synced",
            external_id="gone-id",
        )
    )
    db.add(
        DnsRecord(
            domain_id=1,
            record_type="TXT",
            host="local",
            value="pending",
            ttl=300,
            status="active",
            sync_status="pending",
        )
    )
    db.commit()

    result = TaskScheduler(db)._merge_remote_dns_records(
        domain,
        [
            {"id": "same-id", "type": "A", "host": "@", "value": "1.1.1.1", "ttl": 600},
            {"id": "new-id", "type": "CNAME", "host": "www", "value": "target.example.com", "ttl": 300},
        ],
    )

    assert result == {
        "created": 1,
        "updated": 1,
        "unchanged": 0,
        "deleted": 1,
        "processed": 3,
    }

    updated = db.query(DnsRecord).filter_by(external_id="same-id").one()
    assert updated.ttl == 600
    assert updated.sync_status == "synced"

    created = db.query(DnsRecord).filter_by(external_id="new-id").one()
    assert created.host == "www"
    assert created.status == "active"

    deleted = db.query(DnsRecord).filter_by(external_id="gone-id").one()
    assert deleted.status == "deleted"
    assert deleted.sync_status == "synced"

    pending = db.query(DnsRecord).filter_by(host="local").one()
    assert pending.status == "active"
    assert pending.sync_status == "pending"
