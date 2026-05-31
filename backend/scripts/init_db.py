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
from app.models.permission import ROLE_PERMISSIONS
from app.config import Config
from app.models.user_confirmation import UserOperationConfirmation
from app.models.domain import Domain, RegAccount, DnsAccount, Registrar, DnsProvider
from app.models.dns import DnsRecord
from app.models.audit import AuditLog
from app.models.request import Request
from app.models.system import SystemDefaults  # 确保 system_defaults 表被 create_all 创建


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
        # 检查是否已有超级管理员用户
        existing_super_admin = db.query(User).filter(User.role == "super_admin").first()

        if existing_super_admin:
            print("\n2. 超级管理员用户已存在，跳过创建")
            print(f"   - 现有飞书ID: {existing_super_admin.feishu_user_id}")
            # 如果配置了新的超级管理员ID，更新它
            if Config.SUPER_ADMIN_FEISHU_USER_ID and existing_super_admin.feishu_user_id != Config.SUPER_ADMIN_FEISHU_USER_ID:
                existing_super_admin.feishu_user_id = Config.SUPER_ADMIN_FEISHU_USER_ID
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

        # 初始化注册商数据（已实现适配器的服务商）
        print("\n4. 初始化注册商与DNS服务商数据...")
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
        print("\n5. 可用角色列表:")
        for role_code, role_info in ROLE_PERMISSIONS.items():
            print(f"   - {role_code}: {role_info['name']} ({role_info['description']})")

        # 显示当前用户统计
        print("\n6. 当前用户统计:")
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
