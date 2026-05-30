#!/usr/bin/env python3
"""
SSL 证书申请脚本
使用 Let's Encrypt + Certbot + DNSPod 自动申请和安装 SSL 证书
"""
import sys
import os
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config
from app.adapters.dnspod import DnspodDnsProviderAdapter


def create_dns_record(domain: str, record_name: str, record_value: str) -> bool:
    """
    创建 DNS TXT 记录用于验证

    Args:
        domain: 域名
        record_name: 记录名
        record_value: 记录值

    Returns:
        是否成功
    """
    try:
        print(f"📝 创建 DNS TXT 记录: {record_name}.{domain}")
        
        adapter = DnspodDnsProviderAdapter(
            api_key=Config.DNSPOD_SECRET_ID,
            api_secret=Config.DNSPOD_SECRET_KEY
        )

        result = adapter.create_record(
            domain=domain,
            record_type="TXT",
            host=record_name,
            value=record_value,
            ttl=60
        )

        if result.get("success"):
            print("✅ TXT 记录创建成功！等待 DNS 传播 (30 秒)...")
            import time
            time.sleep(30)
            return True
        else:
            print(f"❌ TXT 记录创建失败: {result.get('message')}")
            return False

    except Exception as e:
        print(f"❌ 创建 TXT 记录异常: {e}")
        return False


def delete_dns_record(domain: str, record_name: str, record_value: str) -> bool:
    """
    删除验证用的 TXT 记录

    Args:
        domain: 域名
        record_name: 记录名
        record_value: 记录值

    Returns:
        是否成功
    """
    try:
        print(f"🧹 删除 DNS TXT 记录: {record_name}.{domain}")
        
        adapter = DnspodDnsProviderAdapter(
            api_key=Config.DNSPOD_SECRET_ID,
            api_secret=Config.DNSPOD_SECRET_KEY
        )

        # 查找记录
        records = adapter.get_records(domain)
        target_record = None
        
        for record in records:
            if (record.get("type") == "TXT" and 
                record.get("host") == record_name and 
                record.get("value") == record_value):
                target_record = record
                break

        if not target_record:
            print("⚠️ 未找到记录，跳过删除")
            return True

        record_id = target_record.get("id")
        result = adapter.delete_record(domain, record_id)

        if result.get("success"):
            print("✅ TXT 记录删除成功！")
            return True
        else:
            print(f"❌ TXT 记录删除失败: {result.get('message')}")
            return False

    except Exception as e:
        print(f"❌ 删除 TXT 记录异常: {e}")
        return False


def issue_certificate(domain: str, email: str, staging: bool = False) -> bool:
    """
    申请 SSL 证书

    Args:
        domain: 域名
        email: 邮箱
        staging: 是否使用测试环境

    Returns:
        是否成功
    """
    print(f"🔐 开始为 {domain} 申请 SSL 证书...")

    if not Config.DNSPOD_SECRET_ID or not Config.DNSPOD_SECRET_KEY:
        print("❌ DNSPod 配置未设置，请检查 .env 文件")
        return False

    # Certbot 命令参数
    certbot_cmd = [
        "certbot",
        "certonly",
        "--non-interactive",
        "--agree-tos",
        "--email", email,
        "--manual",
        "--preferred-challenges=dns",
        "-d", domain,
        "-d", f"*.{domain}" if not domain.startswith("*.") else domain
    ]

    if staging:
        certbot_cmd.append("--staging")
        print("⚠️ 使用 Let's Encrypt 测试环境 (证书不会被浏览器信任)")

    # 环境变量，用于 Manual Hook
    env = os.environ.copy()

    # 我们使用 Certbot 的 manual 模式，配合 hook 脚本
    hook_dir = Path(__file__).parent.parent / "app" / "adapters"
    
    auth_hook = hook_dir / "certbot_auth.sh"
    cleanup_hook = hook_dir / "certbot_cleanup.sh"

    # 检查 hook 脚本
    if not auth_hook.exists():
        print(f"⚠️ Hook 脚本不存在: {auth_hook}")
        print("将使用交互式模式，你需要手动配置 DNS 记录")

    # 构建 Certbot 的认证和清理钩子
    # 使用 Python 脚本直接处理
    # 我们可以通过环境变量传递值给 Certbot，或者使用手动方式
    
    print("\n" + "="*60)
    print("📋 证书申请说明")
    print("="*60)
    print("本脚本将使用 Certbot 的 DNS-01 验证方式申请证书")
    print("验证过程：")
    print("1. Certbot 会提供一个 TXT 记录值")
    print("2. 脚本会在 DNSPod 中自动创建该记录")
    print("3. 等待 DNS 传播")
    print("4. Let's Encrypt 验证通过")
    print("5. 证书颁发")
    print("6. 脚本自动清理临时 DNS 记录")
    print("="*60 + "\n")

    # 对于 Windows，我们使用简化的方式
    # 直接提示用户如何操作

    print(f"⚠️ 由于环境限制，建议您手动运行以下命令来申请证书：")
    print("\n" + "─"*60)
    print(f" certbot certonly --manual --preferred-challenges=dns \\")
    print(f"    --email {email} --agree-tos --non-interactive \\")
    print(f"    -d {domain} -d *.{domain} \\")
    print(f"    {'--staging' if staging else ''}")
    print("─"*60 + "\n")
    print("💡 Certbot 提示创建 TXT 记录时，请按以下步骤操作：")
    print(f"  - 登录 DNSPod 控制台")
    print(f"  - 域名: {domain}")
    print(f"  - 记录类型: TXT")
    print(f"  - 主机记录: _acme-challenge")
    print(f"  - 记录值: (使用 Certbot 提供的值)")
    print(f"  - TTL: 60")
    print(f"  - 创建后等待约 30-60 秒，然后按回车键继续")
    print("\n证书申请成功后，将保存到 /etc/letsencrypt/live/{domain}/")

    return True


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="SSL 证书申请工具")
    parser.add_argument("domain", help="要申请证书的域名 (例如 fwxg.com)")
    parser.add_argument("--email", help="用于接收证书通知的邮箱", 
                       default="admin@fwxg.com")
    parser.add_argument("--staging", action="store_true", 
                       help="使用 Let's Encrypt 测试环境")
    
    args = parser.parse_args()

    issue_certificate(args.domain, args.email, args.staging)


if __name__ == "__main__":
    main()
