"""
DNS解析管理服务模块
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.dns import DnsRecord
from app.models.domain import Domain
from app.schemas.dns import DnsRecordCreate, DnsRecordUpdate


class DnsService:
    """DNS服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_records(
        self,
        domain_id: Optional[int] = None,
        domain_ids: Optional[List[int]] = None,
        record_type: Optional[str] = None,
        host: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DnsRecord]:
        """获取DNS记录列表（domain_id 单值优先；domain_ids 用于 domain_spec 多域名范围过滤）"""
        query = self.db.query(DnsRecord)

        if domain_id:
            query = query.filter(DnsRecord.domain_id == domain_id)
        elif domain_ids is not None:
            query = query.filter(DnsRecord.domain_id.in_(domain_ids))
        if record_type:
            query = query.filter(DnsRecord.record_type == record_type)
        if host:
            query = query.filter(DnsRecord.host.contains(host))

        return query.order_by(DnsRecord.created_at.desc()).offset(skip).limit(limit).all()

    def get_record_count(
        self,
        domain_id: Optional[int] = None,
        domain_ids: Optional[List[int]] = None,
        record_type: Optional[str] = None,
        host: Optional[str] = None
    ) -> int:
        """获取DNS记录总数（domain_ids 用于 domain_spec 多域名范围过滤）"""
        query = self.db.query(DnsRecord)

        if domain_id:
            query = query.filter(DnsRecord.domain_id == domain_id)
        elif domain_ids is not None:
            query = query.filter(DnsRecord.domain_id.in_(domain_ids))
        if record_type:
            query = query.filter(DnsRecord.record_type == record_type)
        if host:
            query = query.filter(DnsRecord.host.contains(host))

        return query.count()

    def get_record(self, record_id: int) -> Optional[DnsRecord]:
        """获取DNS记录详情"""
        return self.db.query(DnsRecord).filter(DnsRecord.id == record_id).first()

    def get_records_by_domain(self, domain_id: int) -> List[DnsRecord]:
        """获取域名的所有DNS记录"""
        return self.db.query(DnsRecord).filter(
            DnsRecord.domain_id == domain_id,
            DnsRecord.status != "deleted"
        ).order_by(DnsRecord.record_type, DnsRecord.host).all()

    def create_record(self, data: DnsRecordCreate) -> DnsRecord:
        """创建DNS记录"""
        # 验证域名是否存在
        domain = self.db.query(Domain).filter(Domain.id == data.domain_id).first()
        if not domain:
            raise ValueError("域名不存在")

        # 验证记录类型
        valid_types = ["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS"]
        if data.record_type not in valid_types:
            raise ValueError(f"无效的记录类型: {data.record_type}")

        # MX记录必须有优先级
        if data.record_type == "MX" and data.priority is None:
            raise ValueError("MX记录必须设置优先级")

        # SRV记录必须有优先级、权重和端口
        if data.record_type == "SRV":
            if data.priority is None or data.weight is None or data.port is None:
                raise ValueError("SRV记录必须设置优先级、权重和端口")

        # 检查是否已存在相同记录
        existing = self.db.query(DnsRecord).filter(
            and_(
                DnsRecord.domain_id == data.domain_id,
                DnsRecord.record_type == data.record_type,
                DnsRecord.host == data.host,
                DnsRecord.value == data.value,
                DnsRecord.status != "deleted"
            )
        ).first()
        if existing:
            raise ValueError("相同的DNS记录已存在")

        record = DnsRecord(
            domain_id=data.domain_id,
            record_type=data.record_type,
            host=data.host,
            value=data.value,
            ttl=data.ttl,
            priority=data.priority,
            weight=data.weight,
            port=data.port,
            remark=data.remark,
            status="pending",
            sync_status="pending"
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_record(self, record_id: int, data: DnsRecordUpdate) -> Optional[DnsRecord]:
        """更新DNS记录"""
        record = self.get_record(record_id)
        if not record:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(record, key, value)

        # 标记为需要同步
        if record.sync_status == "synced":
            record.sync_status = "pending"

        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_record(self, record_id: int) -> bool:
        """删除DNS记录（软删除）"""
        record = self.get_record(record_id)
        if not record:
            return False

        record.status = "deleted"
        record.sync_status = "pending"
        self.db.commit()
        return True

    def batch_delete_records(self, record_ids: List[int]) -> int:
        """批量删除DNS记录"""
        count = 0
        for record_id in record_ids:
            if self.delete_record(record_id):
                count += 1
        return count

    def get_pending_sync_records(self, domain_id: Optional[int] = None) -> List[DnsRecord]:
        """获取待同步的DNS记录"""
        query = self.db.query(DnsRecord).filter(
            DnsRecord.sync_status == "pending",
            DnsRecord.status != "deleted"
        )

        if domain_id:
            query = query.filter(DnsRecord.domain_id == domain_id)

        return query.all()

    def mark_record_synced(self, record_id: int, external_id: Optional[str] = None) -> bool:
        """标记记录为已同步"""
        record = self.get_record(record_id)
        if not record:
            return False

        record.sync_status = "synced"
        record.external_id = external_id
        self.db.commit()
        return True

    def mark_record_error(self, record_id: int, error_message: Optional[str] = None) -> bool:
        """标记记录同步失败"""
        record = self.get_record(record_id)
        if not record:
            return False

        record.sync_status = "error"
        self.db.commit()
        return True
