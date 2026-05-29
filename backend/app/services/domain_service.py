"""
域名管理服务模块
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.domain import Domain, RegAccount, DnsAccount
from app.schemas.domain import (
    DomainCreate, DomainUpdate,
    RegAccountCreate, RegAccountUpdate,
    DnsAccountCreate, DnsAccountUpdate
)


class DomainService:
    """域名服务类"""

    def __init__(self, db: Session):
        self.db = db

    # ========== 域名管理 ==========

    def get_domains(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        registrar_code: Optional[str] = None,
        search: Optional[str] = None,
        owner_id: Optional[int] = None
    ) -> List[Domain]:
        """获取域名列表"""
        query = self.db.query(Domain)

        if status:
            query = query.filter(Domain.status == status)
        if registrar_code:
            query = query.filter(Domain.registrar_code == registrar_code)
        if search:
            query = query.filter(
                or_(
                    Domain.name.contains(search),
                    Domain.remark.contains(search)
                )
            )
        if owner_id:
            query = query.filter(Domain.owner_id == owner_id)

        return query.order_by(Domain.created_at.desc()).offset(skip).limit(limit).all()

    def get_domain_count(
        self,
        status: Optional[str] = None,
        registrar_code: Optional[str] = None,
        search: Optional[str] = None,
        owner_id: Optional[int] = None
    ) -> int:
        """获取域名总数"""
        query = self.db.query(Domain)

        if status:
            query = query.filter(Domain.status == status)
        if registrar_code:
            query = query.filter(Domain.registrar_code == registrar_code)
        if search:
            query = query.filter(
                or_(
                    Domain.name.contains(search),
                    Domain.remark.contains(search)
                )
            )
        if owner_id:
            query = query.filter(Domain.owner_id == owner_id)

        return query.count()

    def get_domain(self, domain_id: int) -> Optional[Domain]:
        """获取域名详情"""
        return self.db.query(Domain).filter(Domain.id == domain_id).first()

    def get_domain_by_name(self, name: str) -> Optional[Domain]:
        """通过域名名称获取"""
        return self.db.query(Domain).filter(Domain.name == name).first()

    def create_domain(self, data: DomainCreate, owner_id: Optional[int] = None) -> Domain:
        """创建域名"""
        # 检查域名是否已存在
        existing = self.get_domain_by_name(data.name)
        if existing:
            raise ValueError(f"域名 {data.name} 已存在")

        domain = Domain(
            name=data.name,
            registrar_code=data.registrar_code,
            reg_account_id=data.reg_account_id,
            dns_provider_code=data.dns_provider_code,
            dns_account_id=data.dns_account_id,
            registration_date=data.registration_date,
            expiration_date=data.expiration_date,
            auto_renew=data.auto_renew,
            registrant_name=data.registrant_name,
            registrant_email=data.registrant_email,
            registrant_phone=data.registrant_phone,
            nameservers=data.nameservers or [],
            tags=data.tags or [],
            remark=data.remark,
            owner_id=owner_id
        )
        self.db.add(domain)
        self.db.commit()
        self.db.refresh(domain)
        return domain



    def get_expiring_domains(self, days: int = 30) -> List[Domain]:
        """获取即将到期的域名"""
        from datetime import timedelta
        threshold = datetime.now() + timedelta(days=days)
        
        return self.db.query(Domain).filter(
            Domain.expiration_date <= threshold,
            Domain.expiration_date > datetime.now(),
            Domain.status == "active"
        ).order_by(Domain.expiration_date.asc()).all()

    # ========== 注册账号管理 ==========

    def get_reg_accounts(
        self,
        skip: int = 0,
        limit: int = 100,
        registrar_code: Optional[str] = None,
        owner_id: Optional[int] = None
    ) -> List[RegAccount]:
        """获取注册账号列表"""
        query = self.db.query(RegAccount)

        if registrar_code:
            query = query.filter(RegAccount.registrar_code == registrar_code)
        if owner_id:
            query = query.filter(RegAccount.owner_id == owner_id)

        return query.order_by(RegAccount.created_at.desc()).offset(skip).limit(limit).all()

    def get_reg_account(self, account_id: int) -> Optional[RegAccount]:
        """获取注册账号详情"""
        return self.db.query(RegAccount).filter(RegAccount.id == account_id).first()

    def create_reg_account(self, data: RegAccountCreate, owner_id: Optional[int] = None) -> RegAccount:
        """创建注册账号"""
        account = RegAccount(
            name=data.name,
            registrar_code=data.registrar_code,
            api_key=data.api_key,
            api_secret=data.api_secret,
            remark=data.remark,
            owner_id=owner_id
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update_reg_account(self, account_id: int, data: RegAccountUpdate) -> Optional[RegAccount]:
        """更新注册账号"""
        account = self.get_reg_account(account_id)
        if not account:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(account, key, value)

        self.db.commit()
        self.db.refresh(account)
        return account

    def delete_reg_account(self, account_id: int) -> bool:
        """删除注册账号"""
        account = self.get_reg_account(account_id)
        if not account:
            return False

        self.db.delete(account)
        self.db.commit()
        return True

    # ========== DNS账号管理 ==========

    def get_dns_accounts(
        self,
        skip: int = 0,
        limit: int = 100,
        provider_code: Optional[str] = None,
        owner_id: Optional[int] = None
    ) -> List[DnsAccount]:
        """获取DNS账号列表"""
        query = self.db.query(DnsAccount)

        if provider_code:
            query = query.filter(DnsAccount.provider_code == provider_code)
        if owner_id:
            query = query.filter(DnsAccount.owner_id == owner_id)

        return query.order_by(DnsAccount.created_at.desc()).offset(skip).limit(limit).all()

    def get_dns_account(self, account_id: int) -> Optional[DnsAccount]:
        """获取DNS账号详情"""
        return self.db.query(DnsAccount).filter(DnsAccount.id == account_id).first()

    def create_dns_account(self, data: DnsAccountCreate, owner_id: Optional[int] = None) -> DnsAccount:
        """创建DNS账号"""
        account = DnsAccount(
            name=data.name,
            provider_code=data.provider_code,
            api_key=data.api_key,
            api_secret=data.api_secret,
            remark=data.remark,
            owner_id=owner_id
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update_dns_account(self, account_id: int, data: DnsAccountUpdate) -> Optional[DnsAccount]:
        """更新DNS账号"""
        account = self.get_dns_account(account_id)
        if not account:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(account, key, value)

        self.db.commit()
        self.db.refresh(account)
        return account

    def delete_dns_account(self, account_id: int) -> bool:
        """删除DNS账号"""
        account = self.get_dns_account(account_id)
        if not account:
            return False

        self.db.delete(account)
        self.db.commit()
        return True
