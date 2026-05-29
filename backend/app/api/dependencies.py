"""
依赖注入模块
"""

from fastapi import Depends, HTTPException, status
from typing import Optional


async def get_current_user():
    """
    获取当前登录用户（待实现）
    """
    pass
