"""
账户自动分类服务，将路由层与编排器解耦。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.account_classification.orchestrator import AccountClassificationService
from app.utils.structlog_config import log_error, log_info


class AutoClassifyError(Exception):
    """自动分类过程中出现业务或系统错误。

    用于标识账户自动分类过程中的异常情况。
    """


@dataclass(slots=True)
class AutoClassifyResult:
    """自动分类结果载体。

    便于在路由与服务之间传递分类结果数据。

    Attributes:
        message: 结果消息。
        classified_accounts: 已分类的账户数量。
        total_classifications_added: 添加的分类总数。
        failed_count: 失败数量。
        errors: 错误列表。
        metadata: 元数据字典。
    """

    message: str
    classified_accounts: int = 0
    total_classifications_added: int = 0
    failed_count: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """构建对外响应载体。

        Returns:
            dict[str, Any]: 仅包含前端需要展示的关键统计字段。
        """
        return {
            "classified_accounts": self.classified_accounts,
            "total_classifications_added": self.total_classifications_added,
            "failed_count": self.failed_count,
            "message": self.message,
        }


class AutoClassifyService:
    """账户自动分类服务。

    封装账户分类调度逻辑，负责参数校验、日志与错误管理。
    将路由层与编排器解耦，提供统一的分类接口。

    Attributes:
        classification_service: 账户分类编排服务实例。
    """

    def __init__(self, classification_service: AccountClassificationService | None = None) -> None:
        self.classification_service = classification_service or AccountClassificationService()

    def auto_classify(
        self,
        *,
        instance_id: Any,
        created_by: int | None,
        use_optimized: Any = True,
    ) -> AutoClassifyResult:
        """执行账户自动分类。

        Args:
            instance_id: 目标实例 ID，为空时表示全量分类。
            created_by: 触发该任务的用户 ID，可为空。
            use_optimized: 是否使用优化版分类器，接受布尔或字符串值。

        Returns:
            AutoClassifyResult: 标准化的自动分类结果载体。

        Raises:
            AutoClassifyError: 分类执行过程中出现业务或系统错误时抛出。
        """

        normalized_instance_id = self._normalize_instance_id(instance_id)
        normalized_use_optimized = self._coerce_bool(use_optimized, default=True)

        log_info(
            "auto_classify_triggered",
            module="account_classification",
            instance_id=normalized_instance_id,
            use_optimized=normalized_use_optimized,
            created_by=created_by,
        )

        try:
            raw_result = self._run_engine(
                instance_id=normalized_instance_id,
                created_by=created_by,
                use_optimized=normalized_use_optimized,
            )
        except Exception as exc:  # noqa: BLE001
            log_error(
                "auto_classify_service_failed",
                module="account_classification",
                instance_id=normalized_instance_id,
                use_optimized=normalized_use_optimized,
                exception=exc,
            )
            raise AutoClassifyError("自动分类执行失败") from exc

        if not raw_result.get("success"):
            error_message = raw_result.get("error") or raw_result.get("message") or "自动分类失败"
            log_error(
                "auto_classify_failed",
                module="account_classification",
                instance_id=normalized_instance_id,
                use_optimized=normalized_use_optimized,
                error=error_message,
            )
            raise AutoClassifyError(error_message)

        result = AutoClassifyResult(
            message=raw_result.get("message") or "自动分类成功",
            classified_accounts=self._as_int(raw_result.get("classified_accounts")),
            total_classifications_added=self._as_int(raw_result.get("total_classifications_added")),
            failed_count=self._as_int(raw_result.get("failed_count")),
            errors=self._normalize_errors(raw_result.get("errors")),
            metadata={
                "total_accounts": self._as_int(raw_result.get("total_accounts")),
                "total_rules": self._as_int(raw_result.get("total_rules")),
                "total_matches": self._as_int(raw_result.get("total_matches")),
                "db_type_results": raw_result.get("db_type_results") or {},
            },
        )

        log_info(
            "auto_classify_completed",
            module="account_classification",
            instance_id=normalized_instance_id,
            use_optimized=normalized_use_optimized,
            classified_accounts=result.classified_accounts,
            total_classifications_added=result.total_classifications_added,
            failed_count=result.failed_count,
        )
        return result

    def _run_engine(
        self,
        *,
        instance_id: int | None,
        created_by: int | None,
        use_optimized: bool,
    ) -> dict[str, Any]:
        """调度底层分类引擎。

        Args:
            instance_id: 目标实例 ID，None 表示全量。
            created_by: 触发任务的用户 ID。
            use_optimized: 是否使用优化版分类流程。

        Returns:
            dict[str, Any]: 编排器返回的原始结果字典。
        """
        # 目前仅存在优化版本，未来可在此切换不同实现。
        if use_optimized:
            return self.classification_service.auto_classify_accounts_optimized(
                instance_id=instance_id,
                created_by=created_by,
            )
        return self.classification_service.auto_classify_accounts_optimized(
            instance_id=instance_id,
            created_by=created_by,
        )

    @staticmethod
    def _as_int(value: Any) -> int:
        """安全地将输入转换为整数。

        Args:
            value: 任意输入值。

        Returns:
            int: 转换成功的整数，失败时返回 0。
        """
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _normalize_instance_id(self, raw_value: Any) -> int | None:
        """规范化实例 ID。

        Args:
            raw_value: 路由层传入的实例 ID。

        Returns:
            int | None: 解析后的实例 ID，空值返回 None。

        Raises:
            AutoClassifyError: 当值无效或无法转换为整数时抛出。
        """
        if raw_value in (None, ""):
            return None
        if isinstance(raw_value, bool):
            raise AutoClassifyError("instance_id 参数无效")
        try:
            return int(raw_value)
        except (TypeError, ValueError) as exc:
            raise AutoClassifyError("instance_id 必须为整数") from exc

    def _coerce_bool(self, value: Any, *, default: bool) -> bool:
        """将输入值转换为布尔型。

        Args:
            value: 原始输入值。
            default: None 或空字符串时的默认值。

        Returns:
            bool: 解析后的布尔结果。

        Raises:
            AutoClassifyError: 当输入无法解析为布尔值时抛出。
        """
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return default
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        raise AutoClassifyError("use_optimized 参数无效")

    @staticmethod
    def _normalize_errors(errors: Any) -> list[str]:
        """规范化错误结构为字符串列表。

        Args:
            errors: 可能为字符串、列表或 None 的错误集合。

        Returns:
            list[str]: 去除 None/空值后的错误消息列表。
        """
        if not errors:
            return []
        if isinstance(errors, str):
            return [errors]
        try:
            return [str(item) for item in errors if item]
        except TypeError:
            return []
