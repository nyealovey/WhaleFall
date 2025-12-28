"""实例域路由包,集中导出蓝图."""

from app.routes.instances.detail import instances_detail_bp
from app.routes.instances.manage import instances_bp

__all__ = [
    "instances_bp",
    "instances_detail_bp",
]
