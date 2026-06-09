"""群集同步异常检测结果 contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict, cast


class ClusterRiskKwargs(TypedDict):
    rule_key: str
    category: str
    severity: str
    label: str
    detail: str
    occurred_at: datetime | None
    target_url: str | None


@dataclass(slots=True)
class ClusterStatusDetectionResult:
    """包装群集同步 result dict，统一任务、告警消费口径."""

    cluster_type: str
    cluster_id: int
    cluster_name: str
    run_id: str
    result: dict[str, Any]

    @classmethod
    def from_result(
        cls,
        *,
        cluster_type: str,
        cluster_id: int,
        cluster_name: str,
        run_id: str,
        result: dict[str, Any],
    ) -> ClusterStatusDetectionResult:
        return cls(
            cluster_type=cluster_type,
            cluster_id=int(cluster_id),
            cluster_name=cluster_name,
            run_id=run_id,
            result=result,
        )

    @property
    def status(self) -> str:
        return str(self.result.get("status") or "unknown")

    @property
    def error_message(self) -> object:
        return self.result.get("error_message")

    @property
    def abnormal_database_count(self) -> int:
        return int(self.result.get("abnormal_database_count", 0) or 0)

    @property
    def abnormal_replica_count(self) -> int:
        return int(self.result.get("abnormal_replica_count", 0) or 0)

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_abnormal(self) -> bool:
        return self.is_failed or self.abnormal_database_count > 0 or self.abnormal_replica_count > 0

    @property
    def alert_dedupe_key(self) -> str:
        return f"{self.cluster_type}:{self.cluster_id}"

    def task_metrics(self) -> dict[str, int]:
        return {
            "abnormal_database_count": self.abnormal_database_count,
            "abnormal_replica_count": self.abnormal_replica_count,
        }

    def task_error_message(self) -> str:
        return str(self.result.get("error_message") or "群集同步状态检测失败")

    def alert_payload(self) -> dict[str, object]:
        return {
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "cluster_type": self.cluster_type,
            "status": self.status,
            "error_message": self.error_message,
            "abnormal_database_count": self.abnormal_database_count,
            "abnormal_replica_count": self.abnormal_replica_count,
            "run_id": self.run_id,
            "summary_text": self.summary_text(),
        }

    def summary_text(self) -> str:
        error_message = str(self.result.get("error_message") or "").strip()
        if self.is_failed and error_message:
            return error_message

        source_errors = self.result.get("source_errors")
        if isinstance(source_errors, list) and source_errors:
            return "; ".join(str(item) for item in source_errors if str(item).strip())

        item_summaries = self._build_mysql_cluster_item_summaries()
        item_summaries.extend(self._build_sqlserver_cluster_item_summaries())
        if item_summaries:
            return "; ".join(item_summaries[:5])
        return f"异常数据库 {self.abnormal_database_count} 个，异常副本 {self.abnormal_replica_count} 个"

    def to_details_json(self) -> dict[str, Any]:
        return self.result

    def _build_mysql_cluster_item_summaries(self) -> list[str]:
        summaries: list[str] = []
        items = self.result.get("items")
        if not isinstance(items, list):
            return summaries
        for item in items:
            if not isinstance(item, dict):
                continue
            if "replication_status" not in item:
                continue
            status = str(item.get("replication_status") or "").strip()
            if status == "healthy":
                continue
            name = str(item.get("name") or item.get("instance_name") or item.get("instance_id") or "unknown").strip()
            reason = str(item.get("last_error") or status or "状态异常").strip()
            lag = item.get("seconds_behind_source")
            if lag not in {None, ""}:
                reason = f"{reason}, lag={lag}s"
            summaries.append(f"{name}: {reason}")
        return summaries

    def _build_sqlserver_cluster_item_summaries(self) -> list[str]:
        summaries: list[str] = []
        for collection_name in ("items", "replicas"):
            rows = self.result.get(collection_name)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict) or not bool(row.get("is_abnormal")):
                    continue
                replica = str(row.get("replica_server_name") or "unknown").strip()
                database = str(row.get("database_name") or "").strip()
                name = f"{replica}/{database}" if database else replica
                reason = str(row.get("error_summary") or row.get("synchronization_health_desc") or "状态异常").strip()
                summaries.append(f"{name}: {reason}")
        return summaries


def build_failed_cluster_status_result(
    *,
    cluster_id: int,
    error_message: str | None,
) -> dict[str, Any]:
    return {
        "cluster_id": cluster_id,
        "status": "failed",
        "error_message": error_message or "群集同步状态检测失败",
        "abnormal_database_count": 0,
        "abnormal_replica_count": 0,
        "items": [],
        "replicas": [],
    }


@dataclass(frozen=True, slots=True)
class ClusterAbnormalIssue:
    """风险中心可消费的群集异常 issue."""

    instance_id: int
    detail: str
    occurred_at: datetime | None

    @classmethod
    def mysql_replication(
        cls,
        *,
        instance_id: int,
        cluster_name: str,
        detail_suffix: str,
        occurred_at: datetime | None,
    ) -> ClusterAbnormalIssue:
        return cls(
            instance_id=int(instance_id),
            detail=f"MySQL 群集 {cluster_name} 副节点复制异常: {detail_suffix}",
            occurred_at=occurred_at,
        )

    @classmethod
    def sqlserver_replica(
        cls,
        *,
        instance_id: int,
        cluster_name: str,
        row: object,
        occurred_at: datetime | None = None,
    ) -> ClusterAbnormalIssue:
        ag_name = str(getattr(row, "ag_name", "") or "")
        replica_name = str(getattr(row, "replica_server_name", "") or "").strip()
        error_summary = getattr(row, "error_summary", None) or "副本状态异常"
        return cls(
            instance_id=int(instance_id),
            detail=f"SQL Server 群集 {cluster_name} AG {ag_name} 副本 {replica_name} 异常: {error_summary}",
            occurred_at=occurred_at
            if occurred_at is not None
            else cast("datetime | None", getattr(row, "last_checked_at", None)),
        )

    @classmethod
    def sqlserver_database(
        cls,
        *,
        instance_id: int,
        cluster_name: str,
        row: object,
        occurred_at: datetime | None = None,
    ) -> ClusterAbnormalIssue:
        ag_name = str(getattr(row, "ag_name", "") or "")
        database_name = str(getattr(row, "database_name", "") or "")
        error_summary = getattr(row, "error_summary", None) or "数据库同步状态异常"
        return cls(
            instance_id=int(instance_id),
            detail=f"SQL Server 群集 {cluster_name} AG {ag_name} 数据库 {database_name} 同步异常: {error_summary}",
            occurred_at=occurred_at
            if occurred_at is not None
            else cast("datetime | None", getattr(row, "last_checked_at", None)),
        )

    def to_risk_kwargs(self) -> ClusterRiskKwargs:
        return {
            "rule_key": "cluster_abnormal",
            "category": "cluster",
            "severity": "medium",
            "label": "群集异常",
            "detail": self.detail,
            "occurred_at": self.occurred_at,
            "target_url": "/cluster/",
        }


def is_sqlserver_secondary_replica(row: object) -> bool:
    return not bool(getattr(row, "is_primary", False)) and str(getattr(row, "role_desc", "") or "").upper() != "PRIMARY"


def sqlserver_replica_scope(row: object) -> tuple[int, str, str]:
    return (
        int(getattr(row, "cluster_id", 0) or 0),
        str(getattr(row, "ag_name", "") or ""),
        str(getattr(row, "replica_server_name", "") or "").strip().lower(),
    )
