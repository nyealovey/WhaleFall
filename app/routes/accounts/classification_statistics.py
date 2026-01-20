"""Accounts 域:账户分类统计页面路由."""

from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.core.constants import DATABASE_TYPES
from app.infra.route_safety import safe_route_call
from app.services.accounts.account_classifications_read_service import AccountClassificationsReadService
from app.services.common.filter_options_service import FilterOptionsService
from app.utils.decorators import view_required

accounts_classification_statistics_bp = Blueprint("accounts_classification_statistics", __name__)
_filter_options_service = FilterOptionsService()
_classifications_read_service = AccountClassificationsReadService()


@accounts_classification_statistics_bp.route("/statistics/classifications", methods=["GET"])
@login_required
@view_required
def classification_statistics() -> str:
    """账户分类统计页面."""

    def _execute() -> str:
        classification_id = request.args.get("classification_id", "").strip()
        period_type = request.args.get("period_type", "daily").strip()
        db_type = request.args.get("db_type", "").strip()
        instance_id = request.args.get("instance_id", "").strip()
        rule_id = request.args.get("rule_id", "").strip()
        status = request.args.get("status", "active").strip()

        database_type_options = [{"value": item["name"], "label": item["display_name"]} for item in DATABASE_TYPES]
        instance_options = _filter_options_service.list_instance_select_options(db_type or None) if db_type else []

        classifications = _classifications_read_service.list_classifications()
        classification_options = [
            {
                "value": str(item.id),
                "label": item.display_name,
                "code": item.code,
            }
            for item in classifications
        ]

        return render_template(
            "accounts/classification_statistics.html",
            classification_options=classification_options,
            database_type_options=database_type_options,
            instance_options=instance_options,
            selected_classification_id=classification_id,
            selected_period_type=period_type,
            selected_db_type=db_type,
            selected_instance_id=instance_id,
            selected_rule_id=rule_id,
            selected_rule_status=status,
        )

    return safe_route_call(
        _execute,
        module="accounts_classification_statistics",
        action="classification_statistics_page",
        public_error="加载账户分类统计页面失败",
        context={
            "classification_id": request.args.get("classification_id"),
            "period_type": request.args.get("period_type"),
            "db_type": request.args.get("db_type"),
            "instance_id": request.args.get("instance_id"),
            "rule_id": request.args.get("rule_id"),
            "status": request.args.get("status"),
        },
    )
