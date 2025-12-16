"""分区管理服务.

负责创建、清理与查询数据库容量相关表的分区信息.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any, Self

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import table

from app import db
from app.errors import DatabaseError
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from types import TracebackType

MODULE = "partition_service"
PARTITION_SERVICE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    DatabaseError,
    SQLAlchemyError,
    RuntimeError,
    LookupError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
)
DECEMBER_MONTH = 12
BYTES_IN_KIB = 1024
BYTES_IN_MIB = BYTES_IN_KIB**2
BYTES_IN_GIB = BYTES_IN_KIB**3


@dataclass(slots=True)
class PartitionAction:
    """记录分区操作的结果,便于结构化日志与返回值."""

    table: str
    table_name: str
    partition_name: str
    display_name: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """将分区操作转换为序列化字典.

        Returns:
            dict[str, Any]: 便于日志或响应使用的字典.

        """
        return asdict(self)


class PartitionManagementService:
    """PostgreSQL 分区管理服务."""

    def __init__(self) -> None:
        """初始化分区管理服务,配置不同分区表的元数据."""
        self.tables: dict[str, dict[str, str]] = {
            "stats": {
                "table_name": "database_size_stats",
                "table_type": "stats",
                "partition_prefix": "database_size_stats_",
                "partition_column": "collected_date",
                "display_name": "数据库统计表",
            },
            "aggregations": {
                "table_name": "database_size_aggregations",
                "table_type": "aggregations",
                "partition_prefix": "database_size_aggregations_",
                "partition_column": "period_start",
                "display_name": "数据库聚合表",
            },
            "instance_stats": {
                "table_name": "instance_size_stats",
                "table_type": "instance_stats",
                "partition_prefix": "instance_size_stats_",
                "partition_column": "collected_date",
                "display_name": "实例统计表",
            },
            "instance_aggregations": {
                "table_name": "instance_size_aggregations",
                "table_type": "instance_aggregations",
                "partition_prefix": "instance_size_aggregations_",
                "partition_column": "period_start",
                "display_name": "实例聚合表",
            },
        }

    # ------------------------------------------------------------------------------
    # 创建与清理分区
    # ------------------------------------------------------------------------------
    def create_partition(self, partition_date: date) -> dict[str, Any]:
        """创建指定日期所在月份的分区.

        为四张相关表(database_size_stats、database_size_aggregations、
        instance_size_stats、instance_size_aggregations)创建月度分区.
        如果分区已存在则跳过,如果创建失败则回滚所有操作.

        Args:
            partition_date: 分区日期,将创建该日期所在月份的分区.
                例如传入 2025-11-15,将创建 2025-11 月份的分区.

        Returns:
            包含分区创建结果的字典,格式如下:
            {
                'partition_window': {
                    'start': '2025-11-01',
                    'end': '2025-12-01'
                },
                'actions': [
                    {
                        'table': 'stats',
                        'table_name': 'database_size_stats',
                        'partition_name': 'database_size_stats_2025_11',
                        'display_name': '数据库统计表',
                        'status': 'created'  # 或 'exists'
                    },
                    ...
                ]
            }

        Raises:
            DatabaseError: 当分区创建失败或提交事务失败时抛出,
                包含失败的分区信息和错误详情.

        """
        month_start, month_end = self._month_window(partition_date)
        actions: list[PartitionAction] = []
        failures: list[dict[str, Any]] = []

        for table_key, table_config in self.tables.items():
            partition_name = f"{table_config['partition_prefix']}{time_utils.format_china_time(month_start, '%Y_%m')}"
            if self._partition_exists(partition_name):
                actions.append(
                    PartitionAction(
                        table=table_key,
                        table_name=table_config["table_name"],
                        partition_name=partition_name,
                        display_name=table_config["display_name"],
                        status="exists",
                    ),
                )
                log_info(
                    "分区已存在,跳过创建",
                    module=MODULE,
                    partition_name=partition_name,
                    table=table_key,
                )
                continue

            try:
                create_sql = (
                    f"CREATE TABLE {partition_name} "
                    f"PARTITION OF {table_config['table_name']} "
                    f"FOR VALUES FROM ('{month_start}') TO ('{month_end}');"
                )
                db.session.execute(text(create_sql))
                self._create_partition_indexes(partition_name, table_config)
                comment_sql = (
                    f"COMMENT ON TABLE {partition_name} IS "
                    f"'{table_config['display_name']}分区表 - {time_utils.format_china_time(month_start, '%Y-%m')}';"
                )
                db.session.execute(text(comment_sql))
                actions.append(
                    PartitionAction(
                        table=table_key,
                        table_name=table_config["table_name"],
                        partition_name=partition_name,
                        display_name=table_config["display_name"],
                        status="created",
                    ),
                )
                log_info(
                    "成功创建分区",
                    module=MODULE,
                    partition_name=partition_name,
                    table=table_key,
                )
            except SQLAlchemyError as exc:
                failures.append(
                    {
                        "table": table_key,
                        "partition_name": partition_name,
                        "error": str(exc),
                    },
                )
                log_error(
                    "创建分区失败",
                    module=MODULE,
                    partition_name=partition_name,
                    table=table_key,
                    exception=exc,
                )
            except PARTITION_SERVICE_EXCEPTIONS as exc:  # pragma: no cover - 防御性分支
                failures.append(
                    {
                        "table": table_key,
                        "partition_name": partition_name,
                        "error": str(exc),
                    },
                )
                safe_exc = exc if isinstance(exc, Exception) else Exception(str(exc))
                log_error(
                    "创建分区发生未知错误",
                    module=MODULE,
                    partition_name=partition_name,
                    table=table_key,
                    exception=safe_exc,
                )

        if failures:
            with self._rollback_on_error():
                raise DatabaseError(
                    message="部分分区创建失败",
                    extra={
                        "partition_window": {
                            "start": month_start.isoformat(),
                            "end": month_end.isoformat(),
                        },
                        "actions": [action.to_dict() for action in actions],
                        "failures": failures,
                    },
                )

        try:
            db.session.commit()
        except SQLAlchemyError as exc:
            with self._rollback_on_error():
                log_error(
                    "提交分区创建事务失败",
                    module=MODULE,
                    exception=exc,
                    partition_window={"start": month_start.isoformat(), "end": month_end.isoformat()},
                )
                raise DatabaseError(
                    message="提交分区创建事务失败",
                    extra={"partition_window": {"start": month_start.isoformat(), "end": month_end.isoformat()}},
                ) from exc

        return {
            "partition_window": {
                "start": month_start.isoformat(),
                "end": month_end.isoformat(),
            },
            "actions": [action.to_dict() for action in actions],
        }

    def create_future_partitions(self, months_ahead: int = 3) -> dict[str, Any]:
        """批量创建未来几个月的分区.

        从当前月份开始,创建未来指定月数的分区.如果某个月份的分区创建失败,
        会继续尝试创建其他月份,最后收集所有错误并抛出异常.

        Args:
            months_ahead: 要创建的未来月份数量,默认为 3 个月.

        Returns:
            包含创建结果的字典,格式如下:
            {
                'months_processed': 3,
                'created': [
                    {
                        'month': '2025-11-01',
                        'result': {...}  # create_partition 的返回值
                    },
                    ...
                ]
            }

        Raises:
            DatabaseError: 当任一月份的分区创建失败时抛出,
                包含所有失败的月份信息和已成功创建的月份列表.

        """
        created: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []
        today = time_utils.now().date()

        for offset in range(months_ahead):
            target_month = (today.replace(day=1) + timedelta(days=offset * 31)).replace(day=1)
            try:
                result = self.create_partition(target_month)
                created.append({"month": target_month.isoformat(), "result": result})
            except DatabaseError as exc:
                issues.append({"month": target_month.isoformat(), "message": exc.message, "extra": exc.extra})
                log_warning(
                    "创建未来分区失败",
                    module=MODULE,
                    month=target_month.isoformat(),
                    error=exc.message,
                    issues=exc.extra,
                )
            except PARTITION_SERVICE_EXCEPTIONS as exc:
                issues.append({"month": target_month.isoformat(), "message": str(exc)})
                safe_exc = exc if isinstance(exc, Exception) else Exception(str(exc))
                log_error(
                    "创建未来分区遇到未捕获异常",
                    module=MODULE,
                    month=target_month.isoformat(),
                    exception=safe_exc,
                )

        if issues:
            raise DatabaseError(
                message="部分未来分区创建失败",
                extra={"issues": issues, "created": created},
            )

        return {
            "months_processed": months_ahead,
            "created": created,
        }

    def cleanup_old_partitions(self, retention_months: int = 12) -> dict[str, Any]:
        """清理超过保留期的旧分区.

        删除所有早于保留期的分区表.保留期从当前日期往前推算指定月数.
        如果任何分区删除失败,会回滚所有操作并抛出异常.

        Args:
            retention_months: 保留月数,默认为 12 个月.
                例如设置为 12,则保留最近 12 个月的分区,删除更早的分区.

        Returns:
            包含清理结果的字典,格式如下:
            {
                'cutoff_date': '2024-11-01',
                'dropped': [
                    {
                        'table': 'stats',
                        'table_name': 'database_size_stats',
                        'partition_name': 'database_size_stats_2024_10',
                        'display_name': '数据库统计表',
                        'status': 'dropped'
                    },
                    ...
                ]
            }

        Raises:
            DatabaseError: 当分区删除失败或提交事务失败时抛出,
                包含失败的分区信息和已删除的分区列表.

        """
        cutoff_date = (time_utils.now().date() - timedelta(days=retention_months * 31)).replace(day=1)
        dropped: list[PartitionAction] = []
        failures: list[dict[str, Any]] = []

        for table_key, table_config in self.tables.items():
            partitions_to_drop = self._get_partitions_to_cleanup(cutoff_date, table_config)
            for partition_name in partitions_to_drop:
                try:
                    drop_sql = f"DROP TABLE IF EXISTS {partition_name};"
                    db.session.execute(text(drop_sql))
                    dropped.append(
                        PartitionAction(
                            table=table_key,
                            table_name=table_config["table_name"],
                            partition_name=partition_name,
                            display_name=table_config["display_name"],
                            status="dropped",
                        ),
                    )
                    log_info(
                        "成功删除旧分区",
                        module=MODULE,
                        partition_name=partition_name,
                        table=table_key,
                    )
                except SQLAlchemyError as exc:
                    failures.append(
                        {
                            "table": table_key,
                            "partition_name": partition_name,
                            "error": str(exc),
                        },
                    )
                    log_error(
                        "删除旧分区失败",
                        module=MODULE,
                        partition_name=partition_name,
                        table=table_key,
                        exception=exc,
                    )
                except PARTITION_SERVICE_EXCEPTIONS as exc:  # pragma: no cover - 防御性分支
                    failures.append(
                        {
                            "table": table_key,
                            "partition_name": partition_name,
                            "error": str(exc),
                        },
                    )
                    safe_exc = exc if isinstance(exc, Exception) else Exception(str(exc))
                    log_error(
                        "删除旧分区遇到未捕获异常",
                        module=MODULE,
                        partition_name=partition_name,
                        table=table_key,
                        exception=safe_exc,
                    )

        if failures:
            with self._rollback_on_error():
                raise DatabaseError(
                    message="部分旧分区清理失败",
                    extra={"failures": failures, "dropped": [action.to_dict() for action in dropped]},
                )

        try:
            db.session.commit()
        except SQLAlchemyError as exc:
            with self._rollback_on_error():
                log_error(
                    "提交旧分区清理事务失败",
                    module=MODULE,
                    exception=exc,
                )
                raise DatabaseError(message="提交旧分区清理事务失败") from exc

        return {
            "cutoff_date": cutoff_date.isoformat(),
            "dropped": [action.to_dict() for action in dropped],
        }

    # ------------------------------------------------------------------------------
    # 查询分区信息
    # ------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------------------
    def _month_window(self, target_date: date) -> tuple[date, date]:
        """计算目标日期所在月份的开始和结束日期.

        Args:
            target_date: 目标日期.

        Returns:
            包含月份开始和结束日期的元组 (month_start, month_end).
            month_start 为该月第一天,month_end 为下月第一天.

        Example:
            >>> service._month_window(date(2025, 11, 15))
            (date(2025, 11, 1), date(2025, 12, 1))

        """
        month_start = target_date.replace(day=1)
        if month_start.month == DECEMBER_MONTH:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        return month_start, month_end

    def _get_table_partitions(self, table_key: str, table_config: dict[str, str]) -> list[dict[str, Any]]:
        """查询单张表的所有分区信息.

        Args:
            table_key: 表的键名,如 'stats'、'aggregations'.
            table_config: 表配置字典,包含 table_name、partition_prefix 等信息.

        Returns:
            分区信息列表,每个元素包含分区名称、大小、记录数、日期、状态等信息.

        Raises:
            DatabaseError: 当数据库查询失败时抛出.

        """
        pattern = f"{table_config['partition_prefix']}%"
        query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
        FROM pg_tables
        WHERE tablename LIKE :pattern
        ORDER BY tablename;
        """

        try:
            rows = db.session.execute(text(query), {"pattern": pattern}).fetchall()
        except SQLAlchemyError as exc:
            log_error(
                "查询表分区信息失败",
                module=MODULE,
                table=table_key,
                exception=exc,
            )
            raise DatabaseError(message="查询分区信息失败", extra={"table": table_key}) from exc

        partitions: list[dict[str, Any]] = []
        for row in rows:
            try:
                date_str = self._extract_date_from_partition_name(row.tablename, table_config["partition_prefix"])
                record_count = self._get_partition_record_count(row.tablename)
                status = self._get_partition_status(date_str)
                partitions.append(
                    {
                        "name": row.tablename,
                        "table": table_config["table_name"],
                        "table_type": table_config.get("table_type", "unknown"),
                        "display_name": table_config["display_name"],
                        "size": row.size,
                        "size_bytes": row.size_bytes,
                        "record_count": record_count,
                        "date": date_str,
                        "status": status,
                    },
                )
            except PARTITION_SERVICE_EXCEPTIONS as exc:  # pragma: no cover - 单条记录失败不影响总体
                log_warning(
                    "处理单个分区信息失败",
                    module=MODULE,
                    table=table_key,
                    partition=row.tablename,
                    error=str(exc),
                )
                continue

        log_info(
            "获取表分区信息完成",
            module=MODULE,
            table=table_key,
            partition_count=len(partitions),
        )
        return partitions

    def _partition_exists(self, partition_name: str) -> bool:
        """检查指定分区表是否存在.

        Args:
            partition_name: 分区表名称.

        Returns:
            如果分区存在返回 True,否则返回 False.

        Raises:
            DatabaseError: 当数据库查询失败时抛出.

        """
        query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = :partition_name
        );
        """
        try:
            result = db.session.execute(text(query), {"partition_name": partition_name}).scalar()
            return bool(result)
        except SQLAlchemyError as exc:
            log_error("检查分区是否存在失败", module=MODULE, partition_name=partition_name, exception=exc)
            raise DatabaseError(message="检查分区是否存在失败", extra={"partition_name": partition_name}) from exc

    def _get_partitions_to_cleanup(self, cutoff_date: date, table_config: dict[str, str]) -> list[str]:
        """获取需要清理的分区名称列表.

        Args:
            cutoff_date: 截止日期,早于此日期的分区将被清理.
            table_config: 表配置字典,包含 table_name、partition_prefix 等信息.

        Returns:
            需要清理的分区名称列表.

        Raises:
            DatabaseError: 当数据库查询失败时抛出.

        """
        query = """
        SELECT tablename
        FROM pg_tables
        WHERE tablename LIKE :pattern
        ORDER BY tablename;
        """
        try:
            rows = db.session.execute(
                text(query),
                {"pattern": f"{table_config['partition_prefix']}%"},
            ).fetchall()
        except SQLAlchemyError as exc:
            log_error(
                "查询候选清理分区失败",
                module=MODULE,
                table=table_config["table_name"],
                exception=exc,
            )
            raise DatabaseError(message="查询待清理分区失败", extra={"table": table_config["table_name"]}) from exc

        partitions: list[str] = []
        for row in rows:
            date_str = self._extract_date_from_partition_name(row.tablename, table_config["partition_prefix"])
            if not date_str:
                continue
            try:
                partition_date = datetime.strptime(date_str, "%Y/%m/%d").replace(tzinfo=UTC).date()
            except ValueError:
                continue
            if partition_date < cutoff_date:
                partitions.append(row.tablename)
        return partitions

    def _extract_date_from_partition_name(self, partition_name: str, prefix: str) -> str | None:
        """从分区名称中解析出日期字符串.

        Args:
            partition_name: 分区表名称,如 'database_size_stats_2025_11'.
            prefix: 分区前缀,如 'database_size_stats_'.

        Returns:
            日期字符串,格式为 'YYYY/MM/DD',如 '2025/11/01'.
            如果解析失败返回 None.

        """
        try:
            date_part = partition_name.replace(prefix, "")
            year, month, *_ = date_part.split("_")
        except ValueError:
            return None
        return f"{year}/{month}/01"

    @staticmethod
    def _ensure_partition_identifier(partition_name: str) -> str:
        """校验并返回安全的分区名称.

        Args:
            partition_name: 待校验的分区表名.

        Returns:
            str: 仅包含字母、数字与下划线的合法分区名.

        Raises:
            ValueError: 当名称包含非法字符时抛出.

        """
        if not re.fullmatch(r"[A-Za-z0-9_]+", partition_name):
            msg = f"非法分区名称: {partition_name}"
            raise ValueError(msg)
        return partition_name

    def _get_partition_record_count(self, partition_name: str) -> int:
        """查询单个分区的记录数.

        Args:
            partition_name: 分区表名称.

        Returns:
            分区中的记录总数.如果查询失败返回 0.

        """
        safe_partition = self._ensure_partition_identifier(partition_name)
        try:
            partition_table = table(safe_partition)
            stmt = select(func.count()).select_from(partition_table)
            result = db.session.execute(stmt).scalar()
            return int(result or 0)
        except ValueError as exc:
            log_warning(
                "分区名称校验失败",
                module=MODULE,
                partition_name=partition_name,
                error=str(exc),
            )
            return 0
        except SQLAlchemyError as exc:
            log_warning(
                "获取分区记录数失败",
                module=MODULE,
                partition_name=partition_name,
                error=str(exc),
            )
            return 0

    def _get_partition_status(self, date_str: str | None) -> str:
        """根据日期推断分区状态.

        Args:
            date_str: 日期字符串,格式为 'YYYY/MM/DD'.

        Returns:
            分区状态:'current'(当前月)、'past'(过去月)、
            'future'(未来月)或 'unknown'(无法解析).

        """
        if not date_str:
            return "unknown"
        try:
            partition_date = datetime.strptime(date_str, "%Y/%m/%d").replace(tzinfo=UTC).date()
        except ValueError:
            return "unknown"

        today = time_utils.now().date()
        current_month = today.replace(day=1)

        if partition_date == current_month:
            return "current"
        if partition_date < current_month:
            return "past"
        return "future"

    def _create_partition_indexes(self, partition_name: str, table_config: dict[str, str]) -> None:
        """为分区表创建必要的索引.

        根据表类型创建不同的索引组合,以优化查询性能.

        Args:
            partition_name: 分区表名称.
            table_config: 表配置字典,包含 table_name 等信息.

        Returns:
            None

        """
        table_name = table_config["table_name"]
        index_sql_list: list[str] = []

        if table_name == "database_size_stats":
            index_sql_list = [
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_db "
                f"ON {partition_name} (instance_id, database_name);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_date ON {partition_name} (collected_date);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_date "
                f"ON {partition_name} (instance_id, collected_date);",
            ]
        elif table_name == "database_size_aggregations":
            index_sql_list = [
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_db "
                f"ON {partition_name} (instance_id, database_name);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_period "
                f"ON {partition_name} (period_start, period_end);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_type "
                f"ON {partition_name} (period_type, period_start);",
            ]
        elif table_name == "instance_size_stats":
            index_sql_list = [
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance ON {partition_name} (instance_id);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_date ON {partition_name} (collected_date);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_date "
                f"ON {partition_name} (instance_id, collected_date);",
            ]
        elif table_name == "instance_size_aggregations":
            index_sql_list = [
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance ON {partition_name} (instance_id);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_period "
                f"ON {partition_name} (period_start, period_end);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_type "
                f"ON {partition_name} (period_type, period_start);",
            ]

        for index_sql in index_sql_list:
            db.session.execute(text(index_sql))

    def _format_size(self, size_bytes: int) -> str:
        """将字节数格式化为可读的大小字符串.

        Args:
            size_bytes: 字节数.

        Returns:
            格式化后的大小字符串,如 '1.5 GB'、'256 MB'.

        """
        if size_bytes < BYTES_IN_KIB:
            return f"{size_bytes} B"
        if size_bytes < BYTES_IN_MIB:
            return f"{size_bytes / BYTES_IN_KIB:.1f} KB"
        if size_bytes < BYTES_IN_GIB:
            return f"{size_bytes / BYTES_IN_MIB:.1f} MB"
        return f"{size_bytes / BYTES_IN_GIB:.1f} GB"

    @staticmethod
    def _rollback_on_error() -> contextlib.AbstractContextManager[None]:
        """提供一个上下文管理器用于异常时自动回滚事务.

        Returns:
            上下文管理器对象,在退出时自动执行 db.session.rollback().

        Example:
            >>> with self._rollback_on_error():
            ...     raise DatabaseError("操作失败")

        """

        class _RollbackContext(contextlib.AbstractContextManager[None]):
            def __enter__(self) -> None:
                return None

            def __exit__(
                self,
                exc_type: type[BaseException] | None,
                exc: BaseException | None,
                tb: TracebackType | None,
            ) -> bool:
                db.session.rollback()
                return False

        return _RollbackContext()
