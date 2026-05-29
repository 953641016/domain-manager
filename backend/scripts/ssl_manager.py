#!/usr/bin/env python3
"""
SSL证书管理脚本
提供证书检查、续期等功能
"""
import sys
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ssl_service import ssl_service


def list_certificates():
    """列出所有证书"""
    print("=== SSL证书列表 ===")
    certs = ssl_service.list_all_certificates()

    if not certs:
        print("未找到证书")
        return

    for cert in certs:
        days = cert.get("days_remaining", "未知")
        status = "✅" if days is None or days > 30 else ("⚠️" if days > 7 else "🔴")
        print(f"{status} {cert['domain']}")
        print(f"   到期: {cert['not_after']}")
        print(f"   剩余: {days} 天")
        print(f"   签发者: {cert['issuer']}")
        print()


def check_expiring(warning_days: int = 30, critical_days: int = 7):
    """检查即将到期的证书"""
    print("=== 检查即将到期的证书 ===")
    result = ssl_service.check_and_alert_expiring_certificates(warning_days, critical_days)

    print(f"共检查 {result['total_checked']} 个证书")
    print()

    if result['warning_certs']:
        print(f"⚠️ 警告 ({warning_days} 天内到期):")
        for cert in result['warning_certs']:
            print(f"   - {cert['domain']}: 剩余 {cert['days_remaining']} 天")
        print()

    if result['critical_certs']:
        print(f"🔴 紧急 ({critical_days} 天内到期):")
        for cert in result['critical_certs']:
            print(f"   - {cert['domain']}: 剩余 {cert['days_remaining']} 天")
        print()

    if not result['warning_certs'] and not result['critical_certs']:
        print("✅ 所有证书状态良好")


def renew_certificate(domain: str, force: bool = False):
    """续期证书"""
    print(f"=== 续期证书: {domain} ===")
    success = ssl_service.renew_certificate(domain, force)

    if success:
        print("✅ 续期成功")
    else:
        print("❌ 续期失败")
        sys.exit(1)


def auto_renew(days_before: int = 3):
    """自动续期即将到期的证书"""
    print(f"=== 自动续期 {days_before} 天内到期的证书 ===")
    result = ssl_service.auto_renew_expiring_certificates(days_before)

    print(f"总数: {result['total']}")
    print(f"成功: {result['renewed']}")
    print(f"失败: {result['failed']}")

    if result['details']:
        print()
        print("详情:")
        for detail in result['details']:
            status = "✅" if detail['status'] == 'success' else "❌"
            print(f"   {status} {detail['domain']}")


def main():
    parser = argparse.ArgumentParser(
        description="SSL证书管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s list                    # 列出所有证书
  %(prog)s check                   # 检查即将到期的证书
  %(prog)s renew example.com       # 续期指定域名的证书
  %(prog)s auto-renew              # 自动续期即将到期的证书
        """
    )

    subparsers = parser.add_subparsers(title="命令", dest="command", required=True)

    # list命令
    list_parser = subparsers.add_parser("list", help="列出所有证书")

    # check命令
    check_parser = subparsers.add_parser("check", help="检查即将到期的证书")
    check_parser.add_argument("--warning", type=int, default=30, help="警告天数 (默认: 30)")
    check_parser.add_argument("--critical", type=int, default=7, help="紧急天数 (默认: 7)")

    # renew命令
    renew_parser = subparsers.add_parser("renew", help="续期指定证书")
    renew_parser.add_argument("domain", help="域名")
    renew_parser.add_argument("--force", action="store_true", help="强制续期")

    # auto-renew命令
    auto_renew_parser = subparsers.add_parser("auto-renew", help="自动续期即将到期的证书")
    auto_renew_parser.add_argument("--days", type=int, default=3, help="提前几天续期 (默认: 3)")

    args = parser.parse_args()

    if args.command == "list":
        list_certificates()
    elif args.command == "check":
        check_expiring(args.warning, args.critical)
    elif args.command == "renew":
        renew_certificate(args.domain, args.force)
    elif args.command == "auto-renew":
        auto_renew(args.days)


if __name__ == "__main__":
    main()
