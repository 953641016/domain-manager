from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

from config import Config

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Request(Base):
    __tablename__ = "requests"

    id = Column(String, primary_key=True, default=lambda: f"REQ-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}")
    type = Column(String, nullable=False)
    requester_id = Column(String, nullable=False)
    requester_name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    dns_config = Column(JSON, default=dict)
    status = Column(String, default="pending_approval")
    approval_history = Column(JSON, default=list)
    execution_result = Column(JSON, default=dict)
    conversation_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "domain": self.domain,
            "dns_config": self.dns_config,
            "status": self.status,
            "approval_history": self.approval_history,
            "execution_result": self.execution_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
