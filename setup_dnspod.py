#!/usr/bin/env python3
"""
设置 DNSPod 账号的完整脚本
1. 生成加密密钥
2. 更新 .env 文件
3. 初始化数据库
4. 创建 DNSPod DNS 账号
"""

import sys
import os
import json
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


def generate_encryption_key():
    """生成 Fernet 加密密钥"""
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        print(f"✅ 生成加密密钥: {key}")
        return key
    except ImportError:
        print("⚠️  cryptography 未安装，尝试安装...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"])
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        print(f"✅ 生成加密密钥: {key}")
        return key


def update_env_file(encryption_key):
    """更新 .env 文件，添加加密密钥"""
    env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "ENCRYPTION_KEY=" in content:
        import re
        content = re.sub(r"ENCRYPTION_KEY=.*", f"ENCRYPTION_KEY={encryption_key}", content)
    else:
        content = content.replace("# 数据加密配置", f"# 数据加密配置\nENCRYPTION_KEY={encryption_key}")
    
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ .env 文件已更新")


def init_database():
    """初始化数据库"""
    from scripts.init_db import init_db
    return init_db()


def create_dnspod_account():
    """创建 DNSPod DNS 账号"""
    from app.core.database import SessionLocal, engine
    from app.models.domain import DnsAccount
    from app.models.user import User
    from app.core.encryption import EncryptionService
    from app.config import Config

    db = SessionLocal()

    try:
        # 获取管理员用户
        admin_user = db.query(User).filter(User.role == "super_admin").first() or \
                     db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            print("❌ 没有找到管理员用户，请先初始化数据库")
            return False

        # 初始化加密服务
        encryption = EncryptionService(Config.ENCRYPTION_KEY)

        # 检查是否已存在 DNSPod 账号
        existing_account = db.query(DnsAccount).filter(
            DnsAccount.provider_code == "dnspod",
            DnsAccount.name == "DNSPod主账号"
        ).first()

        if existing_account:
            print(f"⚠️ DNSPod 账号已存在 (ID: {existing_account.id})")
            return True

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

        return True

    except Exception as e:
        print(f"❌ 创建账号失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


def main():
    print("=" * 70)
    print("域名管家 - DNSPod 账号设置")
    print("=" * 70)

    # 加载环境变量
    load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

    # 步骤 1: 检查加密密钥
    if not Config.ENCRYPTION_KEY:
        print("\n1. 生成加密密钥...")
        key = generate_encryption_key()
        update_env_file(key)
        # 重新加载环境变量
        load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"), override=True)
        from app.config import Config as NewConfig
        globals()['Config'] = NewConfig
    else:
        print("\n1. ✅ 加密密钥已存在")

    # 步骤 2: 初始化数据库
    print("\n2. 初始化数据库...")
    init_database()

    # 步骤 3: 创建 DNSPod 账号
    print("\n3. 创建 DNSPod DNS 账号...")
    create_dnspod_account()

    print("\n" + "=" * 70)
    print("设置完成!")
    print("=" * 70)
    print("\n现在你可以启动应用了:")
    print("  cd backend")
    print("  python -m uvicorn app.main:app --reload")
    print("\n或者使用 Docker:")
    print("  docker-compose up -d")


if __name__ == "__main__":
    from app.config import Config
    main()
