"""
数据库连接配置
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 数据库连接 URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/domainmgr.db")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型
Base = declarative_base()


def get_db():
    """
    获取数据库会话依赖
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
