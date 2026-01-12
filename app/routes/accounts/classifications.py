"""Accounts 域:账户分类管理路由."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from flask import Blueprint, render_template
from flask.typing import ResponseReturnValue, RouteCallable
from flask_login import login_required

from app.core.constants.colors import ThemeColors
from app.infra.route_safety import safe_route_call
from app.utils.decorators import create_required, require_csrf, update_required, view_required
from app.views.classification_forms import AccountClassificationFormView, ClassificationRuleFormView

# 创建蓝图
accounts_classifications_bp = Blueprint(
    "accounts_classifications",
    __name__,
    url_prefix="/accounts/classifications",
)


@accounts_classifications_bp.route("/")
@login_required
@view_required
def index() -> str:
    """账户分类管理首页."""
    def _execute() -> str:
        color_options = ThemeColors.COLOR_MAP
        return render_template("accounts/account-classification/index.html", color_options=color_options)

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="index",
        public_error="加载账户分类页面失败",
    )


_classification_create_view = cast(
    Callable[..., ResponseReturnValue],
    AccountClassificationFormView.as_view("classification_create_form"),
)
_classification_create_view = login_required(create_required(require_csrf(_classification_create_view)))

accounts_classifications_bp.add_url_rule(
    "/classifications/create",
    view_func=cast(RouteCallable, _classification_create_view),
    methods=["GET", "POST"],
    defaults={"resource_id": None},
)

_classification_edit_view = cast(
    Callable[..., ResponseReturnValue],
    AccountClassificationFormView.as_view("classification_edit_form"),
)
_classification_edit_view = login_required(update_required(require_csrf(_classification_edit_view)))

accounts_classifications_bp.add_url_rule(
    "/classifications/<int:resource_id>/edit",
    view_func=cast(RouteCallable, _classification_edit_view),
    methods=["GET", "POST"],
)

_rule_create_view = cast(
    Callable[..., ResponseReturnValue],
    ClassificationRuleFormView.as_view("classification_rule_create_form"),
)
_rule_create_view = login_required(create_required(require_csrf(_rule_create_view)))

accounts_classifications_bp.add_url_rule(
    "/rules/create",
    view_func=cast(RouteCallable, _rule_create_view),
    methods=["GET", "POST"],
    defaults={"resource_id": None},
)

_rule_edit_view = cast(
    Callable[..., ResponseReturnValue],
    ClassificationRuleFormView.as_view("classification_rule_edit_form"),
)
_rule_edit_view = login_required(update_required(require_csrf(_rule_edit_view)))

accounts_classifications_bp.add_url_rule(
    "/rules/<int:resource_id>/edit",
    view_func=cast(RouteCallable, _rule_edit_view),
    methods=["GET", "POST"],
)
