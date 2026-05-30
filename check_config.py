import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

from app.config import Config

print("=== DNSPod 配置检查 ===")
print(f"DNSPOD_SECRET_ID: {Config.DNSPOD_SECRET_ID}")
print(f"DNSPOD_SECRET_KEY: {'*' * (len(Config.DNSPOD_SECRET_KEY) if Config.DNSPOD_SECRET_KEY else 0)}")

if Config.DNSPOD_SECRET_ID and Config.DNSPOD_SECRET_KEY:
    print("\n✅ 配置读取成功")
else:
    print("\n❌ 配置缺失")

print("\n=== 测试适配器 ===")
try:
    from app.adapters.registrar_factory import RegistrarFactory
    from app.adapters.dnspod import DnspodDnsProviderAdapter

    adapter = DnspodDnsProviderAdapter(
        api_key=Config.DNSPOD_SECRET_ID,
        api_secret=Config.DNSPOD_SECRET_KEY,
    )
    print("✅ 适配器创建成功")

    print("\n测试读取 fwxg.com 的记录...")
    records = adapter.get_records("fwxg.com")
    print(f"✅ 读取成功，共 {len(records)} 条记录")

    print(f"\n示例记录:")
    for rec in records[:3]:
        print(f"  {rec.get('host', '@'):>10}  {rec.get('type'):>6}  {rec.get('value')}")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    print(f"\n堆栈: {traceback.format_exc()}")
