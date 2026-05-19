"""SQL Server 群集管理 Service."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import ConflictError, DatabaseError, NotFoundError, ValidationError
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster
from app.repositories.sqlserver_clusters_repository import SQLServerClustersRepository
from app.schemas.sqlserver_clusters import (
    SQLServerAvailabilityGroupCreatePayload,
    SQLServerAvailabilityGroupUpdatePayload,
    SQLServerClusterCreatePayload,
    SQLServerClusterInstancesPayload,
    SQLServerClusterListQuery,
    SQLServerClusterUpdatePayload,
)
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info


class SQLServerClusterManagementService:
    """SQL Server 群集、实例绑定与 AG 配置编排服务."""

    def __init__(self, repository: SQLServerClustersRepository | None = None) -> None:
        self._repository = repository or SQLServerClustersRepository()

    def list_clusters(self, query: SQLServerClusterListQuery) -> dict[str, Any]:
        """分页列出群集."""
        clusters, total, pages = self._repository.list_clusters(query)
        return {
            "items": [self._serialize_cluster_summary(cluster) for cluster in clusters],
            "total": total,
            "page": query.page,
            "pages": pages,
            "limit": query.limit,
        }

    def get_detail(self, cluster_id: int) -> dict[str, Any]:
        """获取群集详情."""
        cluster = self._get_cluster_or_error(cluster_id)
        bindings = self._repository.list_bindings_for_cluster(cluster.id)
        ags = self._repository.list_ag_for_cluster(cluster.id)
        return {
            "cluster": self._serialize_cluster_summary(cluster),
            "instances": [self._serialize_instance(cast(Instance, binding.instance)) for binding in bindings],
            "availability_groups": [self._serialize_ag(ag) for ag in ags],
        }

    def create_cluster(self, payload: object | None, *, operator_id: int | None = None) -> dict[str, Any]:
        """创建群集."""
        parsed = validate_or_raise(SQLServerClusterCreatePayload, parse_payload(payload))
        self._ensure_cluster_name_unique(parsed.name, resource=None)
        cluster = SQLServerCluster(
            name=parsed.name,
            description=parsed.description or "",
            is_enabled=parsed.is_enabled,
        )
        try:
            self._repository.add(cluster)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("创建群集", exc), extra={"exception": str(exc)}) from exc
        log_info(
            "创建 SQL Server 群集",
            module="sqlserver_clusters",
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
        """更新群集基本信息."""
        cluster = self._get_cluster_or_error(cluster_id)
        parsed = validate_or_raise(SQLServerClusterUpdatePayload, parse_payload(payload))
        if parsed.name is not None:
            self._ensure_cluster_name_unique(parsed.name, resource=cluster)
            cluster.name = parsed.name
        if "description" in parsed.model_fields_set:
            cluster.description = parsed.description or ""
        if parsed.is_enabled is not None:
            cluster.is_enabled = parsed.is_enabled
        try:
            self._repository.add(cluster)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("更新群集", exc), extra={"exception": str(exc)}) from exc
        log_info(
            "更新 SQL Server 群集",
            module="sqlserver_clusters",
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
        """整体替换实例绑定."""
        cluster = self._get_cluster_or_error(cluster_id)
        parsed = validate_or_raise(SQLServerClusterInstancesPayload, parse_payload(payload, list_fields=["instance_ids"]))
        instance_ids = list(parsed.instance_ids)
        instances = self._validate_sqlserver_instances(instance_ids)
        self._ensure_instances_not_bound_elsewhere(instance_ids, cluster)
        try:
            self._repository.replace_bindings(cluster.id, instance_ids)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("绑定实例", exc), extra={"exception": str(exc)}) from exc
        log_info(
            "更新 SQL Server 群集实例绑定",
            module="sqlserver_clusters",
            user_id=operator_id,
            cluster_id=cluster.id,
            cluster_name=cluster.name,
            instance_count=len(instance_ids),
        )
        instance_map = {instance.id: instance for instance in instances}
        ordered_instances = [instance_map[instance_id] for instance_id in instance_ids if instance_id in instance_map]
        return {
            "cluster": self._serialize_cluster_summary(cluster),
            "instances": [self._serialize_instance(instance) for instance in ordered_instances],
        }

    def create_availability_group(
        self,
        cluster_id: int,
        payload: object | None,
        *,
        operator_id: int | None = None,
    ) -> dict[str, Any]:
        """新增 AG 配置."""
        cluster = self._get_cluster_or_error(cluster_id)
        parsed = validate_or_raise(SQLServerAvailabilityGroupCreatePayload, parse_payload(payload))
        self._ensure_ag_name_unique(cluster.id, parsed.name, resource=None)
        self._ensure_credential_exists(parsed.credential_id)
        ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name=parsed.name,
            listener_name=parsed.listener_name,
            listener_host=parsed.listener_host,
            listener_port=parsed.listener_port,
            credential_id=parsed.credential_id,
            connection_database=parsed.connection_database,
            contained_enabled=parsed.contained_enabled,
            is_enabled=parsed.is_enabled,
        )
        try:
            self._repository.add(ag)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("创建 AG", exc), extra={"exception": str(exc)}) from exc
        log_info(
            "创建 SQL Server AG 配置",
            module="sqlserver_clusters",
            user_id=operator_id,
            cluster_id=cluster.id,
            availability_group_id=ag.id,
            availability_group_name=ag.name,
        )
        return self._serialize_ag(ag)

    def update_availability_group(
        self,
        cluster_id: int,
        ag_id: int,
        payload: object | None,
        *,
        operator_id: int | None = None,
    ) -> dict[str, Any]:
        """更新 AG 配置."""
        cluster = self._get_cluster_or_error(cluster_id)
        ag = self._get_ag_or_error(ag_id)
        if ag.cluster_id != cluster.id:
            raise NotFoundError("AG 不存在", extra={"cluster_id": cluster.id, "availability_group_id": ag_id})
        parsed = validate_or_raise(SQLServerAvailabilityGroupUpdatePayload, parse_payload(payload))

        if parsed.name is not None:
            self._ensure_ag_name_unique(cluster.id, parsed.name, resource=ag)
            ag.name = parsed.name
        for field in ("listener_name", "listener_host", "listener_port", "credential_id", "connection_database"):
            if field in parsed.model_fields_set:
                setattr(ag, field, getattr(parsed, field))
        if "credential_id" in parsed.model_fields_set:
            self._ensure_credential_exists(parsed.credential_id)
        if parsed.contained_enabled is not None:
            ag.contained_enabled = parsed.contained_enabled
        if parsed.is_enabled is not None:
            ag.is_enabled = parsed.is_enabled

        try:
            self._repository.add(ag)
        except SQLAlchemyError as exc:
            raise DatabaseError(self._normalize_db_error("更新 AG", exc), extra={"exception": str(exc)}) from exc
        log_info(
            "更新 SQL Server AG 配置",
            module="sqlserver_clusters",
            user_id=operator_id,
            cluster_id=cluster.id,
            availability_group_id=ag.id,
            availability_group_name=ag.name,
            is_enabled=ag.is_enabled,
        )
        return self._serialize_ag(ag)

    def list_sqlserver_instance_options(self) -> list[dict[str, Any]]:
        """获取未删除 SQL Server 实例候选."""
        return [self._serialize_instance(instance) for instance in self._repository.list_sqlserver_instance_options()]

    def _get_cluster_or_error(self, cluster_id: int) -> SQLServerCluster:
        cluster = self._repository.get_cluster(cluster_id)
        if cluster is None:
            raise NotFoundError("群集不存在", extra={"cluster_id": cluster_id})
        return cluster

    def _get_ag_or_error(self, ag_id: int) -> SQLServerAvailabilityGroup:
        ag = self._repository.get_availability_group(ag_id)
        if ag is None:
            raise NotFoundError("AG 不存在", extra={"availability_group_id": ag_id})
        return ag

    def _ensure_cluster_name_unique(self, name: str, *, resource: SQLServerCluster | None) -> None:
        exclude_id = resource.id if resource else None
        if self._repository.exists_cluster_name(name, exclude_cluster_id=exclude_id):
            raise ValidationError("群集名称已存在,请使用其他名称")

    def _ensure_ag_name_unique(self, cluster_id: int, name: str, *, resource: SQLServerAvailabilityGroup | None) -> None:
        exclude_id = resource.id if resource else None
        if self._repository.exists_ag_name(cluster_id, name, exclude_ag_id=exclude_id):
            raise ValidationError("AG 名称已存在,请使用其他名称")

    @staticmethod
    def _ensure_credential_exists(credential_id: int | None) -> None:
        if credential_id is None:
            return
        if Credential.query.get(credential_id) is None:
            raise ValidationError("凭据不存在")

    def _validate_sqlserver_instances(self, instance_ids: list[int]) -> list[Instance]:
        if not instance_ids:
            return []
        instances = self._repository.list_existing_sqlserver_instances(instance_ids)
        found_ids = {int(instance.id) for instance in instances}
        missing = [instance_id for instance_id in instance_ids if instance_id not in found_ids]
        if missing:
            raise ValidationError(
                "只能绑定未删除的 SQL Server 实例",
                extra={"invalid_instance_ids": missing},
            )
        return instances

    def _ensure_instances_not_bound_elsewhere(self, instance_ids: list[int], cluster: SQLServerCluster) -> None:
        bindings = self._repository.find_bindings_by_instance_ids(instance_ids)
        for binding in bindings:
            if binding.cluster_id == cluster.id:
                continue
            bound_cluster = binding.cluster
            bound_name = bound_cluster.name if bound_cluster else str(binding.cluster_id)
            raise ConflictError(
                f"实例 {binding.instance_id} 已绑定到群集 {bound_name}",
                extra={"instance_id": binding.instance_id, "cluster_id": binding.cluster_id},
            )

    def _serialize_cluster_summary(self, cluster: SQLServerCluster) -> dict[str, Any]:
        bindings = self._repository.list_bindings_for_cluster(cluster.id)
        ags = self._repository.list_ag_for_cluster(cluster.id)
        latest = max((ag for ag in ags if ag.last_sync_at is not None), key=lambda ag: ag.last_sync_at, default=None)
        payload = cluster.to_dict()
        payload.update(
            {
                "instance_count": len(bindings),
                "availability_group_count": len(ags),
                "contained_ag_count": sum(1 for ag in ags if ag.contained_enabled),
                "last_ag_sync_status": latest.last_sync_status if latest else None,
                "last_ag_sync_at": latest.last_sync_at.isoformat() if latest and latest.last_sync_at else None,
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

    @staticmethod
    def _serialize_ag(ag: SQLServerAvailabilityGroup) -> dict[str, Any]:
        payload = ag.to_dict()
        payload["credential_name"] = ag.credential.name if ag.credential else None
        return payload

    @staticmethod
    def _normalize_db_error(action: str, error: Exception) -> str:
        lowered = str(error).lower()
        if "unique constraint failed" in lowered or "duplicate key value" in lowered:
            return "名称或绑定关系已存在"
        if "foreign key constraint" in lowered:
            return "关联资源不存在"
        return f"{action}失败,请稍后重试"
