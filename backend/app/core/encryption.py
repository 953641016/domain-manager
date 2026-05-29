"""
数据加密服务 - 用于加密存储 API Key 等敏感数据
"""
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.config import Config


class EncryptionService:
    """加密服务"""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化加密服务

        Args:
            encryption_key: Fernet 加密密钥，如果不提供则从配置中读取
        """
        key = encryption_key or Config.ENCRYPTION_KEY
        if not key:
            raise ValueError("ENCRYPTION_KEY 必须配置")
        self.fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        """
        加密文本

        Args:
            plaintext: 明文

        Returns:
            加密后的密文
        """
        if not plaintext:
            return ""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        解密文本

        Args:
            ciphertext: 密文

        Returns:
            解密后的明文
        """
        if not ciphertext:
            return ""
        try:
            return self.fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise ValueError("无效的加密数据或密钥不正确")


# 全局加密服务实例
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """获取加密服务单例"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
