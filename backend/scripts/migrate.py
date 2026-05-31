#!/usr/bin/env python3
"""
数据库迁移脚本（幂等，可重复执行）
策略：PRAGMA table_info 检测缺失列 → ALTER TABLE ADD COLUMN 补列
     Base.metadata.create_all 创建新表
用法：python scripts/migrate.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.core.database import engine, SessionLocal, Base

# ===== 导入所有模型确保 metadata 完整 =====
from app.models.user import User
from app.models.domain import Domain, RegAccount, DnsAccount, Registrar, DnsProvider
from app.models.request import Request
from app.models.dns import DnsRecord
from app.models.audit import AuditLog
from app.models.user_confirmation import UserOperationConfirmation

# ===== 需要补的列（表名 → [(列名, DDL类型, 默认值)] ） =====
COLUMNS_TO_ADD = {
    "users": [
        ("assigned_specialist_id", "INTEGER", "NULL"),
    ],
    "user_operation_confirmations": [
        ("source",           "VARCHAR(30)",  "'web'"),
        ("execution_status", "VARCHAR(20)",  "'pending'"),
        ("expires_at",       "DATETIME",     "NULL"),
    ],
}

# ===== 初始服务商数据（仅在表为空时写入） =====
SEED_REGISTRARS = [
    {"name": "Cloudflare", "code": "cloudflare",
     "description": "Cloudflare Registrar，提供低成本域名注册", "is_enabled": True},
    {"name": "GoDaddy", "code": "godaddy",
     "description": "全球最大的域名注册商", "is_enabled": True},
    {"name": "Namecheap", "code": "namecheap",
     "description": "提供低成本域名注册", "is_enabled": True},
    {"name": "Enom", "code": "enom",
     "description": "专业的域名注册商", "is_enabled": True},
]
SEED_DNS_PROVIDERS = [
    {"name": "Cloudflare DNS", "code": "cloudflare",
     "description": "Cloudflare DNS，提供免费和付费DNS解析", "is_enabled": True},
    {"name": "DNSPod", "code": "dnspod",
     "description": "DNSPod (腾讯云)，国内主流DNS解析服务", "is_enabled": True},
]


def get_existing_columns(conn, table_name: str) -> set:
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result.fetchall()}


def migrate():
    print("=" * 60)
    print("域名管家 - 数据库迁移")
    print("=" * 60)

    with engine.connect() as conn:
        # 1. 创建新表（幂等）
        print("\n[1] 创建/验证数据表...")
        Base.metadata.create_all(bind=engine)
        print("    ✓ 数据表就绪")

        # 2. 补缺失列
        print("\n[2] 补充缺失列...")
        for table, cols in COLUMNS_TO_ADD.items():
            existing = get_existing_columns(conn, table)
            for col_name, col_type, default in cols:
                if col_name not in existing:
                    ddl = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                    conn.execute(text(ddl))
                    conn.commit()
                    print(f"    ✓ {table}.{col_name} 已添加")
                else:
                    print(f"    - {table}.{col_name} 已存在，跳过")

    # 3. 种入初始服务商数据
    print("\n[3] 种入初始服务商数据...")
    db = SessionLocal()
    try:
        if db.query(Registrar).count() == 0:
            for data in SEED_REGISTRARS:
                db.add(Registrar(**data))
            db.commit()
            print(f"    ✓ 已写入 {len(SEED_REGISTRARS)} 个注册商")
        else:
            print("    - 注册商数据已存在，跳过")

        if db.query(DnsProvider).count() == 0:
            for data in SEED_DNS_PROVIDERS:
                db.add(DnsProvider(**data))
            db.commit()
            print(f"    ✓ 已写入 {len(SEED_DNS_PROVIDERS)} 个解析商")
        else:
            print("    - 解析商数据已存在，跳过")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
