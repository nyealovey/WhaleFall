"""数据库大小统计聚合定时任务.

负责计算每周、每月、每季度的统计聚合数据.
"""

import time
from collections.abc import Sequence
from contextlib import suppress
from datetime import date
from typing import Any

import structlog
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.errors import AppError
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance import Instance
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.services.aggregation.aggregation_service import AggregationService
from app.services.sync_session_service import SyncItemStats, sync_session_service
from app.utils.structlog_config import get_sync_logger, log_error, log_info
from app.utils.time_utils import time_utils

STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
TASK_MODULE = "aggregation_tasks"
PREVIOUS_PERIOD_OVERRIDES = {"daily": False}
MAX_HOUR_IN_DAY = 23
AGGREGATION_TASK_EXCEPTIONS: tuple[type[Exception], ...] = (
    AppError,
    SQLAlchemyError,
    RuntimeError,
    LookupError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def _select_periods(
    requested: Sequence[str] | None,
    logger: structlog.BoundLogger,
    allowed_periods: Sequence[str],
) -> list[str]:
    """根据请求的周期返回有效周期列表.

    Args:
        requested: 用户指定的周期集合,None 表示全部.
        logger: 用于记录未知周期的 logger.
        allowed_periods: 服务可用的周期序列.

    Returns:
        过滤并按允许顺序排列的周期列表.

    """
    allowed = list(allowed_periods)
    if not allowed:
        return []

    if requested is None:
        return allowed.copy()

    normalized: list[str] = []
    unknown: list[str] = []
    seen: set[str] = set()
    for item in requested:
        key = (item or "").strip().lower()
        if not key:
            continue
        if key in allowed_periods:
            if key not in seen:
                normalized.append(key)
                seen.add(key)
        else:
            unknown.append(item)

    if unknown:
        logger.warning(
            "忽略未知聚合周期",
            module="aggregation_sync",
            unknown_periods=unknown,
        )

    ordered = [period for period in allowed if period in normalized]
    return ordered if ordered else allowed.copy()


def _has_aggregation_for_period(period_type: str, period_start: date) -> bool:
    """判断某周期聚合是否已存在(实例级 + 数据库级均已落库).

    Args:
        period_type: 周期类型(daily/weekly/monthly/quarterly).
        period_start: 周期开始日期.

    Returns:
        bool: True 表示两类聚合均存在,False 表示需要执行.

    """
    db_exists = (
        db.session.query(DatabaseSizeAggregation.id)
        .filter(
            DatabaseSizeAggregation.period_type == period_type,
            DatabaseSizeAggregation.period_start == period_start,
        )
        .limit(1)
        .first()
        is not None
    )
    if not db_exists:
        return False
    return (
        db.session.query(InstanceSizeAggregation.id)
        .filter(
            InstanceSizeAggregation.period_type == period_type,
            InstanceSizeAggregation.period_start == period_start,
        )
        .limit(1)
        .first()
        is not None
    )


def _filter_periods_already_aggregated(
    service: AggregationService,
    selected_periods: Sequence[str],
    logger: structlog.BoundLogger,
) -> list[str]:
    """过滤掉已完成聚合的历史周期,避免重复全量扫描.

    默认调度场景下,周/月/季通常都是“上一周期”,每日重复执行会造成不必要的 DB 压力。

    Args:
        service: 聚合服务(提供周期计算器).
        selected_periods: 原始周期列表.
        logger: 日志记录器.

    Returns:
        list[str]: 需要继续执行的周期列表.

    """
    skipped: dict[str, str] = {}
    remaining: list[str] = []

    for period_type in selected_periods:
        period_start, _ = service.period_calculator.get_last_period(period_type)
        if _has_aggregation_for_period(period_type, period_start):
            skipped[period_type] = period_start.isoformat()
            continue
        remaining.append(period_type)

    if skipped:
        logger.info(
            "检测到历史周期已聚合,本次跳过执行",
            module="aggregation_sync",
            skipped_periods=skipped,
        )

    return remaining


def _extract_processed_records(result: dict[str, Any] | None) -> int:
    """提取聚合结果中的处理数量.

    Args:
        result: 聚合任务返回的结果字典.

    Returns:
        已处理记录数量,缺失时返回 0.

    """
    if not result:
        return 0
    return int(result.get("processed_records") or 0)


def _extract_error_message(result: dict[str, Any] | None) -> str:
    """提取聚合结果中的错误消息.

    Args:
        result: 聚合任务返回的结果字典.

    Returns:
        合并后的错误消息文本.

    """
    if not result:
        return "无返回结果"
    errors = result.get("errors")
    if isinstance(errors, list) and errors:
        return "; ".join(str(err) for err in errors)
    return result.get("message") or "未知错误"


def _build_skip_response(message: str) -> dict[str, Any]:
    """构造跳过执行的统一响应."""
    return {
        "status": STATUS_SKIPPED,
        "message": message,
        "metrics": {
            "aggregations_created": 0,
            "processed_instances": 0,
        },
        "periods_executed": [],
    }


def _init_aggregation_session(
    *,
    manual_run: bool,
    created_by: int | None,
    active_instances: Sequence[Instance],
    selected_periods: Sequence[str],
    logger: structlog.BoundLogger,
) -> tuple[SyncSession, dict[int, SyncInstanceRecord]]:
    """创建聚合同步会话并返回会话及记录索引."""
    if manual_run:
        sync_type = SyncOperationType.MANUAL_TASK.value
    else:
        created_by = None
        sync_type = SyncOperationType.SCHEDULED_TASK.value

    session = sync_session_service.create_session(
        sync_type=sync_type,
        sync_category=SyncCategory.AGGREGATION.value,
        created_by=created_by,
    )

    logger.info(
        "聚合同步会话已创建",
        module="aggregation_sync",
        session_id=session.session_id,
        instance_count=len(active_instances),
        manual_run=manual_run,
        created_by=created_by,
        periods=selected_periods,
    )

    instance_ids = [inst.id for inst in active_instances]
    records = sync_session_service.add_instance_records(
        session.session_id,
        instance_ids,
        sync_category=SyncCategory.AGGREGATION.value,
    )
    session.total_instances = len(active_instances)
    records_by_instance = {record.instance_id: record for record in records}
    return session, records_by_instance


def _normalize_period_results(
    instance: Instance,
    selected_periods: Sequence[str],
    period_results: dict[str, Any] | None,
    logger: structlog.BoundLogger,
) -> tuple[dict[str, dict[str, Any]], list[str], int]:
    """整理周期结果,提取错误与聚合数量."""
    filtered_period_results: dict[str, dict[str, Any]] = {}
    instance_errors: list[str] = []
    aggregated_count = 0

    for period_name in selected_periods:
        result = period_results.get(period_name) if period_results else None
        if result is None:
            result = {
                "status": STATUS_FAILED,
                "processed_records": 0,
                "message": "聚合服务未返回结果",
                "errors": ["聚合服务未返回结果"],
                "instance_id": instance.id,
                "instance_name": instance.name,
                "period_type": period_name,
            }
        filtered_period_results[period_name] = result

        status = (result.get("status") or STATUS_FAILED).lower()
        if status == STATUS_COMPLETED:
            logger.info(
                "实例聚合完成",
                module="aggregation_sync",
                period=period_name,
                instance_id=instance.id,
                instance_name=instance.name,
                processed_records=_extract_processed_records(result),
                message=result.get("message"),
            )
        elif status == STATUS_SKIPPED:
            logger.info(
                "实例聚合跳过",
                module="aggregation_sync",
                period=period_name,
                instance_id=instance.id,
                instance_name=instance.name,
                message=result.get("message"),
            )
        else:
            error_msg = _extract_error_message(result)
            instance_errors.append(f"{period_name}: {error_msg}")
            logger.error(
                "实例聚合失败",
                module="aggregation_sync",
                period=period_name,
                instance_id=instance.id,
                instance_name=instance.name,
                error=error_msg,
                errors=result.get("errors"),
            )

        aggregated_count += _extract_processed_records(result)

    return filtered_period_results, instance_errors, aggregated_count


def _process_instance_aggregation(
    service: AggregationService,
    instance: Instance,
    selected_periods: Sequence[str],
    logger: structlog.BoundLogger,
    record: SyncInstanceRecord | None,
) -> tuple[dict[str, Any], bool, int, set[int], set[int]]:
    """执行单实例聚合并更新同步记录."""
    started_records: set[int] = set()
    finalized_records: set[int] = set()
    if record and sync_session_service.start_instance_sync(record.id):
        started_records.add(record.id)
        db.session.commit()
    try:
        summary = service.calculate_instance_aggregations(
            instance.id,
            periods=selected_periods,
            use_current_periods=PREVIOUS_PERIOD_OVERRIDES,
        )
        period_results = summary.get("periods", {}) or {}
    except AGGREGATION_TASK_EXCEPTIONS as period_exc:  # pragma: no cover - 防御性日志
        logger.exception(
            "实例聚合执行异常",
            module="aggregation_sync",
            instance_id=instance.id,
            instance_name=instance.name,
            error=str(period_exc),
        )
        period_results = {
            period_name: {
                "status": STATUS_FAILED,
                "instance_id": instance.id,
                "instance_name": instance.name,
                "period_type": period_name,
                "message": f"{period_name} 聚合执行异常: {period_exc}",
                "errors": [str(period_exc)],
                "error": str(period_exc),
            }
            for period_name in selected_periods
        }

    filtered_period_results, instance_errors, aggregated_count = _normalize_period_results(
        instance,
        selected_periods,
        period_results,
        logger,
    )

    details = {
        "aggregations_created": aggregated_count,
        "aggregation_count": aggregated_count,
        "periods": filtered_period_results,
        "errors": instance_errors,
        "instance_id": instance.id,
        "instance_name": instance.name,
    }

    success = not instance_errors
    if record:
        if success:
            stats = SyncItemStats(items_synced=int(aggregated_count or 0))
            if sync_session_service.complete_instance_sync(
                record.id,
                stats=stats,
                sync_details=details,
            ):
                finalized_records.add(record.id)
                db.session.commit()
        elif sync_session_service.fail_instance_sync(
            record.id,
            error_message="; ".join(instance_errors),
            sync_details=details,
        ):
            finalized_records.add(record.id)
            db.session.commit()

    return details, success, aggregated_count, started_records, finalized_records


def _run_instance_aggregations(
    service: AggregationService,
    active_instances: Sequence[Instance],
    selected_periods: Sequence[str],
    records_by_instance: dict[int, Any],
    logger: structlog.BoundLogger,
) -> tuple[
    dict[int, dict[str, Any]],
    int,
    int,
    int,
    set[int],
    set[int],
]:
    """执行所有实例聚合并汇总结果."""
    instance_details: dict[int, dict[str, Any]] = {}
    successful_instances = 0
    failed_instances = 0
    total_instance_aggregations = 0
    started_record_ids: set[int] = set()
    finalized_record_ids: set[int] = set()

    for instance in active_instances:
        record = records_by_instance.get(instance.id)
        details, success, aggregated_count, started_records, finished_records = _process_instance_aggregation(
            service,
            instance,
            selected_periods,
            logger,
            record,
        )
        started_record_ids.update(started_records)
        finalized_record_ids.update(finished_records)
        instance_details[instance.id] = {
            "aggregations_created": aggregated_count,
            "errors": details.get("errors", []),
            "period_results": details.get("periods"),
        }
        total_instance_aggregations += aggregated_count
        if success:
            successful_instances += 1
        else:
            failed_instances += 1

    return (
        instance_details,
        successful_instances,
        failed_instances,
        total_instance_aggregations,
        started_record_ids,
        finalized_record_ids,
    )


def _summarize_database_periods(
    service: AggregationService,
    selected_periods: Sequence[str],
    logger: structlog.BoundLogger,
) -> tuple[list[dict[str, Any]], int]:
    """汇总数据库级聚合结果."""
    period_summaries: list[dict[str, Any]] = []
    total_database_aggregations = 0
    database_period_results = service.aggregate_database_periods(
        selected_periods,
        use_current_periods=PREVIOUS_PERIOD_OVERRIDES,
    )
    for period_name in selected_periods:
        db_result = database_period_results.get(period_name)
        if db_result is None:
            db_result = {
                "status": STATUS_FAILED,
                "processed_records": 0,
                "message": "聚合服务未返回结果",
                "errors": ["聚合服务未返回结果"],
                "error": "聚合服务未返回结果",
                "period_type": period_name,
            }
        status = (db_result.get("status") or STATUS_FAILED).lower()
        if status == STATUS_COMPLETED:
            logger.info(
                "数据库级聚合完成",
                module="aggregation_sync",
                period=period_name,
                processed_records=db_result.get("processed_records", 0),
                processed_instances=db_result.get("processed_instances"),
            )
        elif status == STATUS_SKIPPED:
            logger.info(
                "数据库级聚合跳过",
                module="aggregation_sync",
                period=period_name,
                message=db_result.get("message"),
            )
        else:
            logger.error(
                "数据库级聚合失败",
                module="aggregation_sync",
                period=period_name,
                error=db_result.get("error"),
                errors=db_result.get("errors"),
            )
        db_result.setdefault("period_type", period_name)
        period_summaries.append(db_result)
        total_database_aggregations += _extract_processed_records(db_result)
    return period_summaries, total_database_aggregations


def calculate_database_size_aggregations(
    *,
    manual_run: bool = False,
    periods: list[str] | None = None,
    created_by: int | None = None,
) -> dict[str, Any]:
    """计算数据库大小统计聚合(按日/周/月/季依次执行).

    Args:
        manual_run: 是否由用户手动触发,True 表示手动执行.
        periods: 需要计算的聚合周期列表,取值 daily/weekly/monthly/quarterly,默认全部执行.
        created_by: 手动触发时记录的用户 ID.

    Returns:
        dict[str, Any]: 聚合执行结果与指标统计.

    """
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        task_started_at = time.perf_counter()
        session = None
        started_record_ids, finalized_record_ids = set(), set()
        try:
            sync_logger.info("开始执行数据库大小统计聚合任务", module="aggregation_sync")

            if not bool(app.config.get("AGGREGATION_ENABLED", True)):
                sync_logger.info("数据库大小统计聚合功能已禁用", module="aggregation_sync")
                return _build_skip_response("统计聚合功能已禁用")

            active_instances = Instance.query.filter_by(is_active=True).all()
            if not active_instances:
                sync_logger.warning("没有找到活跃的数据库实例", module="aggregation_sync")
                return _build_skip_response("没有活跃的数据库实例需要聚合")

            service = AggregationService()
            selected_periods = _select_periods(periods, sync_logger, service.period_types)
            if not selected_periods:
                sync_logger.warning(
                    "未选择任何有效的聚合周期,任务直接完成",
                    module="aggregation_sync",
                    requested_periods=periods,
                )
                return _build_skip_response("未选择有效的聚合周期,未执行统计任务")

            if not manual_run and periods is None:
                selected_periods = _filter_periods_already_aggregated(
                    service,
                    selected_periods,
                    sync_logger,
                )
                if not selected_periods:
                    sync_logger.info(
                        "所有周期均已聚合,任务直接跳过",
                        module="aggregation_sync",
                    )
                    return _build_skip_response("所有周期均已聚合,无需重复执行")

            sync_logger.info(
                "找到活跃实例,准备创建同步会话",
                module="aggregation_sync",
                instance_count=len(active_instances),
                manual_run=manual_run,
                periods=selected_periods,
            )

            session, records_by_instance = _init_aggregation_session(
                manual_run=manual_run,
                created_by=created_by,
                active_instances=active_instances,
                selected_periods=selected_periods,
                logger=sync_logger,
            )
            db.session.commit()

            (
                instance_details,
                successful_instances,
                failed_instances,
                total_instance_aggregations,
                instance_started_ids,
                instance_finalized_ids,
            ) = _run_instance_aggregations(
                service,
                active_instances,
                selected_periods,
                records_by_instance,
                sync_logger,
            )
            started_record_ids.update(instance_started_ids)
            finalized_record_ids.update(instance_finalized_ids)

            period_summaries, total_database_aggregations = _summarize_database_periods(
                service,
                selected_periods,
                sync_logger,
            )

            session.successful_instances = successful_instances
            session.failed_instances = failed_instances
            session.status = "completed" if failed_instances == 0 else "failed"
            session.completed_at = time_utils.now()
            db.session.commit()

            overall_status = STATUS_COMPLETED if failed_instances == 0 else STATUS_FAILED
            message = (
                f"统计聚合完成: 成功 {successful_instances} 个实例,失败 {failed_instances} 个实例"
                if failed_instances
                else f"统计聚合完成,共处理 {successful_instances} 个实例"
            )
            total_duration_seconds = time.perf_counter() - task_started_at

            sync_logger.info(
                "统计聚合任务完成",
                module="aggregation_sync",
                session_id=session.session_id,
                successful_instances=successful_instances,
                failed_instances=failed_instances,
                total_instance_aggregations=total_instance_aggregations,
                total_database_aggregations=total_database_aggregations,
                manual_run=manual_run,
                duration_seconds=round(total_duration_seconds, 2),
            )

            return {
                "status": overall_status,
                "message": message,
                "session_id": session.session_id,
                "periods_executed": selected_periods,
                "details": {
                    "periods": period_summaries,
                    "instances": instance_details,
                },
                "metrics": {
                    "instances": {
                        "total": len(active_instances),
                        "successful": successful_instances,
                        "failed": failed_instances,
                    },
                    "records": {
                        "instance": total_instance_aggregations,
                        "database": total_database_aggregations,
                        "total": total_instance_aggregations + total_database_aggregations,
                    },
                },
            }
        except AGGREGATION_TASK_EXCEPTIONS as exc:
            sync_logger.exception(
                "统计聚合任务异常",
                module="aggregation_sync",
                error=str(exc),
                duration_seconds=round(time.perf_counter() - task_started_at, 2),
            )
            if session is not None:
                with suppress(*AGGREGATION_TASK_EXCEPTIONS):  # pragma: no cover - 防御性处理
                    db.session.rollback()
                leftover_ids = started_record_ids - finalized_record_ids
                for record_id in leftover_ids:
                    with suppress(*AGGREGATION_TASK_EXCEPTIONS):
                        sync_session_service.fail_instance_sync(
                            record_id,
                            error_message=f"聚合任务异常: {exc}",
                        )
                session.status = "failed"
                session.completed_at = time_utils.now()
                db.session.add(session)
                db.session.commit()

            return {
                "status": STATUS_FAILED,
                "message": f"统计聚合任务执行失败: {exc}",
                "error": str(exc),
                "periods_executed": locals().get("selected_periods"),
            }


def calculate_instance_aggregations(instance_id: int) -> dict[str, Any]:
    """计算指定实例的统计聚合.

    为指定实例计算所有周期(日/周/月/季)的聚合数据.

    Args:
        instance_id: 实例ID.

    Returns:
        聚合结果字典,包含状态、消息和各周期的聚合详情.

    """
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            log_info(
                "开始计算实例统计聚合",
                module=TASK_MODULE,
                instance_id=instance_id,
            )

            instance = Instance.query.get(instance_id)
            if not instance:
                return {
                    "status": STATUS_FAILED,
                    "message": f"实例 {instance_id} 不存在",
                }

            if not instance.is_active:
                return {
                    "status": STATUS_SKIPPED,
                    "message": f"实例 {instance_id} 未激活",
                }

            # 创建聚合服务
            service = AggregationService()

            # 计算实例的聚合数据
            result = service.calculate_instance_aggregations(
                instance_id,
                use_current_periods=PREVIOUS_PERIOD_OVERRIDES,
            )
            db.session.commit()

            log_info(
                "实例统计聚合完成",
                module=TASK_MODULE,
                instance_id=instance_id,
                status=result.get("status"),
                result_message=result.get("message"),
            )

        except AGGREGATION_TASK_EXCEPTIONS as exc:
            log_error(
                "计算实例统计聚合失败",
                module=TASK_MODULE,
                exception=exc,
                instance_id=instance_id,
            )
            return {
                "status": STATUS_FAILED,
                "message": f"计算实例 {instance_id} 统计聚合失败: {exc}",
                "error": str(exc),
            }
        else:
            return result


def calculate_period_aggregations(period_type: str, start_date: date, end_date: date) -> dict[str, Any]:
    """计算指定周期的统计聚合.

    Args:
        period_type: 周期类型(weekly=周、monthly=月、quarterly=季度).
        start_date: 周期开始日期.
        end_date: 周期结束日期.

    Returns:
        Dict[str, Any]: 聚合执行结果.

    """
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            log_info(
                "开始计算指定周期统计聚合",
                module=TASK_MODULE,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )

            # 创建聚合服务
            service = AggregationService()

            # 计算指定周期的聚合数据
            result = service.calculate_period_aggregations(period_type, start_date, end_date)
            db.session.commit()

            log_info(
                "指定周期统计聚合完成",
                module=TASK_MODULE,
                period_type=period_type,
                status=result.get("status"),
                result_message=result.get("message"),
            )

        except AGGREGATION_TASK_EXCEPTIONS as exc:
            log_error(
                "计算指定周期统计聚合失败",
                module=TASK_MODULE,
                exception=exc,
                period_type=period_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            return {
                "status": STATUS_FAILED,
                "message": f"计算 {period_type} 周期统计聚合失败: {exc}",
                "error": str(exc),
            }
        else:
            return result


def get_aggregation_status() -> dict[str, Any]:
    """获取聚合状态信息.

    Returns:
        Dict[str, Any]: 状态信息

    """
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:

            # 获取今日聚合统计
            today = time_utils.now().date()

            # 获取最近聚合时间
            latest_aggregation = DatabaseSizeAggregation.query.order_by(
                desc(DatabaseSizeAggregation.calculated_at),
            ).first()

            # 获取各周期类型的聚合数量
            aggregation_counts = (
                db.session.query(
                    DatabaseSizeAggregation.period_type,
                    func.count(DatabaseSizeAggregation.id).label("count"),
                )
                .group_by(DatabaseSizeAggregation.period_type)
                .all()
            )

            # 获取总实例数
            total_instances = Instance.query.filter_by(is_active=True).count()

            return {
                "status": STATUS_COMPLETED,
                "latest_aggregation": latest_aggregation.calculated_at.isoformat() if latest_aggregation else None,
                "aggregation_counts": {row.period_type: row.count for row in aggregation_counts},
                "total_instances": total_instances,
                "check_date": today.isoformat(),
            }

        except AGGREGATION_TASK_EXCEPTIONS as exc:
            log_error(
                "获取聚合状态失败",
                module=TASK_MODULE,
                exception=exc,
            )
            return {
                "status": STATUS_FAILED,
                "message": f"获取聚合状态失败: {exc}",
                "error": str(exc),
            }


def validate_aggregation_config() -> dict[str, Any]:
    """验证聚合配置.

    Returns:
        Dict[str, Any]: 验证结果

    """
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        try:
            config_issues = []

            aggregation_enabled = bool(app.config.get("AGGREGATION_ENABLED", True))
            if not aggregation_enabled:
                config_issues.append("数据库大小统计聚合已禁用")

            aggregation_hour = int(app.config.get("AGGREGATION_HOUR", 4))
            if aggregation_hour < 0 or aggregation_hour > MAX_HOUR_IN_DAY:
                config_issues.append("聚合时间配置无效,应为0-23之间的整数")

            status = STATUS_COMPLETED if not config_issues else STATUS_FAILED
            message = "聚合配置验证通过" if not config_issues else "聚合配置存在需要关注的问题"
        except AGGREGATION_TASK_EXCEPTIONS as exc:
            log_error(
                "验证聚合配置失败",
                module=TASK_MODULE,
                exception=exc,
            )
            return {
                "status": STATUS_FAILED,
                "message": f"验证聚合配置失败: {exc}",
                "error": str(exc),
            }
        else:
            return {
                "status": status,
                "message": message,
                "issues": config_issues,
                "config": {
                    "enabled": aggregation_enabled,
                    "hour": aggregation_hour,
                },
            }
