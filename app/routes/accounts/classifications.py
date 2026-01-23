"""Accounts 域:账户分类管理路由."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from app.infra.route_safety import safe_route_call
from app.utils.decorators import view_required

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
        return render_template("accounts/account-classification/index.html")

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="index",
        public_error="加载账户分类页面失败",
    )
