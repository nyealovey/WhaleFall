"""风险中心页面路由."""

from flask import Blueprint, render_template, request, url_for
from flask_login import login_required

from app.core.constants import DatabaseType
from app.infra.flask_typing import RouteReturn
from app.infra.route_safety import safe_route_call
from app.services.risk_center.risk_center_read_service import RiskCenterReadService
from app.utils.database_type_utils import (
    get_database_type_color,
    get_database_type_display_name,
    get_database_type_icon,
)

risk_center_bp = Blueprint("risk_center", __name__)


def _build_database_type_map() -> dict[str, dict[str, str]]:
    return {
        item: {
            "display_name": get_database_type_display_name(item),
            "icon": get_database_type_icon(item),
            "color": get_database_type_color(item),
            "asset_url": url_for("static", filename=f"img/db-types/{item}.png"),
        }
        for item in DatabaseType.RELATIONAL
    }


@risk_center_bp.route("/")
@login_required
def index() -> RouteReturn:
    """渲染风险中心卡片墙."""

    def _execute() -> RouteReturn:
        service = RiskCenterReadService()
        cards = service.list_cards(
            severity=request.args.get("severity", "").strip(),
            db_type=request.args.get("db_type", "").strip(),
            status=request.args.get("status", "").strip(),
            tag=request.args.get("tag", "").strip(),
            search=request.args.get("search", "").strip(),
            page=int(request.args.get("page", "1") or 1),
            limit=int(request.args.get("limit", "0") or 0),
        )
        return render_template(
            "risk_center/index.html",
            summary=service.build_summary(),
            cards=cards,
            database_type_map=_build_database_type_map(),
            filters={
                "severity": request.args.get("severity", ""),
                "db_type": request.args.get("db_type", ""),
                "status": request.args.get("status", ""),
                "tag": request.args.get("tag", ""),
                "search": request.args.get("search", ""),
            },
        )

    return safe_route_call(
        _execute,
        module="risk_center",
        action="index",
        public_error="加载风险中心失败",
    )
