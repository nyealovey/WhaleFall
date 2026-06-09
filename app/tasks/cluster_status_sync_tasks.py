"""群集同步状态检测定时任务."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.core.constants.status_types import TaskRunStatus
from app.core.exceptions import AppError
from app.models.mysql_cluster import MySQLCluster
from app.models.sqlserver_cluster import SQLServerCluster
from app.schemas.task_run_summary import TaskRunSummaryFactory
from app.services.alerts.email_alert_event_service import EmailAlertEventService
from app.services.cluster_status_sync import ClusterStatusSyncService
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_sync_logger

CLUSTER_STATUS_TASK_EXCEPTIONS: tuple[type[Exception], ...] = (
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


@dataclass(slots=True)
class _ClusterStatusTotals:
    mysql_clusters_total: int = 0
    sqlserver_clusters_total: int = 0
    clusters_successful: int = 0
    clusters_failed: int = 0
    abnormal_database_count: int = 0
    abnormal_replica_count: int = 0


def _summary(totals: _ClusterStatusTotals) -> dict[str, Any]:
    payload = TaskRunSummaryFactory.base(task_key="sync_cluster_status")
    payload["metrics"] = {
        "mysql_clusters_total": totals.mysql_clusters_total,
        "sqlserver_clusters_total": totals.sqlserver_clusters_total,
        "clusters_successful": totals.clusters_successful,
        "clusters_failed": totals.clusters_failed,
        "abnormal_database_count": totals.abnormal_database_count,
        "abnormal_replica_count": totals.abnormal_replica_count,
    }
    return payload


def _resolve_run_id(
    *,
    task_runs_service: TaskRunsWriteService,
    manual_run: bool,
    created_by: int | None,
    run_id: str | None,
) -> str:
    resolved_run_id = task_runs_service.resolve_or_start_run(
        run_id=run_id,
        task_key="sync_cluster_status",
        task_name="群集同步状态检测",
        task_category="cluster",
        trigger_source="manual" if manual_run else "scheduled",
        created_by=created_by,
        summary_json=TaskRunSummaryFactory.base(task_key="sync_cluster_status"),
        result_url="/cluster",
    )
    db.session.commit()
    return resolved_run_id


def _init_items(
    *,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    mysql_clusters: list[MySQLCluster],
    sqlserver_clusters: list[SQLServerCluster],
) -> None:
    task_runs_service.init_items(
        run_id,
        items=[
            TaskRunItemInit(item_type="mysql_cluster", item_key=str(cluster.id), item_name=cluster.name)
            for cluster in mysql_clusters
        ]
        + [
            TaskRunItemInit(item_type="sqlserver_cluster", item_key=str(cluster.id), item_name=cluster.name)
            for cluster in sqlserver_clusters
        ],
    )
    db.session.commit()


def _record_result(
    *,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    item_type: str,
    cluster_id: int,
    cluster_name: str,
    result: dict[str, Any],
    totals: _ClusterStatusTotals,
    alert_event_service: EmailAlertEventService,
) -> None:
    status = str(result.get("status") or "")
    abnormal_database_count = int(result.get("abnormal_database_count", 0) or 0)
    abnormal_replica_count = int(result.get("abnormal_replica_count", 0) or 0)
    totals.abnormal_database_count += abnormal_database_count
    totals.abnormal_replica_count += abnormal_replica_count
    if status == "failed":
        totals.clusters_failed += 1
        task_runs_service.fail_item(
            run_id,
            item_type=item_type,
            item_key=str(cluster_id),
            error_message=str(result.get("error_message") or "群集同步状态检测失败"),
            details_json=result,
        )
    else:
        totals.clusters_successful += 1
        task_runs_service.complete_item(
            run_id,
            item_type=item_type,
            item_key=str(cluster_id),
            metrics_json={
                "abnormal_database_count": abnormal_database_count,
                "abnormal_replica_count": abnormal_replica_count,
            },
            details_json=result,
        )
    alert_event_service.record_cluster_status_event(
        cluster_type=item_type,
        cluster_id=cluster_id,
        cluster_name=cluster_name,
        run_id=run_id,
        result=result,
    )
    db.session.commit()


def _record_cluster_exception(
    *,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    item_type: str,
    cluster_id: int,
    cluster_name: str,
    exc: Exception,
    totals: _ClusterStatusTotals,
    alert_event_service: EmailAlertEventService,
) -> None:
    result = {
        "cluster_id": cluster_id,
        "status": "failed",
        "error_message": str(exc) or "群集同步状态检测失败",
        "abnormal_database_count": 0,
        "abnormal_replica_count": 0,
        "items": [],
        "replicas": [],
    }
    _record_result(
        task_runs_service=task_runs_service,
        run_id=run_id,
        item_type=item_type,
        cluster_id=cluster_id,
        cluster_name=cluster_name,
        result=result,
        totals=totals,
        alert_event_service=alert_event_service,
    )


def _finalize_run(task_runs_service: TaskRunsWriteService, run_id: str, totals: _ClusterStatusTotals) -> None:
    task_runs_service.finalize_run_with_summary(
        run_id,
        summary_json=_summary(totals),
        status_override=(
            TaskRunStatus.COMPLETED_WITH_ERRORS if totals.clusters_failed and totals.clusters_successful else None
        ),
    )
    db.session.commit()


def _fail_run(task_runs_service: TaskRunsWriteService, run_id: str, exc: Exception) -> None:
    task_runs_service.mark_run_failed(run_id, error_message=str(exc))
    db.session.commit()


def sync_cluster_status(
    *,
    manual_run: bool = False,
    created_by: int | None = None,
    run_id: str | None = None,
    **_: Any,
) -> None:
    """检测 MySQL 主从和 SQL Server AG 数据库同步状态."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        task_runs_service = TaskRunsWriteService()
        resolved_run_id = _resolve_run_id(
            task_runs_service=task_runs_service,
            manual_run=manual_run,
            created_by=created_by,
            run_id=run_id,
        )
        try:
            service = ClusterStatusSyncService()
            alert_event_service = EmailAlertEventService()
            mysql_clusters = service.list_enabled_mysql_clusters()
            sqlserver_clusters = service.list_enabled_sqlserver_clusters()
            totals = _ClusterStatusTotals(
                mysql_clusters_total=len(mysql_clusters),
                sqlserver_clusters_total=len(sqlserver_clusters),
            )
            _init_items(
                task_runs_service=task_runs_service,
                run_id=resolved_run_id,
                mysql_clusters=mysql_clusters,
                sqlserver_clusters=sqlserver_clusters,
            )
            for cluster in mysql_clusters:
                item_key = str(cluster.id)
                task_runs_service.start_item(resolved_run_id, item_type="mysql_cluster", item_key=item_key)
                db.session.commit()
                try:
                    result = service.sync_mysql_cluster(int(cluster.id))
                except Exception as exc:
                    db.session.rollback()
                    sync_logger.exception(
                        "MySQL 群集同步状态检测异常",
                        module="cluster_status_sync",
                        operation="sync_cluster_status",
                        run_id=resolved_run_id,
                        cluster_id=int(cluster.id),
                        cluster_name=str(cluster.name),
                        error=str(exc),
                    )
                    _record_cluster_exception(
                        task_runs_service=task_runs_service,
                        run_id=resolved_run_id,
                        item_type="mysql_cluster",
                        cluster_id=int(cluster.id),
                        cluster_name=str(cluster.name),
                        exc=exc,
                        totals=totals,
                        alert_event_service=alert_event_service,
                    )
                    continue
                _record_result(
                    task_runs_service=task_runs_service,
                    run_id=resolved_run_id,
                    item_type="mysql_cluster",
                    cluster_id=int(cluster.id),
                    cluster_name=str(cluster.name),
                    result=result,
                    totals=totals,
                    alert_event_service=alert_event_service,
                )
            for cluster in sqlserver_clusters:
                item_key = str(cluster.id)
                task_runs_service.start_item(resolved_run_id, item_type="sqlserver_cluster", item_key=item_key)
                db.session.commit()
                try:
                    result = service.sync_sqlserver_cluster(int(cluster.id))
                except Exception as exc:
                    db.session.rollback()
                    sync_logger.exception(
                        "SQL Server 群集同步状态检测异常",
                        module="cluster_status_sync",
                        operation="sync_cluster_status",
                        run_id=resolved_run_id,
                        cluster_id=int(cluster.id),
                        cluster_name=str(cluster.name),
                        error=str(exc),
                    )
                    _record_cluster_exception(
                        task_runs_service=task_runs_service,
                        run_id=resolved_run_id,
                        item_type="sqlserver_cluster",
                        cluster_id=int(cluster.id),
                        cluster_name=str(cluster.name),
                        exc=exc,
                        totals=totals,
                        alert_event_service=alert_event_service,
                    )
                    continue
                _record_result(
                    task_runs_service=task_runs_service,
                    run_id=resolved_run_id,
                    item_type="sqlserver_cluster",
                    cluster_id=int(cluster.id),
                    cluster_name=str(cluster.name),
                    result=result,
                    totals=totals,
                    alert_event_service=alert_event_service,
                )
            _finalize_run(task_runs_service, resolved_run_id, totals)
            sync_logger.info(
                "群集同步状态检测完成",
                module="cluster_status_sync",
                operation="sync_cluster_status",
                run_id=resolved_run_id,
                clusters_failed=totals.clusters_failed,
                abnormal_database_count=totals.abnormal_database_count,
                abnormal_replica_count=totals.abnormal_replica_count,
            )
        except CLUSTER_STATUS_TASK_EXCEPTIONS as exc:
            db.session.rollback()
            _fail_run(task_runs_service, resolved_run_id, exc)
            sync_logger.exception(
                "群集同步状态检测失败",
                module="cluster_status_sync",
                operation="sync_cluster_status",
                run_id=resolved_run_id,
                error=str(exc),
            )
        except Exception as exc:
            db.session.rollback()
            _fail_run(task_runs_service, resolved_run_id, exc)
            sync_logger.exception(
                "群集同步状态检测失败(未分类)",
                module="cluster_status_sync",
                operation="sync_cluster_status",
                run_id=resolved_run_id,
                error=str(exc),
            )
