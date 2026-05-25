"""MySQL 群集管理 Service."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, cast

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement

from app import db
from app.core.constants import DatabaseType
from app.core.exceptions import ConflictError, DatabaseError, ExternalServiceError, NotFoundError, ValidationError
from app.core.types import SyncConnection
from app.models.instance import Instance
from app.models.mysql_cluster import MySQLCluster, MySQLClusterInstance
from app.schemas.mysql_clusters import (
    MySQLClusterCreatePayload,
    MySQLClusterInstancesPayload,
    MySQLClusterListQuery,
    MySQLClusterUpdatePayload,
)
from app.schemas.validation import validate_or_raise
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

_REPLICA_STATUS_QUERY = "SHOW REPLICA STATUS"
_SLAVE_STATUS_QUERY = "SHOW SLAVE STATUS"
_READ_ONLY_QUERY = "SELECT @@global.read_only AS read_only, @@global.super_read_only AS super_read_only"


class _ConnectionFactoryProtocol(Protocol):
    def create_connection(self, instance: Instance) -> SyncConnection | None: ...


class MySQLClusterManagementService:
    """MySQL 群集、实例绑定与传统 replication 拓扑检测服务."""

    def __init__(self, *, connection_factory: _ConnectionFactoryProtocol | None = None) -> None:
        self._connection_factory = connection_factory or ConnectionFactory

    def list_clusters(self, query_params: MySQLClusterListQuery) -> dict[str, Any]:
        clusters, total, pages = self._list_clusters(query_params)
        return {
            "items": [self._serialize_cluster_summary(cluster) for cluster in clusters],
            "total": total,
            "page": query_params.page,
            "pages": pages,
            "limit": query_params.limit,
        }

    def get_detail(self, cluster_id: int) -> dict[str, Any]:
        cluster = self._get_cluster_or_error(cluster_id)
        bindings = self._list_bindings_for_cluster(cluster.id)
        return {
            "cluster": self._serialize_cluster_summary(cluster),
            "instances": [self._serialize_bound_instance(binding) for binding in bindings],
        }

    def create_cluster(self, payload: object | None, *, operator_id: int | None = None) -> dict[str, Any]:
        parsed = validate_or_raise(MySQLClusterCreatePayload, parse_payload(payload))
        self._ensure_cluster_name_unique(parsed.name, resource=None)
        cluster = MySQLCluster()
        cluster.name = parsed.name
        cluster.topology_type = parsed.topology_type
        cluster.description = parsed.description or ""
        cluster.is_enabled = parsed.is_enabled
        try:
            db.session.add(cluster)
            db.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseError("创建 MySQL 群集失败,请稍后重试", extra={"exception": str(exc)}) from exc
        log_info(
            "创建 MySQL 群集",
            module="mysql_clusters",
            user_id=operator_id,
            cluster_id=cluster.id,
            cluster_name=cluster.name,
        )
        return self._serialize_cluster_summary(cluster)

    def update_cluster(
        self,
        cluster_id: int,
        payload: object | None,
        *,
        operator_id: int | None = None,
    ) -> dict[str, Any]:
        cluster = self._get_cluster_or_error(cluster_id)
        parsed = validate_or_raise(MySQLClusterUpdatePayload, parse_payload(payload))
        if parsed.name is not None:
            self._ensure_cluster_name_unique(parsed.name, resource=cluster)
            cluster.name = parsed.name
        if parsed.topology_type is not None:
            cluster.topology_type = parsed.topology_type
        if "description" in parsed.model_fields_set:
            cluster.description = parsed.description or ""
        if parsed.is_enabled is not None:
            cluster.is_enabled = parsed.is_enabled
        try:
            db.session.add(cluster)
            db.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseError("更新 MySQL 群集失败,请稍后重试", extra={"exception": str(exc)}) from exc
        log_info(
            "更新 MySQL 群集",
            module="mysql_clusters",
            user_id=operator_id,
            cluster_id=cluster.id,
            cluster_name=cluster.name,
            is_enabled=cluster.is_enabled,
        )
        return self._serialize_cluster_summary(cluster)

    def replace_instances(
        self,
        cluster_id: int,
        payload: object | None,
        *,
        operator_id: int | None = None,
    ) -> dict[str, Any]:
        cluster = self._get_cluster_or_error(cluster_id)
        parsed = validate_or_raise(MySQLClusterInstancesPayload, parse_payload(payload, list_fields=["instance_ids"]))
        instance_ids = list(parsed.instance_ids)
        instances = self._validate_mysql_instances(instance_ids)
        self._ensure_instances_not_bound_elsewhere(instance_ids, cluster)
        try:
            MySQLClusterInstance.query.filter(MySQLClusterInstance.cluster_id == cluster.id).delete(
                synchronize_session=False,
            )
            for instance_id in instance_ids:
                binding = MySQLClusterInstance()
                binding.cluster_id = cluster.id
                binding.instance_id = instance_id
                db.session.add(binding)
            db.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseError("绑定 MySQL 实例失败,请稍后重试", extra={"exception": str(exc)}) from exc
        log_info(
            "更新 MySQL 群集实例绑定",
            module="mysql_clusters",
            user_id=operator_id,
            cluster_id=cluster.id,
            cluster_name=cluster.name,
            instance_count=len(instance_ids),
        )
        instance_map = {instance.id: instance for instance in instances}
        return {
            "cluster": self._serialize_cluster_summary(cluster),
            "instances": [
                self._serialize_instance(instance_map[instance_id])
                for instance_id in instance_ids
                if instance_id in instance_map
            ],
        }

    def sync_topology(self, cluster_id: int, *, operator_id: int | None = None) -> dict[str, Any]:
        cluster = self._get_cluster_or_error(cluster_id)
        bindings = self._list_bindings_for_cluster(cluster.id)
        if not bindings:
            raise ValidationError("请先绑定 MySQL 实例后再同步主从拓扑")

        now = time_utils.now()
        items: list[dict[str, Any]] = []
        failed = 0
        abnormal = 0
        for binding in bindings:
            instance = cast(Instance | None, binding.instance)
            if instance is None:
                continue
            try:
                detected = self._detect_instance_topology(instance)
                self._apply_detection(binding, detected, now)
            except (RuntimeError, ValueError, LookupError, ConnectionError, TimeoutError, OSError) as exc:
                failed += 1
                detected = {
                    "replication_role": "unknown",
                    "replication_status": "failed",
                    "last_error": str(exc),
                }
                self._apply_detection(binding, detected, now)
            if binding.replication_status not in {"healthy"}:
                abnormal += 1
            items.append(self._serialize_bound_instance(binding))

        cluster.last_topology_sync_at = now
        cluster.last_topology_sync_status = "failed" if failed == len(items) and items else "completed"
        cluster.last_error = f"{failed} 个实例检测失败" if failed else None
        db.session.add(cluster)
        db.session.flush()
        log_info(
            "同步 MySQL 主从拓扑",
            module="cluster_status_sync",
            user_id=operator_id,
            cluster_id=cluster.id,
            cluster_name=cluster.name,
            instance_count=len(items),
            failed=failed,
            abnormal=abnormal,
        )
        return {
            "cluster_id": cluster.id,
            "status": cluster.last_topology_sync_status,
            "instances_total": len(items),
            "instances_failed": failed,
            "abnormal_replica_count": abnormal,
            "abnormal_database_count": 0,
            "items": items,
        }

    def list_mysql_instance_options(self) -> list[dict[str, Any]]:
        instances = (
            Instance.query.filter(
                func.lower(Instance.db_type) == DatabaseType.MYSQL,
                Instance.deleted_at.is_(None),
            )
            .order_by(Instance.name.asc())
            .all()
        )
        return [self._serialize_instance(instance) for instance in instances]

    @staticmethod
    def _get_cluster_or_error(cluster_id: int) -> MySQLCluster:
        cluster = cast(MySQLCluster | None, MySQLCluster.query.get(cluster_id))
        if cluster is None:
            raise NotFoundError("MySQL 群集不存在", extra={"cluster_id": cluster_id})
        return cluster

    @staticmethod
    def _list_bindings_for_cluster(cluster_id: int) -> list[MySQLClusterInstance]:
        return (
            MySQLClusterInstance.query.filter(MySQLClusterInstance.cluster_id == cluster_id)
            .order_by(MySQLClusterInstance.created_at.asc())
            .all()
        )

    @staticmethod
    def _ensure_cluster_name_unique(name: str, *, resource: MySQLCluster | None) -> None:
        query = MySQLCluster.query.filter(MySQLCluster.name == name.strip())
        if resource is not None:
            query = query.filter(MySQLCluster.id != resource.id)
        if query.first() is not None:
            raise ValidationError("MySQL 群集名称已存在,请使用其他名称")

    @staticmethod
    def _list_clusters(query_params: MySQLClusterListQuery) -> tuple[list[MySQLCluster], int, int]:
        query = cast(Query[MySQLCluster], MySQLCluster.query)
        normalized_search = query_params.search.strip()
        if normalized_search:
            query = query.filter(
                or_(
                    MySQLCluster.name.contains(normalized_search),
                    MySQLCluster.description.contains(normalized_search),
                ),
            )

        enabled_column = cast(ColumnElement[bool], MySQLCluster.is_enabled)
        if query_params.status == "active":
            query = query.filter(enabled_column.is_(True))
        elif query_params.status == "inactive":
            query = query.filter(enabled_column.is_(False))

        sortable_fields: dict[str, ColumnElement[Any]] = {
            "id": cast(ColumnElement[Any], MySQLCluster.id),
            "name": cast(ColumnElement[Any], MySQLCluster.name),
            "is_enabled": cast(ColumnElement[Any], MySQLCluster.is_enabled),
            "created_at": cast(ColumnElement[Any], MySQLCluster.created_at),
            "updated_at": cast(ColumnElement[Any], MySQLCluster.updated_at),
        }
        sort_field = query_params.sort_field if query_params.sort_field in sortable_fields else "id"
        column = sortable_fields[sort_field]
        query = query.order_by(column.asc() if query_params.sort_order == "asc" else column.desc())
        pagination = cast(Any, query).paginate(page=query_params.page, per_page=query_params.limit, error_out=False)
        return cast(list[MySQLCluster], pagination.items), int(pagination.total), int(pagination.pages)

    @staticmethod
    def _validate_mysql_instances(instance_ids: list[int]) -> list[Instance]:
        if not instance_ids:
            return []
        instances = (
            Instance.query.filter(
                Instance.id.in_(instance_ids),
                func.lower(Instance.db_type) == DatabaseType.MYSQL,
                Instance.deleted_at.is_(None),
            )
            .order_by(Instance.name.asc())
            .all()
        )
        found_ids = {int(instance.id) for instance in instances}
        missing = [instance_id for instance_id in instance_ids if instance_id not in found_ids]
        if missing:
            raise ValidationError("只能绑定未删除的 MySQL 实例", extra={"invalid_instance_ids": missing})
        return cast(list[Instance], instances)

    @staticmethod
    def _ensure_instances_not_bound_elsewhere(instance_ids: list[int], cluster: MySQLCluster) -> None:
        if not instance_ids:
            return
        bindings = MySQLClusterInstance.query.filter(MySQLClusterInstance.instance_id.in_(instance_ids)).all()
        for binding in bindings:
            if binding.cluster_id == cluster.id:
                continue
            bound_cluster = binding.cluster
            bound_name = bound_cluster.name if bound_cluster else str(binding.cluster_id)
            raise ConflictError(
                f"MySQL 实例 {binding.instance_id} 已绑定到群集 {bound_name}",
                extra={"instance_id": binding.instance_id, "cluster_id": binding.cluster_id},
            )

    def _detect_instance_topology(self, instance: Instance) -> dict[str, Any]:
        connection = self._connection_factory.create_connection(instance)
        if connection is None:
            raise ExternalServiceError("无法创建 MySQL 连接", extra={"instance_id": instance.id})
        try:
            if not connection.connect():
                raise ExternalServiceError("无法连接 MySQL 实例", extra={"instance_id": instance.id})
            try:
                rows = self._execute_rows(connection, _REPLICA_STATUS_QUERY)
            except (RuntimeError, ValueError, LookupError, ConnectionError, TimeoutError, OSError):
                rows = []
            if rows:
                return self._normalize_replica_status(rows[0], new_names=True)
            try:
                rows = self._execute_rows(connection, _SLAVE_STATUS_QUERY)
            except (RuntimeError, ValueError, LookupError, ConnectionError, TimeoutError, OSError):
                rows = []
            if rows:
                return self._normalize_replica_status(rows[0], new_names=False)
            return self._detect_non_replica(connection)
        finally:
            connection.disconnect()

    @staticmethod
    def _execute_rows(connection: SyncConnection, query: str) -> list[Any]:
        dict_query = getattr(connection, "execute_dict_query", None)
        if callable(dict_query):
            return cast(list[Any], list(cast(Any, dict_query)(query)))
        return list(connection.execute_query(query))

    @staticmethod
    def _normalize_replica_status(row: Any, *, new_names: bool) -> dict[str, Any]:
        mapping = MySQLClusterManagementService._row_to_mapping(row)
        source_host = mapping.get("Source_Host" if new_names else "Master_Host")
        source_port = mapping.get("Source_Port" if new_names else "Master_Port")
        io_running = str(mapping.get("Replica_IO_Running" if new_names else "Slave_IO_Running") or "").strip()
        sql_running = str(mapping.get("Replica_SQL_Running" if new_names else "Slave_SQL_Running") or "").strip()
        seconds_behind = mapping.get("Seconds_Behind_Source" if new_names else "Seconds_Behind_Master")
        last_error = (
            mapping.get("Last_SQL_Error")
            or mapping.get("Last_IO_Error")
            or mapping.get("Last_Error")
        )
        healthy = io_running.lower() == "yes" and sql_running.lower() == "yes"
        return {
            "replication_role": "replica",
            "replication_status": "healthy" if healthy else "unhealthy",
            "source_host": str(source_host).strip() if source_host is not None else None,
            "source_port": MySQLClusterManagementService._optional_int(source_port),
            "io_running": io_running or None,
            "sql_running": sql_running or None,
            "seconds_behind_source": MySQLClusterManagementService._optional_int(seconds_behind),
            "last_error": str(last_error).strip() if last_error else None,
        }

    @staticmethod
    def _detect_non_replica(connection: SyncConnection) -> dict[str, Any]:
        rows = list(connection.execute_query(_READ_ONLY_QUERY))
        read_only = None
        super_read_only = None
        if rows:
            row = rows[0]
            if isinstance(row, Mapping):
                read_only = MySQLClusterManagementService._as_bool(row.get("read_only"))
                super_read_only = MySQLClusterManagementService._as_bool(row.get("super_read_only"))
            elif isinstance(row, Sequence) and not isinstance(row, str):
                values = list(row)
                read_only = MySQLClusterManagementService._as_bool(values[0]) if values else None
                super_read_only = MySQLClusterManagementService._as_bool(values[1]) if len(values) > 1 else None
        role = "unknown" if read_only or super_read_only else "primary"
        return {
            "replication_role": role,
            "replication_status": "healthy" if role == "primary" else "unknown",
            "read_only": read_only,
            "super_read_only": super_read_only,
        }

    @staticmethod
    def _row_to_mapping(row: Any) -> Mapping[str, Any]:
        if isinstance(row, Mapping):
            return row
        raise ValueError("MySQL replication status row must include column names")

    @staticmethod
    def _as_bool(value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        return str(value).strip().lower() in {"1", "on", "true", "yes"}

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value in {None, ""}:
            return None
        return int(value)

    @staticmethod
    def _apply_detection(binding: MySQLClusterInstance, detected: Mapping[str, Any], checked_at: Any) -> None:
        binding.replication_role = str(detected.get("replication_role") or "unknown")
        binding.replication_status = str(detected.get("replication_status") or "unknown")
        binding.source_host = cast(str | None, detected.get("source_host"))
        binding.source_port = cast(int | None, detected.get("source_port"))
        binding.io_running = cast(str | None, detected.get("io_running"))
        binding.sql_running = cast(str | None, detected.get("sql_running"))
        binding.seconds_behind_source = cast(int | None, detected.get("seconds_behind_source"))
        binding.read_only = cast(bool | None, detected.get("read_only"))
        binding.super_read_only = cast(bool | None, detected.get("super_read_only"))
        binding.last_error = cast(str | None, detected.get("last_error"))
        binding.last_checked_at = checked_at
        db.session.add(binding)

    def _serialize_cluster_summary(self, cluster: MySQLCluster) -> dict[str, Any]:
        bindings = self._list_bindings_for_cluster(cluster.id)
        payload = cluster.to_dict()
        unhealthy_count = sum(1 for binding in bindings if binding.replication_status not in {"healthy"})
        payload.update(
            {
                "instance_count": len(bindings),
                "bound_instance_ids": [
                    int(binding.instance_id)
                    for binding in bindings
                    if binding.instance_id is not None
                ],
                "abnormal_replica_count": unhealthy_count,
            },
        )
        return payload

    @staticmethod
    def _serialize_instance(instance: Instance | None) -> dict[str, Any]:
        if instance is None:
            return {}
        return {
            "id": instance.id,
            "name": instance.name,
            "db_type": instance.db_type,
            "host": instance.host,
            "port": instance.port,
            "is_active": bool(instance.is_active),
            "deleted_at": instance.deleted_at.isoformat() if instance.deleted_at else None,
        }

    def _serialize_bound_instance(self, binding: MySQLClusterInstance) -> dict[str, Any]:
        payload = self._serialize_instance(cast(Instance | None, binding.instance))
        payload.update(binding.to_dict())
        return payload
