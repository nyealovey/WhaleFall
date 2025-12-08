"""账户分类规则表单选项常量."""

DB_TYPE_OPTIONS = [
    {"value": "mysql", "label": "MySQL"},
    {"value": "postgresql", "label": "PostgreSQL"},
    {"value": "sqlserver", "label": "SQL Server"},
    {"value": "oracle", "label": "Oracle"},
]

OPERATOR_OPTIONS = [
    {"value": "OR", "label": "OR (任一条件满足)"},
    {"value": "AND", "label": "AND (全部条件满足)"},
]
