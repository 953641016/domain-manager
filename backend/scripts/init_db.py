#!/usr/bin/env python3
"""
数据库初始化脚本
创建数据表并添加默认管理员用户
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.feishu_app import FeishuApp
from app.models.permission import ROLE_PERMISSIONS
from app.config import Config
from app.models.user_confirmation import UserOperationConfirmation
from app.models.domain import Domain, RegAccount, DnsAccount, Registrar, DnsProvider
from app.models.dns import DnsRecord
from app.models.audit import AuditLog
from app.models.request import Request
from app.models.system import SystemDefaults  # 确保 system_defaults 表被 create_all 创建
from sqlalchemy import text


def init_db():
    """
    初始化数据库
    """
    print("=" * 60)
    print("域名管家 - 数据库初始化")
    print("=" * 60)

    # 创建数据表
    print("\n1. 创建数据表...")
    Base.metadata.create_all(bind=engine)
    print("   ✓ 数据表创建完成")

    # 创建会话
    db = SessionLocal()

    try:
        # 初始化默认飞书应用配置
        print("\n2. 初始化飞书应用配置...")
        default_feishu_app = None
        if Config.FEISHU_APP_ID:
            default_feishu_app = db.query(FeishuApp).filter(FeishuApp.app_id == Config.FEISHU_APP_ID).first()
            if not default_feishu_app:
                default_feishu_app = FeishuApp(
                    code="default",
                    name="默认飞书应用",
                    app_id=Config.FEISHU_APP_ID,
                    verification_token=Config.FEISHU_VERIFICATION_TOKEN,
                    encrypt_key=Config.FEISHU_ENCRYPT_KEY,
                    super_admin_feishu_user_id=Config.SUPER_ADMIN_FEISHU_USER_ID,
                    is_default=True,
                    is_active=True,
                )
                if Config.FEISHU_APP_SECRET:
                    default_feishu_app.set_app_secret(Config.FEISHU_APP_SECRET)
                db.add(default_feishu_app)
                db.commit()
                db.refresh(default_feishu_app)
                print(f"   ✓ 已创建默认飞书应用: {default_feishu_app.app_id}")
            else:
                default_feishu_app.code = default_feishu_app.code or "default"
                default_feishu_app.name = default_feishu_app.name or "默认飞书应用"
                default_feishu_app.verification_token = Config.FEISHU_VERIFICATION_TOKEN
                default_feishu_app.encrypt_key = Config.FEISHU_ENCRYPT_KEY
                default_feishu_app.super_admin_feishu_user_id = Config.SUPER_ADMIN_FEISHU_USER_ID
                default_feishu_app.is_default = True
                default_feishu_app.is_active = True
                if Config.FEISHU_APP_SECRET:
                    default_feishu_app.set_app_secret(Config.FEISHU_APP_SECRET)
                db.commit()
                print(f"   - 默认飞书应用已存在并已同步配置: {default_feishu_app.app_id}")
        else:
            print("   - 未配置 FEISHU_APP_ID，跳过默认飞书应用创建")

        # 兼容旧库：users 增加 feishu_app_id，并把现有用户归属到默认应用
        user_cols = [row[1] for row in db.execute(text("PRAGMA table_info(users)")).fetchall()]
        if "feishu_app_id" not in user_cols:
            db.execute(text("ALTER TABLE users ADD COLUMN feishu_app_id INTEGER REFERENCES feishu_apps(id)"))
            db.commit()
            print("   ✓ users.feishu_app_id 列已添加")
        if default_feishu_app:
            db.execute(
                text("UPDATE users SET feishu_app_id = :app_id WHERE feishu_app_id IS NULL"),
                {"app_id": default_feishu_app.id},
            )
            db.commit()
            print("   ✓ 现有用户已归属默认飞书应用")

        db.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_users_feishu_app_id ON users(feishu_app_id)"
        ))
        try:
            db.execute(text("DROP INDEX IF EXISTS ix_users_feishu_user_id"))
            db.commit()
            print("   ✓ 已清理旧 feishu_user_id 单列索引（如存在）")
        except Exception as index_err:
            db.rollback()
            print(f"   - 旧 feishu_user_id 单列索引未能自动清理: {index_err}")
        db.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_feishu_app_user "
            "ON users(feishu_app_id, feishu_user_id) WHERE feishu_user_id IS NOT NULL"
        ))
        db.commit()

        # 检查是否已有超级管理员用户
        existing_super_admin = db.query(User).filter(User.role == "super_admin").first()

        if existing_super_admin:
            print("\n2. 超级管理员用户已存在，跳过创建")
            print(f"   - 现有飞书ID: {existing_super_admin.feishu_user_id}")
            # 如果配置了新的超级管理员ID，更新它
            if Config.SUPER_ADMIN_FEISHU_USER_ID and existing_super_admin.feishu_user_id != Config.SUPER_ADMIN_FEISHU_USER_ID:
                existing_super_admin.feishu_user_id = Config.SUPER_ADMIN_FEISHU_USER_ID
                if default_feishu_app:
                    existing_super_admin.feishu_app_id = default_feishu_app.id
                db.commit()
                print(f"   ✓ 已更新超级管理员飞书ID为: {Config.SUPER_ADMIN_FEISHU_USER_ID}")
        else:
            print("\n2. 创建默认超级管理员用户...")
            
            # 获取超级管理员权限
            super_admin_perms = ROLE_PERMISSIONS.get("super_admin", {})
            permission_list = [k for k, v in super_admin_perms.items() if isinstance(v, bool)]

            # 创建超级管理员用户
            super_admin = User(
                name="超级管理员",
                email="super_admin@company.com",
                role="super_admin",
                feishu_app_id=default_feishu_app.id if default_feishu_app else None,
                feishu_user_id=Config.SUPER_ADMIN_FEISHU_USER_ID or None,
                permissions=permission_list,
                is_active=True,
                remark="默认超级管理员账户"
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            print(f"   ✓ 超级管理员用户创建成功")
            print(f"   - ID: {super_admin.id}")
            print(f"   - 姓名: {super_admin.name}")
            print(f"   - 飞书ID: {super_admin.feishu_user_id}")
            print(f"   - 角色: {super_admin.role}")

        # 检查是否已有系统管理员
        existing_admin = db.query(User).filter(User.role == "admin").first()
        
        if not existing_admin:
            print("\n3. 创建默认系统管理员用户...")
            
            # 获取系统管理员权限
            admin_perms = ROLE_PERMISSIONS.get("admin", {})
            permission_list = [k for k, v in admin_perms.items() if isinstance(v, bool)]

            # 创建系统管理员用户
            admin = User(
                name="系统管理员",
                email="admin@company.com",
                role="admin",
                feishu_app_id=default_feishu_app.id if default_feishu_app else None,
                feishu_user_id=Config.ADMIN_USER_IDS[0] if Config.ADMIN_USER_IDS else None,
                permissions=permission_list,
                is_active=True,
                remark="默认系统管理员账户"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"   ✓ 系统管理员用户创建成功")
            print(f"   - ID: {admin.id}")
            print(f"   - 姓名: {admin.name}")
            print(f"   - 飞书ID: {admin.feishu_user_id}")
            print(f"   - 角色: {admin.role}")
        else:
            print("\n3. 系统管理员用户已存在")

        # ── system_defaults 迁移：单行全局表 → per-user 表 ──────────────────
        print("\n4. system_defaults 表迁移检查（v1.3.3: 全局→per-user）...")
        col_rows = db.execute(text("PRAGMA table_info(system_defaults)")).fetchall()
        existing_cols = [row[1] for row in col_rows]

        if "user_id" not in existing_cols:
            # 添加 user_id 列（SQLite ALTER TABLE 只支持 ADD COLUMN）
            db.execute(text(
                "ALTER TABLE system_defaults ADD COLUMN user_id INTEGER REFERENCES users(id)"
            ))
            db.commit()
            print("   ✓ 已添加 user_id 列")

            # 清理旧全局行（全部 NULL 默认值，无实际意义）
            db.execute(text("DELETE FROM system_defaults WHERE user_id IS NULL"))
            db.commit()
            print("   ✓ 已清理旧全局行")
        else:
            print("   - user_id 列已存在，跳过")

        # 创建唯一索引（SQLite 不支持 CREATE UNIQUE INDEX 在 ALTER 时附加，需单独建）
        db.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "ix_system_defaults_user_id ON system_defaults(user_id)"
        ))
        db.commit()
        print("   ✓ user_id 唯一索引已就绪")

        # 初始化注册商数据（已实现适配器的服务商）
        print("\n5. 初始化注册商与DNS服务商数据...")
        DEFAULT_REGISTRARS = [
            {"code": "cloudflare", "name": "Cloudflare", "description": "Cloudflare 域名注册（同时支持 DNS 解析）"},
            {"code": "godaddy",    "name": "GoDaddy",    "description": "GoDaddy 域名注册"},
        ]
        DEFAULT_DNS_PROVIDERS = [
            {"code": "cloudflare", "name": "Cloudflare DNS", "description": "Cloudflare DNS 解析（推荐首选）"},
        ]
        for item in DEFAULT_REGISTRARS:
            if not db.query(Registrar).filter_by(code=item["code"]).first():
                db.add(Registrar(code=item["code"], name=item["name"], description=item["description"], is_enabled=True))
                print(f"   ✓ 注册商已添加: {item['name']}")
            else:
                print(f"   - 注册商已存在: {item['name']}")
        for item in DEFAULT_DNS_PROVIDERS:
            if not db.query(DnsProvider).filter_by(code=item["code"]).first():
                db.add(DnsProvider(code=item["code"], name=item["name"], description=item["description"], is_enabled=True))
                print(f"   ✓ DNS服务商已添加: {item['name']}")
            else:
                print(f"   - DNS服务商已存在: {item['name']}")
        db.commit()

        # 显示所有角色信息
        print("\n6. 可用角色列表:")
        for role_code, role_info in ROLE_PERMISSIONS.items():
            print(f"   - {role_code}: {role_info['name']} ({role_info['description']})")

        # 显示当前用户统计
        print("\n7. 当前用户统计:")
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        print(f"   - 总用户数: {total_users}")
        print(f"   - 启用用户: {active_users}")

        for role_code in ROLE_PERMISSIONS.keys():
            count = db.query(User).filter(User.role == role_code).count()
            print(f"   - {ROLE_PERMISSIONS[role_code]['name']}: {count}")

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("数据库初始化完成!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    # 确保 data 目录存在
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)

    success = init_db()
    sys.exit(0 if success else 1)
