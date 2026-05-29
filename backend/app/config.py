import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DINGTALK_APP_KEY = os.getenv("DINGTALK_APP_KEY", "")
    DINGTALK_APP_SECRET = os.getenv("DINGTALK_APP_SECRET", "")

    CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
    CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")

    GODADDY_API_KEY = os.getenv("GODADDY_API_KEY", "")
    GODADDY_API_SECRET = os.getenv("GODADDY_API_SECRET", "")

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./domain_manager.db")

    ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")

    # 飞书配置
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
    FEISHU_VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
    FEISHU_ENCRYPT_KEY = os.getenv("FEISHU_ENCRYPT_KEY", "")

    # 前端基础URL（用于OAuth回调）
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

    @classmethod
    def is_admin(cls, user_id):
        return user_id in cls.ADMIN_USER_IDS
