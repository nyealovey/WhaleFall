"""
自动分类批次服务
管理自动分类操作的批次信息
"""

import uuid
from typing import Any

from app import db
from app.models.classification_batch import ClassificationBatch
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils


class ClassificationBatchService:
    """自动分类批次服务"""

    @staticmethod
    def create_batch(
        batch_type: str,
        created_by: int | None = None,
        total_rules: int = 0,
        active_rules: int = 0,
    ) -> str:
        """
        创建新的分类批次

        Args:
            batch_type: 批次类型 (manual, scheduled, api)
            created_by: 创建者用户ID
            total_rules: 总规则数
            active_rules: 活跃规则数

        Returns:
            str: 批次ID
        """
        try:
            batch_id = str(uuid.uuid4())

            batch = ClassificationBatch(
                batch_id=batch_id,
                batch_type=batch_type,
                status="running",
                total_rules=total_rules,
                active_rules=active_rules,
                created_by=created_by,
            )

            db.session.add(batch)
            db.session.commit()

            log_info(
                "创建自动分类批次",
                module="classification_batch",
                batch_id=batch_id,
                batch_type=batch_type,
                total_rules=total_rules,
                active_rules=active_rules,
                created_by=created_by,
            )

            return batch_id

        except Exception as e:
            db.session.rollback()
            log_error(
                "创建自动分类批次失败",
                module="classification_batch",
                batch_type=batch_type,
                error=str(e),
            )
            raise

    @staticmethod
    def update_batch_stats(
        batch_id: str,
        total_accounts: int = 0,
        matched_accounts: int = 0,
        failed_accounts: int = 0,
    ) -> bool:
        """
        更新批次统计信息

        Args:
            batch_id: 批次ID
            total_accounts: 总账户数
            matched_accounts: 匹配账户数
            failed_accounts: 失败账户数

        Returns:
            bool: 是否更新成功
        """
        try:
            batch = ClassificationBatch.query.filter_by(batch_id=batch_id).first()
            if not batch:
                log_warning("批次不存在", module="classification_batch", batch_id=batch_id)
                return False

            batch.total_accounts = total_accounts
            batch.matched_accounts = matched_accounts
            batch.failed_accounts = failed_accounts

            db.session.commit()

            log_info(
                "更新批次统计信息",
                module="classification_batch",
                batch_id=batch_id,
                total_accounts=total_accounts,
                matched_accounts=matched_accounts,
                failed_accounts=failed_accounts,
            )

            return True

        except Exception as e:
            db.session.rollback()
            log_error(
                "更新批次统计信息失败",
                module="classification_batch",
                batch_id=batch_id,
                error=str(e),
            )
            return False

    @staticmethod
    def complete_batch(
        batch_id: str,
        status: str = "completed",
        error_message: str | None = None,
        batch_details: dict[str, Any] | None = None,
    ) -> bool:
        """
        完成批次

        Args:
            batch_id: 批次ID
            status: 完成状态 (completed, failed)
            error_message: 错误信息
            batch_details: 批次详情

        Returns:
            bool: 是否完成成功
        """
        try:
            batch = ClassificationBatch.query.filter_by(batch_id=batch_id).first()
            if not batch:
                log_warning("批次不存在", module="classification_batch", batch_id=batch_id)
                return False

            batch.status = status
            batch.completed_at = time_utils.now()
            batch.error_message = error_message

            if batch_details:
                import json

                batch.batch_details = json.dumps(batch_details, ensure_ascii=False)

            db.session.commit()

            log_info(
                "完成自动分类批次",
                module="classification_batch",
                batch_id=batch_id,
                status=status,
                duration=batch.duration,
                success_rate=batch.success_rate,
                error_message=error_message,
            )

            return True

        except Exception as e:
            db.session.rollback()
            log_error(
                "完成批次失败",
                module="classification_batch",
                batch_id=batch_id,
                error=str(e),
            )
            return False

    @staticmethod
    def get_batch(batch_id: str) -> ClassificationBatch | None:
        """
        获取批次信息

        Args:
            batch_id: 批次ID

        Returns:
            ClassificationBatch: 批次对象
        """
        try:
            return ClassificationBatch.query.filter_by(batch_id=batch_id).first()
        except Exception as e:
            log_error(
                "获取批次信息失败",
                module="classification_batch",
                batch_id=batch_id,
                error=str(e),
            )
            return None

    @staticmethod
    def get_batches(
        batch_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """
        获取批次列表

        Args:
            batch_type: 批次类型过滤
            status: 状态过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            list: 批次列表
        """
        try:
            query = ClassificationBatch.query

            if batch_type:
                query = query.filter(ClassificationBatch.batch_type == batch_type)

            if status:
                query = query.filter(ClassificationBatch.status == status)

            return query.order_by(ClassificationBatch.started_at.desc()).offset(offset).limit(limit).all()

        except Exception as e:
            log_error(
                "获取批次列表失败",
                module="classification_batch",
                batch_type=batch_type,
                status=status,
                error=str(e),
            )
            return []

    @staticmethod
    def get_batch_stats(batch_id: str) -> dict[str, Any] | None:
        """
        获取批次统计信息

        Args:
            batch_id: 批次ID

        Returns:
            Dict: 统计信息
        """
        try:
            batch = ClassificationBatch.query.filter_by(batch_id=batch_id).first()
            if not batch:
                return None

            return {
                "batch_id": batch.batch_id,
                "batch_type": batch.batch_type,
                "status": batch.status,
                "duration": batch.duration,
                "success_rate": batch.success_rate,
                "total_accounts": batch.total_accounts,
                "matched_accounts": batch.matched_accounts,
                "failed_accounts": batch.failed_accounts,
                "total_rules": batch.total_rules,
                "active_rules": batch.active_rules,
                "started_at": (batch.started_at.isoformat() if batch.started_at else None),
                "completed_at": (batch.completed_at.isoformat() if batch.completed_at else None),
            }

        except Exception as e:
            log_error(
                "获取批次统计信息失败",
                module="classification_batch",
                batch_id=batch_id,
                error=str(e),
            )
            return None
