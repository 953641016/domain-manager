"""
域名管家 API 入口
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="域名管家 API",
    description="企业级域名管理系统",
    version="1.0.0"
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
from app.api.v1 import auth, users, confirmations, feishu, domains, dns, requests, registrar, audit
app.include_router(auth.router, prefix="/api/v1", tags=["认证"])
app.include_router(users.router, prefix="/api/v1", tags=["用户"])
app.include_router(confirmations.router, prefix="/api/v1", tags=["用户确认"])
app.include_router(feishu.router, prefix="/api/v1", tags=["飞书集成"])
app.include_router(domains.router, prefix="/api/v1", tags=["域名管理"])
app.include_router(dns.router, prefix="/api/v1", tags=["DNS解析"])
app.include_router(requests.router, prefix="/api/v1", tags=["申请管理"])
app.include_router(registrar.router, prefix="/api/v1", tags=["注册商管理"])
app.include_router(audit.router, prefix="/api/v1", tags=["审计日志"])


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
