#!/usr/bin/env python3
"""
飞书应用配置管理脚本
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.feishu_app import FeishuApp


def list_apps() -> int:
    db = SessionLocal()
    try:
        apps = db.query(FeishuApp).order_by(FeishuApp.is_default.desc(), FeishuApp.id.asc()).all()
        for app in apps:
            default_mark = " default" if app.is_default else ""
            active_mark = "active" if app.is_active else "disabled"
            print(f"{app.id}\t{app.code}\t{app.name}\t{app.app_id}\t{active_mark}{default_mark}")
        return 0
    finally:
        db.close()


def add_app(args) -> int:
    app_secret = args.app_secret
    if args.app_secret_stdin:
        app_secret = sys.stdin.read().strip()
    if not app_secret:
        raise SystemExit("必须提供 App Secret")

    db = SessionLocal()
    try:
        existing = db.query(FeishuApp).filter(
            (FeishuApp.code == args.code) | (FeishuApp.app_id == args.app_id)
        ).first()
        if existing:
            raise SystemExit(f"飞书应用已存在: id={existing.id}, code={existing.code}, app_id={existing.app_id}")

        if args.default:
            db.query(FeishuApp).update({"is_default": False})

        app = FeishuApp(
            code=args.code,
            name=args.name,
            app_id=args.app_id,
            verification_token=args.verification_token or "",
            encrypt_key=args.encrypt_key or "",
            super_admin_feishu_user_id=args.super_admin_feishu_user_id or "",
            is_default=args.default,
            is_active=True,
        )
        app.set_app_secret(app_secret)
        db.add(app)
        db.commit()
        db.refresh(app)
        print(f"已添加飞书应用: id={app.id}, code={app.code}, name={app.name}")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="管理域名管家飞书应用配置")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="列出飞书应用")

    add_parser = subparsers.add_parser("add", help="新增飞书应用")
    add_parser.add_argument("--code", required=True, help="应用标识，如 sub_company_b")
    add_parser.add_argument("--name", required=True, help="展示名称")
    add_parser.add_argument("--app-id", required=True, help="飞书 App ID")
    add_parser.add_argument("--app-secret", default="", help="飞书 App Secret")
    add_parser.add_argument("--app-secret-stdin", action="store_true", help="从标准输入读取飞书 App Secret")
    add_parser.add_argument("--verification-token", default="", help="Webhook Verification Token")
    add_parser.add_argument("--encrypt-key", default="", help="Webhook Encrypt Key")
    add_parser.add_argument("--super-admin-feishu-user-id", default="", help="该应用下超管飞书 user_id")
    add_parser.add_argument("--default", action="store_true", help="设为默认飞书应用")

    args = parser.parse_args()
    if args.command == "list":
        return list_apps()
    if args.command == "add":
        return add_app(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
