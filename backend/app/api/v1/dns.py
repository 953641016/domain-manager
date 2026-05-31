"""
DNS解析管理API路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, require_manage_users
from app.services.dns_service import DnsService
from app.schemas.dns import (
    DnsRecordCreate, DnsRecordUpdate, DnsRecordResponse, DnsRecordListResponse,
    DnsRecordSyncRequest, DnsRecordSyncResponse
)
from app.models.user import User
from app.models.domain import Domain

router = APIRouter(
    prefix="/dns",
    tags=["DNS解析"],
)


@router.get("/records", response_model=DnsRecordListResponse)
def get_dns_records(
    domain_id: Optional[int] = Query(None, description="域名ID"),
    record_type: Optional[str] = Query(None, description="记录类型"),
    host: Optional[str] = Query(None, description="主机记录"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取DNS记录列表（domain_spec 只能查看自己名下域名的记录）
    """
    service = DnsService(db)

    # domain_spec 只能查看自己名下域名的 DNS 记录
    filter_domain_ids: Optional[List[int]] = None
    if current_user.role == "domain_spec":
        if domain_id is not None:
            # 验证该域名归属当前专员
            domain = db.query(Domain).filter(Domain.id == domain_id).first()
            if not domain or domain.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权查看此域名的DNS记录"
                )
        else:
            # 无 domain_id 过滤时，只返回自己名下域名的记录
            filter_domain_ids = [
                row.id for row in
                db.query(Domain.id).filter(Domain.owner_id == current_user.id).all()
            ]

    records = service.get_records(
        domain_id=domain_id,
        domain_ids=filter_domain_ids,
        record_type=record_type,
        host=host,
        skip=skip,
        limit=limit
    )
    total = service.get_record_count(
        domain_id=domain_id,
        domain_ids=filter_domain_ids,
        record_type=record_type,
        host=host
    )

    return DnsRecordListResponse(
        total=total,
        items=[DnsRecordResponse.model_validate(r) for r in records]
    )


@router.get("/records/{record_id}", response_model=DnsRecordResponse)
def get_dns_record(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取DNS记录详情（domain_spec 只能查看自己名下域名的记录）
    """
    service = DnsService(db)
    record = service.get_record(record_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DNS记录不存在"
        )

    # domain_spec 只能查看自己名下域名的记录
    if current_user.role == "domain_spec":
        domain = db.query(Domain).filter(Domain.id == record.domain_id).first()
        if not domain or domain.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看此DNS记录"
            )

    return DnsRecordResponse.model_validate(record)


@router.get("/domain/{domain_id}")
def get_domain_records(
    domain_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    获取域名的所有DNS记录（domain_spec 只能查看自己名下域名的记录）
    """
    # domain_spec 只能查看自己名下域名的记录
    if current_user.role == "domain_spec":
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain or domain.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看此域名的DNS记录"
            )

    service = DnsService(db)
    records = service.get_records_by_domain(domain_id)

    return {
        "domain_id": domain_id,
        "total": len(records),
        "items": [DnsRecordResponse.model_validate(r) for r in records]
    }





@router.post("/sync", response_model=DnsRecordSyncResponse)
def sync_dns_records(
    request: DnsRecordSyncRequest,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    同步DNS记录

    从DNS服务商同步记录到本地

    注意：此接口需要集成DNS服务商API后才能正常工作
    """
    service = DnsService(db)
    pending_records = service.get_pending_sync_records(request.domain_id)

    if not pending_records:
        return DnsRecordSyncResponse(
            success=True,
            message="没有待同步的记录",
            synced_count=0,
            failed_count=0
        )

    # TODO: 实现实际的DNS服务商API调用
    # 目前返回模拟结果
    return DnsRecordSyncResponse(
        success=True,
        message=f"发现 {len(pending_records)} 条待同步记录，但DNS服务商API尚未集成",
        synced_count=0,
        failed_count=len(pending_records),
        details=[{"record_id": r.id, "status": "pending", "message": "等待API集成"} for r in pending_records[:10]]
    )


@router.get("/record-types")
def get_record_types():
    """
    获取支持的DNS记录类型
    """
    return {
        "record_types": [
            {"type": "A", "name": "A记录", "description": "将域名指向IPv4地址"},
            {"type": "AAAA", "name": "AAAA记录", "description": "将域名指向IPv6地址"},
            {"type": "CNAME", "name": "CNAME记录", "description": "将域名指向另一个域名"},
            {"type": "MX", "name": "MX记录", "description": "邮件交换记录"},
            {"type": "TXT", "name": "TXT记录", "description": "文本记录"},
            {"type": "SRV", "name": "SRV记录", "description": "服务记录"},
            {"type": "NS", "name": "NS记录", "description": "域名服务器记录"}
        ]
    }
