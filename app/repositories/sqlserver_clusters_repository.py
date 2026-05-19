"""SQL Server 群集管理 Repository."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func, or_
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement

from app import db
from app.models.instance import Instance
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.schemas.sqlserver_clusters import SQLServerClusterListQuery


class SQLServerClustersRepository:
    """SQL Server 群集查询与写入仓储."""

    def get_cluster(self, cluster_id: int) -> SQLServerCluster | None:
        """按 ID 获取群集."""
        return cast("SQLServerCluster | None", SQLServerCluster.query.get(cluster_id))

    def get_availability_group(self, ag_id: int) -> SQLServerAvailabilityGroup | None:
        """按 ID 获取 AG."""
        return cast("SQLServerAvailabilityGroup | None", SQLServerAvailabilityGroup.query.get(ag_id))

    def exists_cluster_name(self, name: str, *, exclude_cluster_id: int | None = None) -> bool:
        """判断群集名称是否已存在."""
        query = SQLServerCluster.query.filter(SQLServerCluster.name == name.strip())
        if exclude_cluster_id is not None:
            query = query.filter(SQLServerCluster.id != exclude_cluster_id)
        return query.first() is not None

    def exists_ag_name(self, cluster_id: int, name: str, *, exclude_ag_id: int | None = None) -> bool:
        """判断同群集 AG 名称是否已存在."""
        query = SQLServerAvailabilityGroup.query.filter(
            SQLServerAvailabilityGroup.cluster_id == cluster_id,
            SQLServerAvailabilityGroup.name == name.strip(),
        )
        if exclude_ag_id is not None:
            query = query.filter(SQLServerAvailabilityGroup.id != exclude_ag_id)
        return query.first() is not None

    def add(self, model: object) -> object:
        """写入并 flush."""
        db.session.add(model)
        db.session.flush()
        return model

    def list_clusters(self, query_params: SQLServerClusterListQuery) -> tuple[list[SQLServerCluster], int, int]:
        """分页查询群集."""
        query = cast("Query[SQLServerCluster]", SQLServerCluster.query)
        normalized_search = query_params.search.strip()
        if normalized_search:
            query = query.filter(
                or_(
                    SQLServerCluster.name.contains(normalized_search),
                    SQLServerCluster.description.contains(normalized_search),
                ),
            )

        enabled_column = cast(ColumnElement[bool], SQLServerCluster.is_enabled)
        if query_params.status == "active":
            query = query.filter(enabled_column.is_(True))
        elif query_params.status == "inactive":
            query = query.filter(enabled_column.is_(False))

        query = self._apply_sorting(query, query_params)
        pagination = cast(Any, query).paginate(
            page=query_params.page,
            per_page=query_params.limit,
            error_out=False,
        )
        return cast("list[SQLServerCluster]", pagination.items), int(pagination.total), int(pagination.pages)

    @staticmethod
    def list_bindings_for_cluster(cluster_id: int) -> list[SQLServerClusterInstance]:
        """查询指定群集的实例绑定."""
        return (
            SQLServerClusterInstance.query.filter(SQLServerClusterInstance.cluster_id == cluster_id)
            .order_by(SQLServerClusterInstance.created_at.asc())
            .all()
        )

    @staticmethod
    def list_ag_for_cluster(cluster_id: int) -> list[SQLServerAvailabilityGroup]:
        """查询指定群集的 AG 配置."""
        return (
            SQLServerAvailabilityGroup.query.filter(SQLServerAvailabilityGroup.cluster_id == cluster_id)
            .order_by(SQLServerAvailabilityGroup.name.asc())
            .all()
        )

    @staticmethod
    def list_existing_sqlserver_instances(instance_ids: list[int]) -> list[Instance]:
        """按 ID 查询未删除 SQL Server 实例."""
        if not instance_ids:
            return []
        return (
            Instance.query.filter(
                Instance.id.in_(instance_ids),
                func.lower(Instance.db_type) == "sqlserver",
                Instance.deleted_at.is_(None),
            )
            .order_by(Instance.name.asc())
            .all()
        )

    @staticmethod
    def list_sqlserver_instance_options() -> list[Instance]:
        """查询未删除 SQL Server 实例，用于页面绑定候选."""
        return (
            Instance.query.filter(
                func.lower(Instance.db_type) == "sqlserver",
                Instance.deleted_at.is_(None),
            )
            .order_by(Instance.name.asc())
            .all()
        )

    @staticmethod
    def find_bindings_by_instance_ids(instance_ids: list[int]) -> list[SQLServerClusterInstance]:
        """按实例 ID 查询已有绑定."""
        if not instance_ids:
            return []
        return SQLServerClusterInstance.query.filter(SQLServerClusterInstance.instance_id.in_(instance_ids)).all()

    @staticmethod
    def replace_bindings(cluster_id: int, instance_ids: list[int]) -> None:
        """整体替换群集实例绑定."""
        SQLServerClusterInstance.query.filter(SQLServerClusterInstance.cluster_id == cluster_id).delete(
            synchronize_session=False,
        )
        for instance_id in instance_ids:
            db.session.add(SQLServerClusterInstance(cluster_id=cluster_id, instance_id=instance_id))
        db.session.flush()

    @staticmethod
    def _apply_sorting(query: Query[SQLServerCluster], filters: SQLServerClusterListQuery) -> Query[SQLServerCluster]:
        sortable_fields: dict[str, ColumnElement[Any]] = {
            "id": cast(ColumnElement[Any], SQLServerCluster.id),
            "name": cast(ColumnElement[Any], SQLServerCluster.name),
            "is_enabled": cast(ColumnElement[Any], SQLServerCluster.is_enabled),
            "created_at": cast(ColumnElement[Any], SQLServerCluster.created_at),
            "updated_at": cast(ColumnElement[Any], SQLServerCluster.updated_at),
        }
        sort_field = filters.sort_field if filters.sort_field in sortable_fields else "id"
        column = sortable_fields[sort_field]
        return query.order_by(column.asc() if filters.sort_order == "asc" else column.desc())
