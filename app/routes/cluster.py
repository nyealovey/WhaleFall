"""群集管理页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import STATUS_ACTIVE_OPTIONS
from app.infra.route_safety import safe_route_call
from app.repositories.credentials_repository import CredentialsRepository
from app.services.cluster_status_sync.read_service import SQLServerAgDatabaseSyncStatesReadService
from app.services.mysql_clusters import MySQLClusterManagementService
from app.services.sqlserver_clusters import SQLServerClusterManagementService
from app.utils.decorators import view_required

cluster_bp = Blueprint("cluster", __name__)


@cluster_bp.route("/")
@login_required
@view_required
def index() -> str:
    """群集管理页面，管理 SQL Server 与 MySQL 群集."""
    search = (request.args.get("search") or "").strip()
    status = (request.args.get("status") or "").strip()

    def _render() -> str:
        credentials = [
            credential
            for credential in CredentialsRepository.list_active_credentials()
            if not credential.db_type or credential.db_type == "sqlserver"
        ]
        credential_options = [
            {"id": credential.id, "name": credential.name}
            for credential in credentials
        ]
        sqlserver_instances = SQLServerClusterManagementService().list_sqlserver_instance_options()
        mysql_instances = MySQLClusterManagementService().list_mysql_instance_options()
        return render_template(
            "cluster/list.html",
            search=search,
            status=status,
            status_options=STATUS_ACTIVE_OPTIONS,
            credentials=credentials,
            credential_options=credential_options,
            sqlserver_instances=sqlserver_instances,
            mysql_instances=mysql_instances,
        )

    return safe_route_call(
        _render,
        module="cluster",
        action="index",
        public_error="加载群集管理页面失败",
        context={"search": search, "status": status},
    )


@cluster_bp.route("/sqlserver-status")
@login_required
@view_required
def sqlserver_status() -> str:
    """SQL Server AG 数据库同步状态页."""
    cluster_id = (request.args.get("cluster_id") or "").strip()
    ag_name = (request.args.get("ag_name") or "").strip()
    status = (request.args.get("status") or "all").strip() or "all"
    search = (request.args.get("search") or "").strip()

    def _render() -> str:
        read_service = SQLServerAgDatabaseSyncStatesReadService()
        selected_cluster_id = int(cluster_id) if cluster_id.isdigit() else None
        return render_template(
            "cluster/sqlserver_status.html",
            search=search,
            selected_cluster_id=selected_cluster_id,
            selected_ag_name=ag_name,
            selected_status=status,
            cluster_options=read_service.list_cluster_options(),
            ag_options=read_service.list_ag_options(selected_cluster_id),
        )

    return safe_route_call(
        _render,
        module="cluster",
        action="sqlserver_status",
        public_error="加载 SQL Server AG 数据库状态页失败",
        context={"cluster_id": cluster_id, "ag_name": ag_name, "status": status, "search": search},
    )
