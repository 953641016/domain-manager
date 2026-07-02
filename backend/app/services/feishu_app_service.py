"""
飞书应用配置服务
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.feishu_app import FeishuApp
from app.config import Config
from app.services.feishu_service import FeishuService


class FeishuAppService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_apps(self) -> List[FeishuApp]:
        return (
            self.db.query(FeishuApp)
            .filter(FeishuApp.is_active == True)
            .order_by(FeishuApp.is_default.desc(), FeishuApp.id.asc())
            .all()
        )

    def get_app(self, app_id: Optional[int] = None, app_code: Optional[str] = None) -> Optional[FeishuApp]:
        query = self.db.query(FeishuApp).filter(FeishuApp.is_active == True)
        if app_id:
            return query.filter(FeishuApp.id == app_id).first()
        if app_code:
            return query.filter(FeishuApp.code == app_code).first()
        return query.filter(FeishuApp.is_default == True).first() or query.order_by(FeishuApp.id.asc()).first()

    def get_service(self, app_id: Optional[int] = None, app_code: Optional[str] = None) -> FeishuService:
        app = self.get_app(app_id=app_id, app_code=app_code)
        if app:
            return FeishuService.from_feishu_app(app)
        return FeishuService()


def get_feishu_service_for_user(db: Session, user) -> FeishuService:
    """按用户归属飞书应用返回服务实例，兼容旧用户无归属时走默认应用。"""
    return FeishuAppService(db).get_service(app_id=getattr(user, "feishu_app_id", None))


def ensure_default_feishu_app(db: Session) -> Optional[FeishuApp]:
    """确保默认 .env 飞书应用存在，用于应用启动或旧数据迁移。"""
    if not Config.FEISHU_APP_ID:
        return None
    app = db.query(FeishuApp).filter(FeishuApp.app_id == Config.FEISHU_APP_ID).first()
    if not app:
        app = FeishuApp(
            code="default",
            name="默认飞书应用",
            app_id=Config.FEISHU_APP_ID,
            verification_token=Config.FEISHU_VERIFICATION_TOKEN,
            encrypt_key=Config.FEISHU_ENCRYPT_KEY,
            super_admin_feishu_user_id=Config.SUPER_ADMIN_FEISHU_USER_ID,
            is_default=True,
            is_active=True,
        )
        if Config.FEISHU_APP_SECRET:
            app.set_app_secret(Config.FEISHU_APP_SECRET)
        db.add(app)
    else:
        app.is_default = True
        app.is_active = True
    db.commit()
    db.refresh(app)
    return app
