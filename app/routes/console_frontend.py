"""React console frontend routes.

The legacy Flask/Jinja UI keeps its existing routes. This blueprint only serves
the independently built React app under `/console`.
"""

from pathlib import Path

from flask import Blueprint, current_app, send_from_directory
from werkzeug.exceptions import NotFound

from app.infra.flask_typing import RouteReturn
from app.infra.route_safety import safe_route_call
from app.settings import PROJECT_ROOT

console_frontend_bp = Blueprint("console_frontend", __name__)

DEFAULT_CONSOLE_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"


def _console_dist_dir() -> Path:
    configured = current_app.config.get("CONSOLE_FRONTEND_DIST_DIR")
    if configured:
        return Path(str(configured)).resolve()
    return DEFAULT_CONSOLE_DIST_DIR


def _send_console_index() -> RouteReturn:
    dist_dir = _console_dist_dir()
    if not (dist_dir / "index.html").is_file():
        raise NotFound("React console build output is missing")

    response = send_from_directory(str(dist_dir), "index.html")
    response.headers["Cache-Control"] = "no-store"
    return response


@console_frontend_bp.get("/console/assets/<path:filename>")
def console_assets(filename: str) -> RouteReturn:
    """Serve hashed React build assets."""

    def _execute() -> RouteReturn:
        assets_dir = _console_dist_dir() / "assets"
        response = send_from_directory(str(assets_dir), filename)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    return safe_route_call(
        _execute,
        module="console_frontend",
        action="console_assets",
        public_error="加载控制台静态资源失败",
        context={"filename": filename},
    )


@console_frontend_bp.get("/console/static/<path:filename>")
def console_static(filename: str) -> RouteReturn:
    """Serve copied React public assets."""

    def _execute() -> RouteReturn:
        static_dir = _console_dist_dir() / "static"
        response = send_from_directory(str(static_dir), filename)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    return safe_route_call(
        _execute,
        module="console_frontend",
        action="console_static",
        public_error="加载控制台公共静态资源失败",
        context={"filename": filename},
    )


@console_frontend_bp.get("/console")
@console_frontend_bp.get("/console/")
@console_frontend_bp.get("/console/<path:_spa_path>")
def console_app(_spa_path: str = "") -> RouteReturn:
    """Serve the React SPA entry for `/console` routes."""
    return safe_route_call(
        _send_console_index,
        module="console_frontend",
        action="console_app",
        public_error="加载控制台前端失败",
        context={"path": _spa_path},
    )
