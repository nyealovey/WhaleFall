#!/usr/bin/env python3
"""校验 account_permission legacy 权限列与 snapshot(view)一致性.

该脚本用于阶段 1/2/3 的一致性门禁:
- 抽样校验: ``--sample-size``
- 全量校验: ``--full``

注意:
- v4 方案明确“不兼容无 snapshot 的旧数据”,缺失 snapshot 视为不一致。
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.models.account_permission import AccountPermission
from app.utils.structlog_config import get_task_logger

JsonValue = Any


def _echo(message: str = "") -> None:
    """向 stdout 输出一行文本,替代 print 避免 Ruff T201."""
    sys.stdout.write(f"{message}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验 account_permission legacy 列与 v4 snapshot(view)的一致性.")
    parser.add_argument("--sample-size", type=int, default=1000, help="抽样数量(默认 1000)")
    parser.add_argument("--full", action="store_true", help="全量校验(忽略 sample-size)")
    parser.add_argument("--output", default="consistency_report.json", help="输出 JSON 文件路径")
    return parser


def _canonicalize(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return {str(k): _canonicalize(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        normalized = [_canonicalize(item) for item in value]
        return sorted(normalized, key=_stable_sort_key)
    return value


def _stable_sort_key(value: JsonValue) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def _extract_snapshot_field(snapshot: dict[str, Any], record: AccountPermission, field: str) -> JsonValue:
    db_type = str(getattr(record, "db_type", "") or "").lower()

    categories = snapshot.get("categories")
    if not isinstance(categories, dict):
        return None

    if field == "database_privileges_pg":
        return categories.get("database_privileges")
    if field == "tablespace_privileges_oracle":
        return categories.get("tablespace_privileges")

    if field == "type_specific":
        type_specific = snapshot.get("type_specific")
        if isinstance(type_specific, dict) and db_type in type_specific:
            return type_specific.get(db_type)
        return type_specific

    return categories.get(field)


def _iter_legacy_fields() -> list[str]:
    # 与 `app/services/accounts_sync/permission_manager.py::PERMISSION_FIELDS` 保持一致
    return [
        "global_privileges",
        "database_privileges",
        "predefined_roles",
        "role_attributes",
        "database_privileges_pg",
        "tablespace_privileges",
        "server_roles",
        "server_permissions",
        "database_roles",
        "database_permissions",
        "oracle_roles",
        "system_privileges",
        "tablespace_privileges_oracle",
        "type_specific",
    ]


def main() -> int:
    args = _build_parser().parse_args()
    task_logger = get_task_logger()

    if args.sample_size <= 0 and not args.full:
        task_logger.error("sample_size 必须为正整数(或使用 --full)", module="snapshot_consistency")
        return 2

    try:
        from app.services.accounts_permissions.snapshot_view import build_permission_snapshot_view
    except ModuleNotFoundError:
        task_logger.error(
            "snapshot_view 尚未实现,请先完成 Phase 2 读路径(或先落地 snapshot_view 模块)",
            module="snapshot_consistency",
        )
        return 2

    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sampled = 0
        consistent = 0
        inconsistent = 0
        errors: list[dict[str, Any]] = []

        query = AccountPermission.query.order_by(AccountPermission.id.desc())
        if not args.full:
            query = query.limit(args.sample_size)

        try:
            for record in query.all():
                sampled += 1
                snapshot = build_permission_snapshot_view(record)
                if not isinstance(snapshot, dict) or "SNAPSHOT_MISSING" in (snapshot.get("errors") or []):
                    inconsistent += 1
                    errors.append(
                        {
                            "account_id": getattr(record, "id", None),
                            "field": "permission_snapshot",
                            "legacy": None,
                            "snapshot": None,
                        }
                    )
                    continue

                row_inconsistent = False
                for field in _iter_legacy_fields():
                    legacy_value = getattr(record, field, None)
                    snapshot_value = _extract_snapshot_field(snapshot, record, field)
                    if _canonicalize(legacy_value) != _canonicalize(snapshot_value):
                        row_inconsistent = True
                        errors.append(
                            {
                                "account_id": getattr(record, "id", None),
                                "field": field,
                                "legacy": legacy_value,
                                "snapshot": snapshot_value,
                            }
                        )

                if row_inconsistent:
                    inconsistent += 1
                else:
                    consistent += 1

            inconsistency_rate = (inconsistent / sampled) if sampled else 0
            report = {
                "total_sampled": sampled,
                "consistent": consistent,
                "inconsistent": inconsistent,
                "inconsistency_rate": inconsistency_rate,
                "errors": errors,
            }
            with open(args.output, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False, sort_keys=True)

            _echo(f"consistency report written: {args.output}")
            _echo(f"total_sampled={sampled} consistent={consistent} inconsistent={inconsistent}")
            return 0
        except SQLAlchemyError as exc:
            db.session.rollback()
            task_logger.exception(
                "一致性校验失败",
                module="snapshot_consistency",
                error=str(exc),
            )
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

