"""
用户管理 API
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import (
    get_current_active_user,
    require_manage_users
)
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    RoleInfo
)
from app.services.user_service import UserService
from app.models.user import User

router = APIRouter(
    prefix="/users",
    tags=["用户管理"],
)


@router.get("", response_model=UserListResponse)
def get_users(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    role: Optional[str] = Query(None, description="角色筛选"),
    is_active: Optional[bool] = Query(None, description="是否启用筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    获取用户列表
    需要用户管理权限
    """
    service = UserService(db)
    users = service.get_users(
        skip=skip,
        limit=limit,
        role=role,
        is_active=is_active,
        search=search
    )
    total = service.get_users_count(
        role=role,
        is_active=is_active,
        search=search
    )

    return UserListResponse(total=total, items=users)


@router.get("/roles", response_model=list[RoleInfo])
def get_roles(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取所有角色信息
    需要已认证
    """
    return UserService.get_all_roles()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    获取用户详情
    需要用户管理权限
    """
    service = UserService(db)
    user = service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前登录用户信息
    """
    return current_user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    创建用户
    需要用户管理权限
    """
    service = UserService(db)
    try:
        user = service.create_user(user_in)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    更新用户
    需要用户管理权限
    """
    service = UserService(db)
    user = service.update_user(user_id, user_in)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    删除用户（软删除）
    需要用户管理权限
    """
    service = UserService(db)
    success = service.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    db: Session = Depends(get_db),
):
    """
    激活用户
    需要用户管理权限
    """
    service = UserService(db)
    user = service.activate_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user
