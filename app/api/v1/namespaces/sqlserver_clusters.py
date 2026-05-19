"""SQL Server clusters namespace."""

from __future__ import annotations

from typing import Any, ClassVar, cast

from flask_login import current_user
from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource, get_raw_payload
from app.api.v1.resources.decorators import api_admin_required, api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.core.constants import HttpStatus
from app.core.constants.system_constants import SuccessMessages
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.schemas.sqlserver_clusters import SQLServerClusterListQuery
from app.schemas.validation import validate_or_raise
from app.services.sqlserver_clusters import SQLServerClusterManagementService
from app.utils.decorators import require_csrf

ns = Namespace("sqlserver-clusters", description="SQL Server 群集管理")

ErrorEnvelope = get_error_envelope_model(ns)

ClusterPayload = ns.model(
    "SQLServerClusterPayload",
    {
        "name": fields.String(required=True, description="群集名称"),
        "description": fields.String(required=False, description="描述"),
        "is_enabled": fields.Boolean(required=False, description="是否启用"),
    },
)

ClusterInstancesPayload = ns.model(
    "SQLServerClusterInstancesPayload",
    {
        "instance_ids": fields.List(fields.Integer, required=False, description="实例 ID 列表"),
    },
)

AvailabilityGroupPayload = ns.model(
    "SQLServerAvailabilityGroupPayload",
    {
        "name": fields.String(required=True, description="AG 名称"),
        "listener_name": fields.String(required=False, description="监听器名称"),
        "listener_host": fields.String(required=True, description="监听器 host"),
        "listener_port": fields.Integer(required=False, description="监听器端口"),
        "credential_id": fields.Integer(required=False, description="凭据 ID"),
        "connection_database": fields.String(required=False, description="连接数据库"),
        "contained_enabled": fields.Boolean(required=False, description="是否启用 contained"),
        "is_enabled": fields.Boolean(required=False, description="是否启用采集"),
    },
)

ClustersListData = ns.model(
    "SQLServerClustersListData",
    {
        "items": fields.List(fields.Raw),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
    },
)
ClustersListEnvelope = make_success_envelope_model(ns, "SQLServerClustersListEnvelope", ClustersListData)

ClusterDetailData = ns.model(
    "SQLServerClusterDetailData",
    {
        "cluster": fields.Raw,
        "instances": fields.List(fields.Raw),
        "availability_groups": fields.List(fields.Raw),
    },
)
ClusterDetailEnvelope = make_success_envelope_model(ns, "SQLServerClusterDetailEnvelope", ClusterDetailData)

ClusterWriteData = ns.model("SQLServerClusterWriteData", {"cluster": fields.Raw})
ClusterWriteEnvelope = make_success_envelope_model(ns, "SQLServerClusterWriteEnvelope", ClusterWriteData)

ClusterInstancesData = ns.model(
    "SQLServerClusterInstancesData",
    {
        "cluster": fields.Raw,
        "instances": fields.List(fields.Raw),
    },
)
ClusterInstancesEnvelope = make_success_envelope_model(ns, "SQLServerClusterInstancesEnvelope", ClusterInstancesData)

AvailabilityGroupData = ns.model("SQLServerAvailabilityGroupData", {"availability_group": fields.Raw})
AvailabilityGroupEnvelope = make_success_envelope_model(
    ns,
    "SQLServerAvailabilityGroupEnvelope",
    AvailabilityGroupData,
)

_clusters_list_query_parser = new_parser()
_clusters_list_query_parser.add_argument("page", type=int, default=1, location="args")
_clusters_list_query_parser.add_argument("limit", type=int, default=20, location="args")
_clusters_list_query_parser.add_argument("search", type=str, default="", location="args")
_clusters_list_query_parser.add_argument("status", type=str, default="", location="args")
_clusters_list_query_parser.add_argument("sort", type=str, default="id", location="args")
_clusters_list_query_parser.add_argument("order", type=str, default="desc", location="args")


