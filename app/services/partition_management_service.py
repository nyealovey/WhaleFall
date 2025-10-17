"""
分区管理服务
负责创建、清理与查询数据库容量相关表的分区信息
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import DatabaseError
from app.utils.structlog_config import log_error, log_info, log_warning

MODULE = "partition_service"


@dataclass(slots=True)
class PartitionAction:
    """记录分区操作的结果，便于结构化日志与返回值"""

    table: str
    table_name: str
    partition_name: str
    display_name: str
    status: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PartitionManagementService:
    """PostgreSQL 分区管理服务"""

    def __init__(self) -> None:
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
        """
        创建指定日期所在月份的分区（包含四张相关表）
        返回生成的分区信息；若任何分区创建失败将抛出 DatabaseError
        """
        month_start, month_end = self._month_window(partition_date)
        actions: list[PartitionAction] = []
        failures: list[dict[str, Any]] = []

        for table_key, table_config in self.tables.items():
            from app.utils.time_utils import time_utils
            partition_name = f"{table_config['partition_prefix']}{time_utils.format_china_time(month_start, '%Y_%m')}"
            if self._partition_exists(partition_name):
                actions.append(
                    PartitionAction(
                        table=table_key,
                        table_name=table_config["table_name"],
                        partition_name=partition_name,
                        display_name=table_config["display_name"],
                        status="exists",
                    )
                )
                log_info(
                    "分区已存在，跳过创建",
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
                    )
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
                    }
                )
                log_error(
                    "创建分区失败",
                    module=MODULE,
                    partition_name=partition_name,
                    table=table_key,
                    exception=exc,
                )
            except Exception as exc:  # pragma: no cover - 防御性分支
                failures.append(
                    {
                        "table": table_key,
                        "partition_name": partition_name,
                        "error": str(exc),
                    }
                )
                log_error(
                    "创建分区发生未知错误",
                    module=MODULE,
                    partition_name=partition_name,
                    table=table_key,
                    exception=exc,
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
        """
        批量创建未来几个月的分区
        若任一月份创建失败，会收集错误并抛出 DatabaseError
        """
        created: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []
        today = date.today()

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
            except Exception as exc:
                issues.append({"month": target_month.isoformat(), "message": str(exc)})
                log_error(
                    "创建未来分区遇到未捕获异常",
                    module=MODULE,
                    month=target_month.isoformat(),
                    exception=exc,
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
        """
        清理超过保留期的旧分区
        全部成功返回删除记录列表，若有失败则抛出 DatabaseError
        """
        cutoff_date = (date.today() - timedelta(days=retention_months * 31)).replace(day=1)
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
                        )
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
                        }
                    )
                    log_error(
                        "删除旧分区失败",
                        module=MODULE,
                        partition_name=partition_name,
                        table=table_key,
                        exception=exc,
                    )
                except Exception as exc:  # pragma: no cover - 防御性分支
                    failures.append(
                        {
                            "table": table_key,
                            "partition_name": partition_name,
                            "error": str(exc),
                        }
                    )
                    log_error(
                        "删除旧分区遇到未捕获异常",
                        module=MODULE,
                        partition_name=partition_name,
                        table=table_key,
                        exception=exc,
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
    def get_partition_info(self) -> dict[str, Any]:
        """获取所有分区的详细信息"""
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            log_error("数据库连接失败", module=MODULE, exception=exc)
            raise DatabaseError(message="数据库连接失败") from exc

        partitions: list[dict[str, Any]] = []
        total_size_bytes = 0
        total_records = 0

        for table_key, table_config in self.tables.items():
            table_partitions = self._get_table_partitions(table_key, table_config)
            partitions.extend(table_partitions)
            for partition in table_partitions:
                total_size_bytes += partition.get("size_bytes", 0)
                total_records += partition.get("record_count", 0)

        partitions.sort(key=lambda item: item["name"])
        log_info(
            "完成分区信息查询",
            module=MODULE,
            partition_count=len(partitions),
            total_size_bytes=total_size_bytes,
        )

        return {
            "partitions": partitions,
            "total_partitions": len(partitions),
            "total_size_bytes": total_size_bytes,
            "total_size": self._format_size(total_size_bytes),
            "total_records": total_records,
            "tables": list(self.tables.keys()),
        }

    def get_partition_statistics(self) -> dict[str, Any]:
        """基于分区信息生成概要统计"""
        info = self.get_partition_info()
        return {
            "total_records": info["total_records"],
            "total_partitions": info["total_partitions"],
            "total_size": info["total_size"],
            "total_size_bytes": info["total_size_bytes"],
            "partitions": info["partitions"],
            "tables": info["tables"],
        }

    # ------------------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------------------
    def _month_window(self, target_date: date) -> tuple[date, date]:
        """计算目标日期所在月份的开始和结束"""
        month_start = target_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        return month_start, month_end

    def _get_table_partitions(self, table_key: str, table_config: dict[str, str]) -> list[dict[str, Any]]:
        """查询单张表的分区信息"""
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
                    }
                )
            except Exception as exc:  # pragma: no cover - 单条记录失败不影响总体
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
        """检查指定分区是否存在"""
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
        """返回需要清理的分区名称"""
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
                partition_date = datetime.strptime(date_str, "%Y/%m/%d").date()
            except ValueError:
                continue
            if partition_date < cutoff_date:
                partitions.append(row.tablename)
        return partitions

    def _extract_date_from_partition_name(self, partition_name: str, prefix: str) -> Optional[str]:
        """从分区名称中解析出日期字符串"""
        try:
            date_part = partition_name.replace(prefix, "")
            year, month, *_ = date_part.split("_")
            return f"{year}/{month}/01"
        except ValueError:
            return None

    def _get_partition_record_count(self, partition_name: str) -> int:
        """查询单个分区的记录数"""
        query = f"SELECT COUNT(*) FROM {partition_name};"
        try:
            result = db.session.execute(text(query)).scalar()
            return int(result or 0)
        except SQLAlchemyError as exc:
            log_warning(
                "获取分区记录数失败",
                module=MODULE,
                partition_name=partition_name,
                error=str(exc),
            )
            return 0

    def _get_partition_status(self, date_str: Optional[str]) -> str:
        """根据日期推断分区状态"""
        if not date_str:
            return "unknown"
        try:
            partition_date = datetime.strptime(date_str, "%Y/%m/%d").date()
        except ValueError:
            return "unknown"

        today = date.today()
        current_month = today.replace(day=1)

        if partition_date == current_month:
            return "current"
        if partition_date < current_month:
            return "past"
        return "future"

    def _create_partition_indexes(self, partition_name: str, table_config: dict[str, str]) -> None:
        """为不同分区表创建必要索引"""
        table_name = table_config["table_name"]
        index_sql_list: list[str] = []

        if table_name == "database_size_stats":
            index_sql_list = [
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_db "
                f"ON {partition_name} (instance_id, database_name);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_date "
                f"ON {partition_name} (collected_date);",
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
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance "
                f"ON {partition_name} (instance_id);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_date "
                f"ON {partition_name} (collected_date);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_date "
                f"ON {partition_name} (instance_id, collected_date);",
            ]
        elif table_name == "instance_size_aggregations":
            index_sql_list = [
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance "
                f"ON {partition_name} (instance_id);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_period "
                f"ON {partition_name} (period_start, period_end);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_type "
                f"ON {partition_name} (period_type, period_start);",
            ]

        for index_sql in index_sql_list:
            db.session.execute(text(index_sql))

    def _format_size(self, size_bytes: int) -> str:
        """将字节数格式化为可读字符串"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024**2:
            return f"{size_bytes / 1024:.1f} KB"
        if size_bytes < 1024**3:
            return f"{size_bytes / (1024**2):.1f} MB"
        return f"{size_bytes / (1024**3):.1f} GB"

    @staticmethod
    def _rollback_on_error():
        """提供一个上下文管理器式的回滚封装"""
        class _RollbackContext:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc, tb):
                db.session.rollback()
                return False

        return _RollbackContext()
