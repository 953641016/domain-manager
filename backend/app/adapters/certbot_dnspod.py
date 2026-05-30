#!/usr/bin/env python3
"""
Certbot DNS-01 验证的 DNSPod Hook 脚本
用于 Let's Encrypt 证书申请时的 TXT 记录管理
"""
import sys
import os
import json
import time
from typing import Dict, Any
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import Config
from app.adapters.dnspod import DnspodDnsProviderAdapter


def create_txt_record(domain: str, record_name: str, record_value: str) -> Dict[str, Any]:
    """
    创建 TXT 记录用于 DNS-01 验证

    Args:
        domain: 域名 (例如 example.com)
        record_name: TXT 记录名 (例如 _acme-challenge)
        record_value: TXT 记录值 (Let's Encrypt 验证值)

    Returns:
        操作结果
    """
    try:
        adapter = DnspodDnsProviderAdapter(
            api_key=Config.DNSPOD_SECRET_ID,
            api_secret=Config.DNSPOD_SECRET_KEY
        )

        print(f"正在添加 TXT 记录: {record_name}.{domain} = {record_value[:50]}...")
        
        result = adapter.create_record(
            domain=domain,
            record_type="TXT",
            host=record_name,
            value=record_value,
            ttl=60
        )

        if result.get("success"):
            print(f"✅ TXT 记录创建成功，等待 DNS 传播 (30 秒)...")
            time.sleep(30)  # 给 DNS 传播一些时间
            return result
        else:
            print(f"❌ TXT 记录创建失败: {result.get('message')}")
            return result

    except Exception as e:
        print(f"❌ 创建 TXT 记录异常: {str(e)}")
        return {"success": False, "message": str(e)}


def delete_txt_record(domain: str, record_name: str, record_value: str) -> Dict[str, Any]:
    """
    删除验证使用的 TXT 记录

    Args:
        domain: 域名
        record_name: TXT 记录名
        record_value: TXT 记录值

    Returns:
        操作结果
    """
    try:
        adapter = DnspodDnsProviderAdapter(
            api_key=Config.DNSPOD_SECRET_ID,
            api_secret=Config.DNSPOD_SECRET_KEY
        )

        print(f"正在查找 TXT 记录: {record_name}.{domain}")
        
        # 先获取所有记录
        records = adapter.get_records(domain)
        
        # 找到匹配的记录
        target_record = None
        for record in records:
            if (record.get("type") == "TXT" and 
                record.get("host") == record_name and 
                record.get("value") == record_value):
                target_record = record
                break

        if not target_record:
            print(f"⚠️ 未找到要删除的 TXT 记录")
            return {"success": True, "message": "记录不存在"}

        record_id = target_record.get("id")
        print(f"正在删除 TXT 记录 (ID: {record_id})")
        
        result = adapter.delete_record(domain, record_id)
        
        if result.get("success"):
            print(f"✅ TXT 记录删除成功")
            return result
        else:
            print(f"❌ TXT 记录删除失败: {result.get('message')}")
            return result

    except Exception as e:
        print(f"❌ 删除 TXT 记录异常: {str(e)}")
        return {"success": False, "message": str(e)}


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    if len(sys.argv) < 3:
        print("使用方式:")
        print("  python certbot_dnspod.py create <domain> <record_name> <record_value>")
        print("  python certbot_dnspod.py delete <domain> <record_name> <record_value>")
        sys.exit(1)

    command = sys.argv[1]
    domain = sys.argv[2]
    record_name = sys.argv[3] if len(sys.argv) > 3 else "_acme-challenge"
    record_value = sys.argv[4] if len(sys.argv) > 4 else ""

    if command == "create":
        create_txt_record(domain, record_name, record_value)
    elif command == "delete":
        delete_txt_record(domain, record_name, record_value)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)