@ns.route("")
class SQLServerClustersResource(BaseResource):
    """SQL Server 群集列表与创建资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", ClustersListEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.expect(_clusters_list_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取 SQL Server 群集列表."""
        parsed = cast("dict[str, object]", _clusters_list_query_parser.parse_args())
        query = validate_or_raise(SQLServerClusterListQuery, parsed)

        def _execute():
            data = SQLServerClusterManagementService().list_clusters(query)
            return self.success(data=data, message=SuccessMessages.OPERATION_SUCCESS)

        return self.safe_call(
            _execute,
            module="sqlserver_clusters",
            action="list_clusters",
            public_error="获取 SQL Server 群集列表失败",
            context={"search": query.search, "status": query.status, "page": query.page, "limit": query.limit},
        )

    @ns.expect(ClusterPayload, validate=False)
    @ns.response(201, "Created", ClusterWriteEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @api_admin_required
    @require_csrf
    def post(self):
        """创建 SQL Server 群集."""
        payload = cast(Any, get_raw_payload())
        operator_id = getattr(current_user, "id", None)

        def _execute():
            cluster = SQLServerClusterManagementService().create_cluster(payload, operator_id=operator_id)
            return self.success(
                data={"cluster": cluster},
                message=SuccessMessages.DATA_SAVED,
                status=HttpStatus.CREATED,
            )

        return self.safe_call(
            _execute,
            module="sqlserver_clusters",
            action="create_cluster",
            public_error="创建 SQL Server 群集失败",
            context={"cluster_name": payload.get("name") if isinstance(payload, dict) else None},
            expected_exceptions=(ValidationError,),
        )


@ns.route("/<int:cluster_id>")
class SQLServerClusterDetailResource(BaseResource):
    """SQL Server 群集详情与更新资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", ClusterDetailEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, cluster_id: int):
        """获取 SQL Server 群集详情."""

        def _execute():
            data = SQLServerClusterManagementService().get_detail(cluster_id)
            return self.success(data=data, message=SuccessMessages.OPERATION_SUCCESS)

        return self.safe_call(
            _execute,
            module="sqlserver_clusters",
            action="get_cluster_detail",
            public_error="获取 SQL Server 群集详情失败",
            context={"cluster_id": cluster_id},
            expected_exceptions=(NotFoundError,),
        )

    @ns.expect(ClusterPayload, validate=False)
    @ns.response(200, "OK", ClusterWriteEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @api_admin_required
    @require_csrf
    def patch(self, cluster_id: int):
        """更新 SQL Server 群集."""
        payload = cast(Any, get_raw_payload())
        operator_id = getattr(current_user, "id", None)

        def _execute():
            cluster = SQLServerClusterManagementService().update_cluster(
                cluster_id,
                payload,
                operator_id=operator_id,
            )
            return self.success(data={"cluster": cluster}, message=SuccessMessages.DATA_SAVED)

        return self.safe_call(
            _execute,
            module="sqlserver_clusters",
            action="update_cluster",
            public_error="更新 SQL Server 群集失败",
            context={"cluster_id": cluster_id},
            expected_exceptions=(NotFoundError, ValidationError),
        )


@ns.route("/<int:cluster_id>/instances")
class SQLServerClusterInstancesResource(BaseResource):
    """SQL Server 群集实例绑定资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.expect(ClusterInstancesPayload, validate=False)
    @ns.response(200, "OK", ClusterInstancesEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @api_admin_required
    @require_csrf
    def put(self, cluster_id: int):
        """整体替换 SQL Server 群集实例绑定."""
        payload = cast(Any, get_raw_payload())
        operator_id = getattr(current_user, "id", None)

        def _execute():
            data = SQLServerClusterManagementService().replace_instances(
                cluster_id,
                payload,
                operator_id=operator_id,
            )
            return self.success(data=data, message=SuccessMessages.DATA_SAVED)

        return self.safe_call(
            _execute,
            module="sqlserver_clusters",
            action="replace_cluster_instances",
            public_error="更新 SQL Server 群集实例绑定失败",
            context={"cluster_id": cluster_id},
            expected_exceptions=(ConflictError, NotFoundError, ValidationError),
        )


@ns.route("/<int:cluster_id>/availability-groups")
class SQLServerAvailabilityGroupsResource(BaseResource):
    """SQL Server AG 配置集合资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.expect(AvailabilityGroupPayload, validate=False)
    @ns.response(201, "Created", AvailabilityGroupEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @api_admin_required
    @require_csrf
    def post(self, cluster_id: int):
        """新增 SQL Server AG 配置."""
        payload = cast(Any, get_raw_payload())
        operator_id = getattr(current_user, "id", None)

        def _execute():
            ag = SQLServerClusterManagementService().create_availability_group(
                cluster_id,
                payload,
                operator_id=operator_id,
            )
            return self.success(
                data={"availability_group": ag},
                message=SuccessMessages.DATA_SAVED,
                status=HttpStatus.CREATED,
            )

        return self.safe_call(
            _execute,
            module="sqlserver_clusters",
            action="create_availability_group",
            public_error="创建 SQL Server AG 配置失败",
            context={"cluster_id": cluster_id},
            expected_exceptions=(NotFoundError, ValidationError),
        )


@ns.route("/<int:cluster_id>/availability-groups/<int:ag_id>")
class SQLServerAvailabilityGroupResource(BaseResource):
    """SQL Server AG 配置详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.expect(AvailabilityGroupPayload, validate=False)
    @ns.response(200, "OK", AvailabilityGroupEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @api_admin_required
    @require_csrf
    def patch(self, cluster_id: int, ag_id: int):
        """更新 SQL Server AG 配置."""
        payload = cast(Any, get_raw_payload())
        operator_id = getattr(current_user, "id", None)

        def _execute():
            ag = SQLServerClusterManagementService().update_availability_group(
                cluster_id,
                ag_id,
                payload,
                operator_id=operator_id,
            )
            return self.success(data={"availability_group": ag}, message=SuccessMessages.DATA_SAVED)

        return self.safe_call(
            _execute,
            module="sqlserver_clusters",
            action="update_availability_group",
            public_error="更新 SQL Server AG 配置失败",
            context={"cluster_id": cluster_id, "availability_group_id": ag_id},
            expected_exceptions=(NotFoundError, ValidationError),
        )
