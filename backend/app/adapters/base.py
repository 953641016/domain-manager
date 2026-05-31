"""
注册商适配器基类
定义统一的接口规范
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class BaseRegistrarAdapter(ABC):
    """注册商适配器基类"""

    def __init__(self, api_key: str, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret

    @abstractmethod
    def check_domain_availability(self, domain: str) -> Dict[str, Any]:
        """
        检查域名是否可注册

        Args:
            domain: 域名名称

        Returns:
            {
                "available": bool,
                "domain": str,
                "price": float,
                "currency": str,
                "message": str
            }
        """
        pass

    @abstractmethod
    def register_domain(self, domain: str, registrant_info: Dict[str, Any], nameservers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        注册域名

        Args:
            domain: 域名名称
            registrant_info: 注册人信息
            nameservers: NS服务器列表

        Returns:
            {
                "success": bool,
                "domain": str,
                "order_id": str,
                "registration_date": str,
                "expiration_date": str,
                "message": str
            }
        """
        pass

    @abstractmethod
    def renew_domain(self, domain: str, years: int = 1) -> Dict[str, Any]:
        """
        续费域名

        Args:
            domain: 域名名称
            years: 续费年数

        Returns:
            {
                "success": bool,
                "domain": str,
                "expiration_date": str,
                "message": str
            }
        """
        pass

    @abstractmethod
    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """
        获取域名信息

        Args:
            domain: 域名名称

        Returns:
            {
                "domain": str,
                "status": str,
                "registration_date": str,
                "expiration_date": str,
                "nameservers": List[str],
                "contacts": Dict[str, Any]
            }
        """
        pass

    @abstractmethod
    def update_nameservers(self, domain: str, nameservers: List[str]) -> Dict[str, Any]:
        """
        更新域名NS服务器

        Args:
            domain: 域名名称
            nameservers: 新的NS服务器列表

        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        pass

    @abstractmethod
    def transfer_domain(self, domain: str, auth_code: str) -> Dict[str, Any]:
        """
        转入域名

        ⚠️ 已禁用：域名转入功能暂不开放
        如需启用，需：
        1. 在 permission.py 中添加 can_transfer 权限
        2. 在 API 层暴露 transfer 接口
        3. 添加审批流程控制

        Args:
            domain: 域名名称
            auth_code: 转移授权码

        Returns:
            {
                "success": bool,
                "domain": str,
                "message": str
            }
        """
        pass

    def get_transfer_code(self, domain: str) -> Dict[str, Any]:
        """
        获取域名转移授权码

        ⚠️ 已禁用：域名转出功能暂不开放
        该功能用于将域名从当前注册商转出，涉及域名安全风险
        如需启用，需额外安全评估和审批流程

        Args:
            domain: 域名名称

        Returns:
            {
                "success": bool,
                "auth_code": str,
                "message": str
            }
        """
        return {
            "success": False,
            "message": "该注册商不支持获取转移码"
        }


class BaseDnsProviderAdapter(ABC):
    """DNS解析商适配器基类"""

    def __init__(self, api_key: str, api_secret: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret

    @abstractmethod
    def get_zone_id(self, domain: str) -> Optional[str]:
        """
        获取域名的Zone ID

        Args:
            domain: 域名名称

        Returns:
            Zone ID，如果不存在则返回None
        """
        pass

    @abstractmethod
    def get_records(self, domain: str) -> List[Dict[str, Any]]:
        """
        获取域名的所有DNS记录

        Args:
            domain: 域名名称

        Returns:
            [
                {
                    "id": str,
                    "type": str,
                    "host": str,
                    "value": str,
                    "ttl": int,
                    "priority": int
                }
            ]
        """
        pass

    @abstractmethod
    def create_record(self, domain: str, record_type: str, host: str, value: str, ttl: int = 300, priority: Optional[int] = None) -> Dict[str, Any]:
        """
        创建DNS记录

        Args:
            domain: 域名名称
            record_type: 记录类型
            host: 主机记录
            value: 记录值
            ttl: TTL
            priority: 优先级

        Returns:
            {
                "success": bool,
                "record_id": str,
                "message": str
            }
        """
        pass

    @abstractmethod
    def update_record(self, domain: str, record_id: str, record_type: str, host: str, value: str, ttl: int = 300, priority: Optional[int] = None) -> Dict[str, Any]:
        """
        更新DNS记录

        Args:
            domain: 域名名称
            record_id: 记录ID
            record_type: 记录类型
            host: 主机记录
            value: 记录值
            ttl: TTL
            priority: 优先级

        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        pass

    @abstractmethod
    def delete_record(self, domain: str, record_id: str) -> Dict[str, Any]:
        """
        删除DNS记录

        Args:
            domain: 域名名称
            record_id: 记录ID

        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        pass
