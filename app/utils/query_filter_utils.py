"""筛选器/下拉选项格式化工具.

约束:
- 仅保留纯函数/格式化逻辑
- 禁止在此模块内访问数据库或依赖 Flask app_context
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def build_tag_options(tags: Iterable[Any]) -> list[dict[str, str]]:
    """将标签列表转换为通用下拉/多选 options 结构."""
    options: list[dict[str, str]] = []
    for tag in tags:
        options.append(
            {
                "value": getattr(tag, "name", "") or "",
                "label": getattr(tag, "display_name", "") or "",
                "color": getattr(tag, "color", "") or "",
                "category": getattr(tag, "category", "") or "",
            },
        )
    return options


def build_category_options(categories: Iterable[str], label_mapping: Mapping[str, str]) -> list[dict[str, str]]:
    """将分类值列表转换为下拉 options 结构."""
    options: list[dict[str, str]] = []
    for category in categories:
        normalized = (category or "").strip()
        if not normalized:
            continue
        options.append(
            {
                "value": normalized,
                "label": label_mapping.get(normalized, normalized),
            },
        )
    return options


def build_classification_options(classifications: Iterable[Any]) -> list[dict[str, str]]:
    """将账户分类列表转换为下拉 options 结构."""
    options: list[dict[str, str]] = []
    for classification in classifications:
        label = (
            getattr(classification, "display_name", None)
            or getattr(classification, "name", None)  # legacy
            or getattr(classification, "code", None)
            or ""
        )
        options.append(
            {
                "value": str(getattr(classification, "id", "") or ""),
                "label": str(label),
                "color": getattr(classification, "color", "") or "",
            },
        )
    return options


def build_instance_select_options(instances: Iterable[Any]) -> list[dict[str, str]]:
    """将实例列表转换为 instance_filter 组件使用的 options 结构."""
    options: list[dict[str, str]] = []
    for instance in instances:
        instance_id = getattr(instance, "id", None)
        name = getattr(instance, "name", "") or ""
        db_type = getattr(instance, "db_type", "") or ""
        options.append(
            {
                "value": str(instance_id or ""),
                "label": f"{name} ({db_type})",
                "db_type": db_type,
            },
        )
    return options


def build_database_select_options(databases: Iterable[Any]) -> list[dict[str, str]]:
    """将数据库列表转换为 database_filter 组件使用的 options 结构."""
    options: list[dict[str, str]] = []
    for database in databases:
        database_id = getattr(database, "id", None)
        name = getattr(database, "database_name", "") or ""
        options.append(
            {
                "value": str(database_id or ""),
                "label": name,
                "name": name,
            },
        )
    return options


def build_key_value_options(values: Iterable[str]) -> list[dict[str, str]]:
    """将值列表转换为 value/label 同名的 options 结构."""
    options: list[dict[str, str]] = []
    for value in values:
        normalized = (value or "").strip()
        if not normalized:
            continue
        options.append({"value": normalized, "label": normalized})
    return options
