"""
鲸落 - 实例账户管理路由
"""

from flask import Blueprint, Response, jsonify, request
from flask_login import login_required

from app.services.sync_data_manager import SyncDataManager
from app.utils.decorators import view_required
from app.utils.structlog_config import get_api_logger, log_error

# 创建蓝图
instance_accounts_bp = Blueprint("instance_accounts", __name__)

# 获取API日志记录器
api_logger = get_api_logger()


@instance_accounts_bp.route("/<int:instance_id>/accounts")
@login_required
@view_required
def get_instance_accounts(instance_id: int) -> Response:
    """获取实例的账户列表"""
    try:
        # 获取查询参数
        db_type = request.args.get("db_type")
        include_deleted = request.args.get("include_deleted", "false").lower() == "true"

        api_logger.info(
            "获取实例账户列表",
            module="instance_accounts",
            instance_id=instance_id,
            db_type=db_type,
            include_deleted=include_deleted,
        )

        if db_type:
            # 获取指定数据库类型的账户
            accounts = SyncDataManager.get_accounts_by_instance_and_db_type(
                instance_id=instance_id,
                db_type=db_type,
                include_deleted=include_deleted,
            )
        else:
            # 获取所有数据库类型的账户
            accounts = SyncDataManager.get_accounts_by_instance(
                instance_id=instance_id, include_deleted=include_deleted
            )

        # 转换为字典格式
        accounts_data = [account.to_dict() for account in accounts]

        api_logger.info(
            "成功获取实例账户列表",
            module="instance_accounts",
            instance_id=instance_id,
            account_count=len(accounts_data),
        )

        return jsonify({"success": True, "data": accounts_data, "count": len(accounts_data)})

    except Exception as e:
        log_error(
            "获取实例账户列表失败",
            module="instance_accounts",
            instance_id=instance_id,
            error=str(e),
        )
        return (
            jsonify({"success": False, "error": f"获取实例账户列表失败: {str(e)}"}),
            500,
        )


@instance_accounts_bp.route("/<int:instance_id>/accounts/<username>/permissions")
@login_required
@view_required
def get_account_permissions(instance_id: int, username: str) -> Response:
    """查看账户权限详情"""
    try:
        db_type = request.args.get("db_type", "mysql")

        api_logger.info(
            "获取账户权限详情",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            db_type=db_type,
        )

        account = SyncDataManager.get_account_latest(
            db_type=db_type,
            instance_id=instance_id,
            username=username,
            include_deleted=True,
        )

        if not account:
            return jsonify({"success": False, "error": "账户不存在"}), 404

        # 根据数据库类型返回相应的权限结构
        permissions_data = account.get_permissions_by_db_type()

        response_data = {
            "success": True,
            "data": {
                "username": account.username,
                "db_type": account.db_type,
                "is_superuser": account.is_superuser,
                "is_deleted": account.is_deleted,
                "deleted_time": (account.deleted_time.isoformat() if account.deleted_time else None),
                "last_sync_time": (account.last_sync_time.isoformat() if account.last_sync_time else None),
                "last_change_time": (account.last_change_time.isoformat() if account.last_change_time else None),
                "permissions": permissions_data,
            },
        }

        api_logger.info(
            "成功获取账户权限详情",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            db_type=db_type,
        )

        return jsonify(response_data)

    except Exception as e:
        log_error(
            "获取账户权限详情失败",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            error=str(e),
        )
        return (
            jsonify({"success": False, "error": f"获取账户权限详情失败: {str(e)}"}),
            500,
        )


