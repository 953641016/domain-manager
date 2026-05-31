"""
域名管家 API 入口
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭时的生命周期管理"""
    # ===== 启动时 =====
    _start_scheduler()
    yield
    # ===== 关闭时 =====
    _stop_scheduler()


def _start_scheduler():
    """启动 APScheduler 定时任务"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from app.tasks.scheduler import run_scheduled_tasks
        from app.tasks.confirmation_tasks import expire_pending_confirmations

        scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

        # 每天 09:00 检查域名到期、发到期提醒
        scheduler.add_job(
            lambda: _run_with_db(run_scheduled_tasks),
            CronTrigger(hour=9, minute=0),
            id="daily_domain_check",
            replace_existing=True,
        )

        # 每 4 小时扫描超时的待确认记录
        scheduler.add_job(
            lambda: _run_with_db(expire_pending_confirmations),
            CronTrigger(hour="*/4"),
            id="expire_confirmations",
            replace_existing=True,
        )

        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("定时任务调度器已启动")
    except Exception as e:
        logger.error("定时任务调度器启动失败: %s", e)


def _stop_scheduler():
    """关闭调度器"""
    try:
        sched = getattr(app.state, "scheduler", None)
        if sched and sched.running:
            sched.shutdown(wait=False)
            logger.info("定时任务调度器已关闭")
    except Exception:
        pass


def _run_with_db(func):
    """为定时任务提供数据库会话"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        func(db)
    except Exception as e:
        logger.error("定时任务执行失败: %s", e)
    finally:
        db.close()


app = FastAPI(
    title="域名管家 API",
    description="企业级域名管理系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 从环境变量获取允许的 CORS origins
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

# CORS配置 - 修复安全问题，不再使用 "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from app.api.v1 import auth, users, confirmations, feishu, domains, dns, requests, registrar, audit, ssl
from app.api.v1.registrar import router as providers_router
app.include_router(auth.router, prefix="/api/v1", tags=["认证"])
app.include_router(users.router, prefix="/api/v1", tags=["用户"])
app.include_router(confirmations.router, prefix="/api/v1", tags=["用户确认"])
app.include_router(feishu.router, prefix="/api/v1", tags=["飞书集成"])
app.include_router(domains.router, prefix="/api/v1", tags=["域名管理"])
app.include_router(dns.router, prefix="/api/v1", tags=["DNS解析"])
app.include_router(requests.router, prefix="/api/v1", tags=["申请管理"])
app.include_router(registrar.router, prefix="/api/v1", tags=["注册商管理（旧）"])
app.include_router(providers_router, prefix="/api/v1", tags=["服务商管理"])
app.include_router(audit.router, prefix="/api/v1", tags=["审计日志"])
app.include_router(ssl.router, prefix="/api/v1", tags=["SSL证书管理"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "域名管家 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
