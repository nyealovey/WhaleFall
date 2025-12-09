"""标签路由聚合模块.

暴露标签管理与批量操作蓝图,供应用在入口处统一注册.
"""

from app.routes.tags.bulk import tags_bulk_bp
from app.routes.tags.manage import tags_bp

__all__ = ["tags_bp", "tags_bulk_bp"]
