"""
待确认操作的定时清理任务

超管确认请求（user_operation_confirmations）若长期无人处理，会一直挂在
PENDING 状态。此任务定期把超时的请求自动取消，避免无限堆积，并通过审计留痕。
"""

import logging
from datetime import datetime, timedelta

from app.models.user_confirmation import (
    UserOperationConfirmation,
    ConfirmationStatus,
)

logger = logging.getLogger(__name__)

# 待确认超时时间（小时）：超过该时长仍未审批的请求自动取消
CONFIRMATION_TIMEOUT_HOURS = 48


def expire_pending_confirmations(db, timeout_hours: int = CONFIRMATION_TIMEOUT_HOURS) -> int:
    """
    将超时未处理的待确认请求标记为已取消。

    Args:
        db: 数据库会话
        timeout_hours: 超时小时数，默认 48 小时

    Returns:
        本次取消的记录数
    """
    # created_at 由 server_default func.now() 写入（SQLite 为 UTC 朴素时间），
    # 这里同样用 UTC 朴素时间做比较，避免时区不一致。
    cutoff = datetime.utcnow() - timedelta(hours=timeout_hours)

    stale = (
        db.query(UserOperationConfirmation)
        .filter(
            UserOperationConfirmation.status == ConfirmationStatus.PENDING,
            UserOperationConfirmation.created_at < cutoff,
        )
        .all()
    )

    if not stale:
        return 0

    for conf in stale:
        conf.status = ConfirmationStatus.CANCELLED
        conf.reject_reason = f"超过 {timeout_hours} 小时未处理，系统自动取消"

    db.commit()
    logger.info("自动取消 %d 条超时待确认请求", len(stale))
    return len(stale)
