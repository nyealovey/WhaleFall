"""cluster 页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import STATUS_ACTIVE_OPTIONS
from app.infra.route_safety import safe_route_call
from app.repositories.credentials_repository import CredentialsRepository
from app.services.sqlserver_clusters import SQLServerClusterManagementService
from app.utils.decorators import view_required

cluster_bp = Blueprint("cluster", __name__)


@cluster_bp.route("/")
@login_required
@view_required
def index() -> str:
    """cluster 管理页面，仅管理 SQL Server 群集."""
    search = (request.args.get("search") or "").strip()
    status = (request.args.get("status") or "").strip()

    def _render() -> str:
        credentials = [
            credential
            for credential in CredentialsRepository.list_active_credentials()
            if not credential.db_type or credential.db_type == "sqlserver"
        ]
        sqlserver_instances = SQLServerClusterManagementService().list_sqlserver_instance_options()
        return render_template(
            "cluster/list.html",
            search=search,
            status=status,
            status_options=STATUS_ACTIVE_OPTIONS,
            credentials=credentials,
            sqlserver_instances=sqlserver_instances,
        )

    return safe_route_call(
        _render,
        module="cluster",
        action="index",
        public_error="加载 cluster 页面失败",
        context={"search": search, "status": status},
    )