@instance_accounts_bp.route("/<int:instance_id>/accounts/<username>/history")
@login_required
@view_required
def get_account_history(instance_id: int, username: str) -> Response:
    """查看账户变更历史"""
    try:
        db_type = request.args.get("db_type", "mysql")

        api_logger.info(
            "获取账户变更历史",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            db_type=db_type,
        )

        changes = SyncDataManager.get_account_changes(instance_id, db_type, username)

        # 转换为字典格式
        changes_data = [change.to_dict() for change in changes]

        api_logger.info(
            "成功获取账户变更历史",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            db_type=db_type,
            change_count=len(changes_data),
        )

        return jsonify({"success": True, "data": changes_data, "count": len(changes_data)})

    except Exception as e:
        log_error(
            "获取账户变更历史失败",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            error=str(e),
        )
        return (
            jsonify({"success": False, "error": f"获取账户变更历史失败: {str(e)}"}),
            500,
        )


@instance_accounts_bp.route("/<int:instance_id>/accounts/<username>/delete", methods=["POST"])
@login_required
@view_required
def delete_account(instance_id: int, username: str) -> Response:
    """标记账户为已删除"""
    try:
        db_type = request.args.get("db_type", "mysql")
        session_id = request.args.get("session_id")

        api_logger.info(
            "标记账户为已删除",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            db_type=db_type,
        )

        # 检查账户是否存在
        account = SyncDataManager.get_account_latest(
            db_type=db_type,
            instance_id=instance_id,
            username=username,
            include_deleted=True,
        )

        if not account:
            return jsonify({"success": False, "error": "账户不存在"}), 404

        if account.is_deleted:
            return jsonify({"success": False, "error": "账户已经被删除"}), 400

        # 标记为已删除
        SyncDataManager.mark_account_deleted(instance_id, db_type, username, session_id)

        api_logger.info(
            "成功标记账户为已删除",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            db_type=db_type,
        )

        return jsonify({"success": True, "message": "账户已标记为删除"})

    except Exception as e:
        log_error(
            "标记账户为已删除失败",
            module="instance_accounts",
            instance_id=instance_id,
            username=username,
            error=str(e),
        )
        return (
            jsonify({"success": False, "error": f"标记账户为已删除失败: {str(e)}"}),
            500,
        )


@instance_accounts_bp.route("/<int:instance_id>/accounts/statistics")
@login_required
@view_required
def get_account_statistics(instance_id: int) -> Response:
    """获取实例账户统计信息"""
    try:
        api_logger.info("获取实例账户统计信息", module="instance_accounts", instance_id=instance_id)

        # 获取所有数据库类型的账户统计
        db_types = ["mysql", "postgresql", "sqlserver", "oracle"]
        statistics = {}

        for db_type in db_types:
            accounts = SyncDataManager.get_accounts_by_instance_and_db_type(
                instance_id=instance_id, db_type=db_type, include_deleted=False
            )

            deleted_accounts = SyncDataManager.get_accounts_by_instance_and_db_type(
                instance_id=instance_id, db_type=db_type, include_deleted=True
            )

            statistics[db_type] = {
                "total": len(accounts),
                "deleted": len(deleted_accounts) - len(accounts),
                "superusers": len([acc for acc in accounts if acc.is_superuser]),
            }

        # 计算总计
        total_accounts = sum(stats["total"] for stats in statistics.values())
        total_deleted = sum(stats["deleted"] for stats in statistics.values())
        total_superusers = sum(stats["superusers"] for stats in statistics.values())

        response_data = {
            "success": True,
            "data": {
                "by_db_type": statistics,
                "summary": {
                    "total_accounts": total_accounts,
                    "total_deleted": total_deleted,
                    "total_superusers": total_superusers,
                },
            },
        }

        api_logger.info(
            "成功获取实例账户统计信息",
            module="instance_accounts",
            instance_id=instance_id,
            total_accounts=total_accounts,
        )

        return jsonify(response_data)

    except Exception as e:
        log_error(
            "获取实例账户统计信息失败",
            module="instance_accounts",
            instance_id=instance_id,
            error=str(e),
        )
        return (
            jsonify({"success": False, "error": f"获取实例账户统计信息失败: {str(e)}"}),
            500,
        )
