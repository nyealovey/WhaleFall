"""导入/模板相关常量。."""

from __future__ import annotations

# 实例批量导入模板列，需与前端提示保持一致
INSTANCE_IMPORT_TEMPLATE_HEADERS = [
    "name",
    "db_type",
    "host",
    "port",
    "database_name",
    "description",
    "credential_id",
]

# 实例批量导入必填字段
INSTANCE_IMPORT_REQUIRED_FIELDS = {"name", "db_type", "host", "port"}

# 模板示例行，帮助用户快速理解格式
INSTANCE_IMPORT_TEMPLATE_SAMPLE = [
    "demo-mysql-01",
    "mysql",
    "10.10.10.10",
    "3306",
    "inventory",
    "example instance",
    "123",
]
