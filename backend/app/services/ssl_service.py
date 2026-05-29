"""
SSL证书管理服务
提供SSL证书监控、到期提醒和自动续期功能
"""
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SSLService:
    """SSL证书服务类"""

    def __init__(self, certbot_path: str = "certbot"):
        self.certbot_path = certbot_path
        self.certs_dir = Path("/etc/letsencrypt/live")
        self.archive_dir = Path("/etc/letsencrypt/archive")

    def get_certificate_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        获取SSL证书信息

        Args:
            domain: 域名

        Returns:
            证书信息字典，包含到期日期、签发者等
        """
        cert_path = self.certs_dir / domain / "fullchain.pem"

        if not cert_path.exists():
            logger.warning(f"证书文件不存在: {cert_path}")
            return None

        try:
            # 使用OpenSSL获取证书信息
            cmd = [
                "openssl", "x509",
                "-in", str(cert_path),
                "-text",
                "-noout"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"获取证书信息失败: {result.stderr}")
                return None

            # 解析证书信息
            cert_info = self._parse_openssl_output(result.stdout, domain)

            return cert_info

        except Exception as e:
            logger.error(f"获取证书信息异常: {str(e)}")
            return None

    def _parse_openssl_output(self, output: str, domain: str) -> Dict[str, Any]:
        """
        解析OpenSSL输出

        Args:
            output: OpenSSL命令输出
            domain: 域名

        Returns:
            解析后的证书信息
        """
        cert_info = {
            "domain": domain,
            "not_before": None,
            "not_after": None,
            "issuer": None,
            "subject": None,
            "sans": [],
            "days_remaining": None
        }

        # 解析Not Before
        if "Not Before:" in output:
            idx = output.find("Not Before:")
            end_idx = output.find("\n", idx)
            if end_idx != -1:
                date_str = output[idx + len("Not Before:"):end_idx].strip()
                try:
                    cert_info["not_before"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y GMT")
                except ValueError:
                    pass

        # 解析Not After
        if "Not After :" in output:
            idx = output.find("Not After :")
            end_idx = output.find("\n", idx)
            if end_idx != -1:
                date_str = output[idx + len("Not After :"):end_idx].strip()
                try:
                    cert_info["not_after"] = datetime.strptime(date_str, "%b %d %H:%M:%S %Y GMT")
                    # 计算剩余天数
                    if cert_info["not_after"]:
                        delta = cert_info["not_after"] - datetime.now()
                        cert_info["days_remaining"] = delta.days
                except ValueError:
                    pass

        # 解析Issuer
        if "Issuer:" in output:
            idx = output.find("Issuer:")
            end_idx = output.find("\n", idx)
            if end_idx != -1:
                cert_info["issuer"] = output[idx + len("Issuer:"):end_idx].strip()

        # 解析Subject
        if "Subject:" in output:
            idx = output.find("Subject:")
            end_idx = output.find("\n", idx)
            if end_idx != -1:
                cert_info["subject"] = output[idx + len("Subject:"):end_idx].strip()

        return cert_info

    def list_all_certificates(self) -> List[Dict[str, Any]]:
        """
        列出所有SSL证书

        Returns:
            证书信息列表
        """
        certificates = []

        if not self.certs_dir.exists():
            logger.warning(f"证书目录不存在: {self.certs_dir}")
            return certificates

        # 遍历live目录下的所有域名
        for domain_dir in self.certs_dir.iterdir():
            if domain_dir.is_dir() and (domain_dir / "fullchain.pem").exists():
                domain = domain_dir.name
                cert_info = self.get_certificate_info(domain)
                if cert_info:
                    certificates.append(cert_info)

        return certificates

    def get_expiring_certificates(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取即将到期的证书

        Args:
            days: 到期天数阈值

        Returns:
            即将到期的证书列表
        """
        expiring_certs = []

        certificates = self.list_all_certificates()

        for cert in certificates:
            days_remaining = cert.get("days_remaining")
            if days_remaining is not None and days_remaining <= days:
                expiring_certs.append(cert)
                logger.warning(f"证书即将到期: {cert['domain']}, 剩余 {days_remaining} 天")

        return expiring_certs

    def renew_certificate(self, domain: str, force: bool = False) -> bool:
        """
        续期SSL证书

        Args:
            domain: 域名
            force: 是否强制续期

        Returns:
            是否续期成功
        """
        try:
            cmd = [self.certbot_path, "renew"]

            if force:
                cmd.append("--force-renewal")

            # 只续期指定域名
            cmd.extend(["--cert-name", domain])

            # 非交互式
            cmd.append("--non-interactive")

            logger.info(f"开始续期证书: {domain}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"续期证书失败: {result.stderr}")
                return False

            logger.info(f"证书续期成功: {domain}")
            return True

        except Exception as e:
            logger.error(f"续期证书异常: {str(e)}")
            return False

    def auto_renew_expiring_certificates(self, days_before: int = 3) -> Dict[str, Any]:
        """
        自动续期即将到期的证书

        Args:
            days_before: 提前几天续期

        Returns:
            续期结果
        """
        result = {
            "total": 0,
            "renewed": 0,
            "failed": 0,
            "details": []
        }

        # 获取即将到期的证书
        expiring_certs = self.get_expiring_certificates(days_before)
        result["total"] = len(expiring_certs)

        for cert in expiring_certs:
            domain = cert["domain"]
            success = self.renew_certificate(domain)

            if success:
                result["renewed"] += 1
                result["details"].append({
                    "domain": domain,
                    "status": "success"
                })
            else:
                result["failed"] += 1
                result["details"].append({
                    "domain": domain,
                    "status": "failed"
                })

        return result

    def check_and_alert_expiring_certificates(self, warning_days: int = 30, critical_days: int = 7) -> Dict[str, Any]:
        """
        检查并提醒即将到期的证书

        Args:
            warning_days: 警告天数阈值
            critical_days: 紧急天数阈值

        Returns:
            检查结果
        """
        result = {
            "warning_certs": [],
            "critical_certs": [],
            "total_checked": 0
        }

        certificates = self.list_all_certificates()
        result["total_checked"] = len(certificates)

        for cert in certificates:
            days_remaining = cert.get("days_remaining")

            if days_remaining is None:
                continue

            if days_remaining <= critical_days:
                result["critical_certs"].append(cert)
            elif days_remaining <= warning_days:
                result["warning_certs"].append(cert)

        return result


# 单例实例
ssl_service = SSLService()
