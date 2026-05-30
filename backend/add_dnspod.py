#!/usr/bin/env python3
"""添加 DNSPod 账号"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.models.domain import DnsAccount
from app.models.user import User
from app.core.encryption import EncryptionService
from app.config import Config


def main():
    db = SessionLocal()
    try:
        # 获取管理员用户
        admin_user = db.query(User).filter(User.role == "super_admin").first() or \
                     db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            print("❌ 没有找到管理员用户")
            return

        # 初始化加密服务
        encryption = EncryptionService(Config.ENCRYPTION_KEY)

        # 检查是否已存在 DNSPod 账号
        existing_account = db.query(DnsAccount).filter(
            DnsAccount.provider_code == "dnspod",
            DnsAccount.name == "DNSPod主账号"
        ).first()

        if existing_account:
            print(f"⚠️ DNSPod 账号已存在 (ID: {existing_account.id})")
            return

        # 创建账号
        account = DnsAccount(
            name="DNSPod主账号",
            provider_code="dnspod",
            api_key=encryption.encrypt(Config.DNSPOD_SECRET_ID),
            api_secret=encryption.encrypt(Config.DNSPOD_SECRET_KEY),
            owner_id=admin_user.id,
            is_active=True,
            remark="用于管理 fwxg.com 等域名的 DNSPod 账号"
        )

        db.add(account)
        db.commit()
        db.refresh(account)

        print(f"✅ DNSPod 账号创建成功")
        print(f"   - ID: {account.id}")
        print(f"   - 名称: {account.name}")
        print(f"   - 解析商: {account.provider_code}")
        print(f"   - 所有者: {admin_user.name} (ID: {admin_user.id})")
        print(f"   - 状态: {'✅ 启用' if account.is_active else '❌ 禁用'}")

    except Exception as e:
        print(f"❌ 创建账号失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
