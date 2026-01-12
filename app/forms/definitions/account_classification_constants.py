"""账户分类表单选项常量.

说明: 常量定义已下沉到 `app.core.constants.classification_constants`,
该文件仅保留为 Forms 层向后兼容的 re-export.
"""

from app.core.constants.classification_constants import ICON_OPTIONS, RISK_LEVEL_OPTIONS

__all__ = ["ICON_OPTIONS", "RISK_LEVEL_OPTIONS"]
