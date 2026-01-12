"""标签批量操作页面路由."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.core.constants import FlashCategory, UserRole
from app.core.types import RouteReturn
from app.utils.decorators import view_required

# 创建蓝图
tags_bulk_bp = Blueprint("tags_bulk", __name__)


@tags_bulk_bp.route("/assign")
@login_required
@view_required
def batch_assign() -> RouteReturn:
    """批量分配标签页面(仅管理员)."""
    if current_user.role != UserRole.ADMIN:
        flash("您没有权限访问此页面", FlashCategory.ERROR)
        return redirect(url_for("tags.index"))

    return render_template("tags/bulk/assign.html")
