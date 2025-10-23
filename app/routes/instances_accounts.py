"""
实例账户相关接口
"""

from typing import Any

from flask import Response, request
from flask_login import login_required

from app.errors import SystemError
from app.models.instance import Instance
from app.routes.instances import instances_bp
from app.services.account_sync_adapters.account_data_manager import AccountDataManager
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils


@instances_bp.route("/api/<int:instance_id>/accounts")
@login_required
@view_required
def api_get_accounts(instance_id: int) -> Response:
    """获取实例账户数据API"""
    instance = Instance.query.get_or_404(instance_id)

    include_deleted = request.args.get("include_deleted", "false").lower() == "true"

    try:
        accounts = AccountDataManager.get_accounts_by_instance(instance_id, include_deleted=include_deleted)

        account_data = []
        for account in accounts:
            type_specific = account.type_specific or {}

            account_info = {
                "id": account.id,
                "username": account.username,
                "is_superuser": account.is_superuser,
                "is_locked": not account.is_active,
                "is_deleted": account.is_deleted,
                "last_change_time": account.last_change_time.isoformat() if account.last_change_time else None,
                "type_specific": type_specific,
                "server_roles": account.server_roles or [],
                "server_permissions": account.server_permissions or [],
                "database_roles": account.database_roles or {},
                "database_permissions": account.database_permissions or {},
            }

            if instance.db_type == "mysql":
                account_info.update({"host": type_specific.get("host", "%"), "plugin": type_specific.get("plugin", "")})
            elif instance.db_type == "sqlserver":
                account_info.update({"password_change_time": type_specific.get("password_change_time")})
            elif instance.db_type == "oracle":
                account_info.update(
                    {
                        "oracle_id": type_specific.get("oracle_id"),
                        "authentication_type": type_specific.get("authentication_type"),
                        "account_status": type_specific.get("account_status"),
                        "lock_date": type_specific.get("lock_date"),
                        "expiry_date": type_specific.get("expiry_date"),
                        "default_tablespace": type_specific.get("default_tablespace"),
                        "created": type_specific.get("created"),
                    }
                )

            account_data.append(account_info)

        return jsonify_unified_success(
            data={"accounts": account_data},
            message="获取实例账户数据成功",
        )

    except Exception as exc:  # noqa: BLE001
        log_error(
            "获取实例账户数据失败",
            module="instances",
            instance_id=instance_id,
            exception=exc,
        )
        raise SystemError("获取实例账户数据失败") from exc


@instances_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/permissions")
@login_required
@view_required
def get_account_permissions(instance_id: int, account_id: int) -> dict[str, Any] | Response | tuple[Response, int]:
    """获取账户权限详情"""
    instance = Instance.query.get_or_404(instance_id)

    from app.models.current_account_sync_data import CurrentAccountSyncData

    account = CurrentAccountSyncData.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

    try:
        permissions = {
            "数据库类型": instance.db_type.upper(),
            "用户名": account.username,
            "超级用户": "是" if account.is_superuser else "否",
            "最后同步时间": (
                time_utils.format_china_time(account.last_sync_time) if account.last_sync_time else "未知"
            ),
        }

        if instance.db_type == "mysql":
            if account.global_privileges:
                permissions["global_privileges"] = account.global_privileges
            if account.database_privileges:
                permissions["database_privileges"] = account.database_privileges

        elif instance.db_type == "postgresql":
            if account.predefined_roles:
                permissions["predefined_roles"] = account.predefined_roles
            if account.role_attributes:
                permissions["role_attributes"] = account.role_attributes
            if account.database_privileges_pg:
                permissions["database_privileges_pg"] = account.database_privileges_pg

        elif instance.db_type == "sqlserver":
            if account.server_roles:
                permissions["server_roles"] = account.server_roles
            if account.server_permissions:
                permissions["server_permissions"] = account.server_permissions
            if account.database_roles:
                permissions["database_roles"] = account.database_roles
            if account.database_permissions:
                permissions["database_permissions"] = account.database_permissions

        elif instance.db_type == "oracle":
            if account.oracle_roles:
                permissions["oracle_roles"] = account.oracle_roles
            if account.system_privileges:
                permissions["system_privileges"] = account.system_privileges
            if account.tablespace_privileges_oracle:
                permissions["tablespace_privileges_oracle"] = account.tablespace_privileges_oracle

        return jsonify_unified_success(
            data={
                "account": {
                    "id": account.id,
                    "username": account.username,
                    "host": getattr(account, "host", None),
                    "plugin": getattr(account, "plugin", None),
                    "db_type": instance.db_type,
                },
                "permissions": permissions,
            },
            message="获取权限详情成功",
        )

    except Exception as exc:  # noqa: BLE001
        log_error(
            "获取账户权限失败",
            module="instances",
            instance_id=instance_id,
            account_id=account_id,
            exception=exc,
        )
        raise SystemError("获取权限失败") from exc


@instances_bp.route("/api/<int:instance_id>/accounts/<int:account_id>/change-history")
@login_required
@view_required
def get_account_change_history(instance_id: int, account_id: int) -> Response:
    """获取账户变更历史"""
    instance = Instance.query.get_or_404(instance_id)

    from app.models.current_account_sync_data import CurrentAccountSyncData

    account = CurrentAccountSyncData.query.filter_by(id=account_id, instance_id=instance_id).first_or_404()

    try:
        from app.models.account_change_log import AccountChangeLog

        change_logs = (
            AccountChangeLog.query.filter_by(
                instance_id=instance_id,
                username=account.username,
                db_type=instance.db_type,
            )
            .order_by(AccountChangeLog.change_time.desc())
            .limit(50)
            .all()
        )

        history = []
        for log in change_logs:
            history.append(
                {
                    "id": log.id,
                    "change_type": log.change_type,
                    "change_time": (time_utils.format_china_time(log.change_time) if log.change_time else "未知"),
                    "status": log.status,
                    "message": log.message,
                    "privilege_diff": log.privilege_diff,
                    "other_diff": log.other_diff,
                    "session_id": log.session_id,
                }
            )

        return jsonify_unified_success(
            data={
                "account": {
                    "id": account.id,
                    "username": account.username,
                    "db_type": instance.db_type,
                },
                "history": history,
            },
            message="获取账户变更历史成功",
        )

    except Exception as exc:  # noqa: BLE001
        log_error(
            "获取账户变更历史失败",
            module="instances",
            instance_id=instance_id,
            account_id=account_id,
            exception=exc,
        )
        raise SystemError("获取变更历史失败") from exc
