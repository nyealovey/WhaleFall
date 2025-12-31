"""统一日志敏感字段清理脚本.

用于对 UnifiedLog.context 中的敏感字段做脱敏处理,避免历史日志泄露导致账号/密钥被接管.
该脚本不会输出任何敏感明文,仅记录处理数量与执行结果.
"""

from __future__ import annotations

import argparse
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.models.unified_log import UnifiedLog
from app.utils.sensitive_data import scrub_sensitive_fields
from app.utils.structlog_config import get_task_logger

SENSITIVE_EXTRA_KEYS = (
    "access_token",
    "refresh_token",
    "secret_key",
    "jwt_secret_key",
    "password_encryption_key",
    "key",
    "env_var",
    "postgres_password",
    "redis_password",
    "database_url",
    "cache_redis_url",
    "authorization",
    "cookie",
    "set-cookie",
    "set_cookie",
    "x-csrf-token",
    "csrf_token",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="对 unified_logs.context 做敏感字段脱敏(批量).")
    parser.add_argument("--dry-run", action="store_true", help="仅统计需要脱敏的记录,不写入数据库")
    parser.add_argument("--batch-size", type=int, default=500, help="每批处理数量(默认 500)")
    parser.add_argument("--max-rows", type=int, default=0, help="最多处理条数(默认 0 表示不限制)")
    return parser


def _scrub_context(context: Any) -> dict[str, Any] | None:
    if not isinstance(context, dict):
        return None
    scrubbed = scrub_sensitive_fields(context, extra_keys=SENSITIVE_EXTRA_KEYS)
    return dict(scrubbed)


def main() -> int:
    args = _build_parser().parse_args()
    task_logger = get_task_logger()

    if args.batch_size <= 0:
        task_logger.error("batch_size 参数必须为正整数", module="security_script")
        return 2

    if args.max_rows < 0:
        task_logger.error("max_rows 参数不能为负数", module="security_script")
        return 2

    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        scanned = 0
        modified = 0
        last_id = 0

        try:
            while True:
                query = (
                    UnifiedLog.query.filter(UnifiedLog.id > last_id, UnifiedLog.context.isnot(None))
                    .order_by(UnifiedLog.id)
                    .limit(args.batch_size)
                )
                rows = query.all()
                if not rows:
                    break

                for row in rows:
                    last_id = row.id
                    scanned += 1
                    scrubbed_context = _scrub_context(row.context)
                    if scrubbed_context is None:
                        continue
                    if scrubbed_context != (row.context or {}):
                        modified += 1
                        if not args.dry_run:
                            row.context = scrubbed_context

                    if args.max_rows and scanned >= args.max_rows:
                        break

                if not args.dry_run:
                    db.session.commit()

                if args.max_rows and scanned >= args.max_rows:
                    break

            if args.dry_run:
                task_logger.info(
                    "统一日志脱敏(dry-run)完成",
                    module="security_script",
                    scanned=scanned,
                    would_modify=modified,
                )
            else:
                task_logger.info(
                    "统一日志脱敏完成",
                    module="security_script",
                    scanned=scanned,
                    modified=modified,
                )
            return 0
        except SQLAlchemyError as exc:
            db.session.rollback()
            task_logger.exception(
                "统一日志脱敏失败",
                module="security_script",
                error=str(exc),
            )
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
