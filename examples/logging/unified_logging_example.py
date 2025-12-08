"""Unified logging 示例脚本。.

执行方式：
    $ python examples/logging/unified_logging_example.py

示例展示了如何在业务代码中使用统一的 structlog 日志工具，包括：
1. 绑定/清理全局上下文
2. 绑定请求上下文（request_id、用户信息等）
3. 使用 log_info/log_warning/log_error 等快捷方法
4. 结合自定义异常记录结构化错误日志
"""

from __future__ import annotations

import random
import time
import uuid
from contextlib import suppress

from app.errors import ValidationError
from app.utils.structlog_config import (
    bind_context,
    bind_request_context,
    clear_context,
    clear_request_context,
    get_system_logger,
    log_debug,
    log_error,
    log_info,
    log_warning,
)


def bootstrap_logging() -> None:
    """初始化全局日志上下文."""
    bind_context(environment="development", service="logging_demo")
    log_info("日志上下文初始化成功", module="logging_demo")


def simulate_request_cycle(request_path: str) -> None:
    """模拟一次请求处理生命周期."""
    request_id = str(uuid.uuid4())
    user_id = random.randint(1, 100)

    bind_request_context(request_id=request_id, user_id=user_id)
    log_info("请求开始处理", module="logging_demo", path=request_path, method="GET")

    try:
        # 模拟业务校验
        validate_payload({"amount": random.choice([10, -5, 20])})

        # 模拟业务逻辑与外部调用
        time.sleep(0.05)
        log_debug("外部接口调用完成", module="logging_demo", latency_ms=47)

        # 成功响应
        log_info("请求处理完成", module="logging_demo", status="success")
    except ValidationError as exc:
        log_warning(
            "参数校验失败",
            module="logging_demo",
            exception=exc,
            payload=exc.extra,
        )
    except Exception as exc:
        log_error(
            "请求处理发生未预期错误",
            module="logging_demo",
            exception=exc,
            path=request_path,
        )
    finally:
        clear_request_context()


def validate_payload(payload: dict) -> None:
    """示例校验逻辑."""
    amount = payload.get("amount")
    if amount is None or amount < 0:
        msg = "amount 必须为非负数"
        raise ValidationError(
            msg,
            extra={"received": amount},
        )


def log_system_health_probe() -> None:
    """直接获取命名 logger 的示例."""
    system_logger = get_system_logger()
    with suppress(Exception):
        system_logger.info("health_probe", module="logging_demo", status="ok")


def main() -> None:
    bootstrap_logging()
    for path in ("/api/accounts", "/api/databases", "/api/aggregations"):
        simulate_request_cycle(path)
    log_system_health_probe()
    clear_context()


if __name__ == "__main__":
    main()
