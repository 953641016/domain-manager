"""
注册商工厂
根据注册商代码创建对应的适配器实例
"""
from typing import Optional
from app.adapters.base import BaseRegistrarAdapter, BaseDnsProviderAdapter
from app.adapters.cloudflare import CloudflareRegistrarAdapter, CloudflareDnsProviderAdapter
from app.adapters.dnspod import DnspodDnsProviderAdapter
from app.adapters.godaddy import GoDaddyRegistrarAdapter
from app.config import Config


class RegistrarFactory:
    """注册商工厂类"""

    # 支持的注册商
    SUPPORTED_REGISTRARS = ["cloudflare", "godaddy"]

    # 支持的DNS解析商
    SUPPORTED_DNS_PROVIDERS = ["cloudflare", "dnspod"]

    @classmethod
    def create_registrar(cls, code: str, api_key: str, api_secret: Optional[str] = None, account_id: Optional[str] = None) -> BaseRegistrarAdapter:
        """
        创建注册商适配器

        Args:
            code: 注册商代码
            api_key: API Key
            api_secret: API Secret
            account_id: 账号ID（Cloudflare需要）

        Returns:
            注册商适配器实例
        """
        code = code.lower()

        if code == "cloudflare":
            return CloudflareRegistrarAdapter(api_key=api_key, account_id=account_id or Config.CLOUDFLARE_ACCOUNT_ID)
        elif code == "godaddy":
            if not api_secret:
                raise ValueError("GoDaddy需要提供API Secret")
            return GoDaddyRegistrarAdapter(api_key=api_key, api_secret=api_secret)
        else:
            raise ValueError(f"不支持的注册商: {code}，支持的注册商: {cls.SUPPORTED_REGISTRARS}")

    @classmethod
    def create_dns_provider(cls, code: str, api_key: str, api_secret: Optional[str] = None) -> BaseDnsProviderAdapter:
        """
        创建DNS解析商适配器

        Args:
            code: 解析商代码
            api_key: API Key
            api_secret: API Secret

        Returns:
            DNS解析商适配器实例
        """
        code = code.lower()

        if code == "cloudflare":
            return CloudflareDnsProviderAdapter(api_key=api_key)
        elif code == "dnspod":
            if not api_secret:
                raise ValueError("DNSPod需要提供SecretKey")
            return DnspodDnsProviderAdapter(api_key=api_key, api_secret=api_secret)
        else:
            raise ValueError(f"不支持的DNS解析商: {code}，支持的解析商: {cls.SUPPORTED_DNS_PROVIDERS}")

    @classmethod
    def get_registrar_info(cls, code: str) -> dict:
        """
        获取注册商信息

        Args:
            code: 注册商代码

        Returns:
            注册商信息字典
        """
        registrars = {
            "cloudflare": {
                "code": "cloudflare",
                "name": "Cloudflare",
                "description": "Cloudflare Registrar，提供低成本域名注册",
                "supports_registration": True,
                "supports_transfer": False,  # 已禁用：域名转入转出功能暂不开放，代码保留但API层未暴露
                "supports_dns": True
            },
            "godaddy": {
                "code": "godaddy",
                "name": "GoDaddy",
                "description": "GoDaddy，全球最大的域名注册商",
                "supports_registration": True,
                "supports_transfer": False,  # 已禁用：域名转入转出功能暂不开放，代码保留但API层未暴露
                "supports_dns": True
            },
        }

        return registrars.get(code, None)

    @classmethod
    def get_dns_provider_info(cls, code: str) -> dict:
        """
        获取DNS解析商信息

        Args:
            code: 解析商代码

        Returns:
            解析商信息字典
        """
        providers = {
            "cloudflare": {
                "code": "cloudflare",
                "name": "Cloudflare",
                "description": "Cloudflare DNS，提供免费和付费DNS解析服务",
                "supports_anycast": True,
                "max_records": 10000
            },
            "dnspod": {
                "code": "dnspod",
                "name": "DNSPod",
                "description": "DNSPod (腾讯云)，国内主流DNS解析服务",
                "supports_anycast": False,
                "max_records": 10000
            }
        }

        return providers.get(code, None)


class DnsProviderFactory:
    """DNS解析商工厂"""

    @classmethod
    def create(cls, code: str, api_key: str, api_secret: Optional[str] = None) -> BaseDnsProviderAdapter:
        """
        创建DNS解析商适配器

        Args:
            code: 解析商代码
            api_key: API Key
            api_secret: API Secret

        Returns:
            DNS解析商适配器实例
        """
        return RegistrarFactory.create_dns_provider(code, api_key, api_secret)
