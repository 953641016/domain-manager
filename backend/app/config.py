import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --------------------------------------------------------------------------
    # 域名和 CORS 配置
    # --------------------------------------------------------------------------
    FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN", "localhost")
    BACKEND_DOMAIN = os.getenv("BACKEND_DOMAIN", "localhost")
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

    # --------------------------------------------------------------------------
    # JWT 认证配置
    # --------------------------------------------------------------------------
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-please-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # --------------------------------------------------------------------------
    # 数据加密配置
    # --------------------------------------------------------------------------
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

    # --------------------------------------------------------------------------
    # 钉钉机器人配置
    # --------------------------------------------------------------------------
    DINGTALK_APP_KEY = os.getenv("DINGTALK_APP_KEY", "")
    DINGTALK_APP_SECRET = os.getenv("DINGTALK_APP_SECRET", "")

    # --------------------------------------------------------------------------
    # 飞书应用配置
    # --------------------------------------------------------------------------
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
    FEISHU_VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
    FEISHU_ENCRYPT_KEY = os.getenv("FEISHU_ENCRYPT_KEY", "")
    SUPER_ADMIN_FEISHU_USER_ID = os.getenv("SUPER_ADMIN_FEISHU_USER_ID", "")
    BACKEND_DNS_DEFAULT_TARGET = os.getenv("BACKEND_DNS_DEFAULT_TARGET", "54.89.199.228")
    BACKEND_DNS_DEFAULT_HOSTNAME = os.getenv("BACKEND_DNS_DEFAULT_HOSTNAME", "svc")
    BACKEND_DNS_JINAN_HOSTNAME = os.getenv("BACKEND_DNS_JINAN_HOSTNAME", "art")
    BACKEND_DNS_JINAN_TARGET = os.getenv("BACKEND_DNS_JINAN_TARGET", "20.9.240.31")
    BACKEND_DNS_JINAN_APPLICANT_MATCHERS = [
        item.strip()
        for item in os.getenv("BACKEND_DNS_JINAN_APPLICANT_MATCHERS", "\u6d4e\u5357").split(",")
        if item.strip()
    ]

    # --------------------------------------------------------------------------
    # Cloudflare 配置
    # --------------------------------------------------------------------------
    CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
    CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")

    # --------------------------------------------------------------------------
    # GoDaddy 配置
    # --------------------------------------------------------------------------
    GODADDY_API_KEY = os.getenv("GODADDY_API_KEY", "")
    GODADDY_API_SECRET = os.getenv("GODADDY_API_SECRET", "")

    # --------------------------------------------------------------------------
    # DNSPod (腾讯云) 配置
    # --------------------------------------------------------------------------
    DNSPOD_SECRET_ID = os.getenv("DNSPOD_SECRET_ID", "")
    DNSPOD_SECRET_KEY = os.getenv("DNSPOD_SECRET_KEY", "")

    # --------------------------------------------------------------------------
    # 数据库配置
    # --------------------------------------------------------------------------
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/domain_manager.db")

    # --------------------------------------------------------------------------
    # 管理员配置
    # --------------------------------------------------------------------------
    ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")

    # --------------------------------------------------------------------------
    # Site deployment integration
    # --------------------------------------------------------------------------
    SITE_DEPLOY_API_URL = os.getenv("SITE_DEPLOY_API_URL", "http://3.238.24.187/deploy-nginx-site")
    SITE_DEPLOY_API_TOKEN = os.getenv("SITE_DEPLOY_API_TOKEN", "")
    SITE_DEPLOY_TIMEOUT_SECONDS = int(os.getenv("SITE_DEPLOY_TIMEOUT_SECONDS", "900"))
    SITE_DEPLOY_POLL_INTERVAL_SECONDS = float(os.getenv("SITE_DEPLOY_POLL_INTERVAL_SECONDS", "3"))

    SITE_POST_DEPLOY_API_URL = os.getenv(
        "SITE_POST_DEPLOY_API_URL",
        "https://manage.xwbc.com/api/autoSite/createAutoSite",
    )
    SITE_POST_DEPLOY_API_TOKEN = os.getenv("SITE_POST_DEPLOY_API_TOKEN", "")
    SITE_POST_DEPLOY_API_TOKEN_HEADER = os.getenv("SITE_POST_DEPLOY_API_TOKEN_HEADER", "x-token")

    # --------------------------------------------------------------------------
    # 日志配置
    # --------------------------------------------------------------------------
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "./logs/app.log")

    @classmethod
    def is_admin(cls, user_id):
        return user_id in cls.ADMIN_USER_IDS
