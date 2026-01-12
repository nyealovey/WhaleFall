"""账户分类规则表单选项常量."""

from app.core.constants.classification_constants import OPERATOR_OPTIONS

DB_TYPE_OPTIONS = [
    {"value": "mysql", "label": "MySQL"},
    {"value": "postgresql", "label": "PostgreSQL"},
    {"value": "sqlserver", "label": "SQL Server"},
    {"value": "oracle", "label": "Oracle"},
]

__all__ = ["DB_TYPE_OPTIONS", "OPERATOR_OPTIONS"]
