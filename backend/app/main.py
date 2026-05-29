"""
域名管家 API 入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="域名管家 API",
    description="企业级域名管理系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from app.api.v1 import users, confirmations, feishu
app.include_router(users.router, prefix="/api/v1", tags=["用户"])
app.include_router(confirmations.router, prefix="/api/v1", tags=["用户确认"])
app.include_router(feishu.router, prefix="/api/v1", tags=["飞书集成"])


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
