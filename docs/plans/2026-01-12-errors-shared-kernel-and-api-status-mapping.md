# Errors Shared Kernel & API Status Mapping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 将异常定义从“Errors 层”调整为 shared kernel(`app/core/exceptions.py`), 并把异常→HTTP status 的映射下放到 API 边界(`app/api/error_mapping.py`), 清理业务层对 `HttpStatus`/`status_code` 的依赖, 保持现有错误封套(JSON envelope)不变。

**Architecture:** `app/core` 只承载与框架无关的异常类型与语义字段(如 `category/severity/message_key/extra`); HTTP 层(Flask/RestX)在入口处做异常到状态码的映射, 并将 `status_code` 作为参数传给 `unified_error_response(...)`。全仓统一改用 `app.core.exceptions`，不提供 `app/errors.py` 兼容门面。

**Tech Stack:** Flask + Flask-RESTX + Werkzeug + ruff + pyright + pytest.

---

## Verification Baseline(完成后必跑)

Run:

```bash
./.venv/bin/ruff check \
  app/api/error_mapping.py \
  app/core/exceptions.py \
  app/__init__.py \
  app/api/v1/api.py \
  app/utils/response_utils.py \
  app/utils/structlog_config.py \
  app/utils/logging/error_adapter.py
./scripts/ci/pyright-guard.sh
uv run pytest -m unit
# 如本机 uv cache 权限异常,改用:
./.venv/bin/pytest -m unit
```

Expected:

- `ruff` Exit 0
- `pyright` diagnostics: 0(Exit 0)
- `pytest` Exit 0

---

## Task 1: 新增 shared kernel 异常模块

**Files:**

- Create: `app/core/__init__.py`
- Create: `app/core/exceptions.py`
- Delete: `app/errors.py`(不提供 re-export/兼容门面)

**Steps:**

1) 将异常类型迁移到 `app/core/exceptions.py`
2) 移除异常元数据中的 HTTP status 概念, 不再在异常上保存 `status_code`

---

## Task 2: 将异常→HTTP status 映射迁移到 API 边界

**Files:**

- Create: `app/api/error_mapping.py`
- Delete: `app/utils/error_mapping.py`

**Steps:**

1) `map_exception_to_status(...)` 仅依赖 `werkzeug.exceptions.HTTPException` 与 `app/core/exceptions.py` 的异常类型
2) 以异常类型(如 `ValidationError/NotFoundError/...`)为主做映射, 未命中回落到 500

---

## Task 3: 边界层显式传递 status_code, 取消 utils 内部自动映射

**Files:**

- Modify: `app/__init__.py`(全局 errorhandler)
- Modify: `app/api/v1/api.py`(RestX `handle_error`)
- Modify: `app/utils/response_utils.py`(不再 import/调用 `map_exception_to_status`)
- Modify: `app/utils/structlog_config.py`(装饰器 `error_handler` 使用新映射模块)

**Steps:**

1) 在各 HTTP 入口处先算 `status_code = map_exception_to_status(...)`
2) 调用 `unified_error_response(error, status_code=status_code, ...)` 构造封套

---

## Task 4: 清理业务层 `status_code=HttpStatus.*` 用法

**Files:**

- Modify: `app/services/**` 中主动抛错位置(优先改为 `ConflictError/ValidationError/...`)

**Steps:**

1) 将 `raise AppError(..., status_code=HttpStatus.CONFLICT, ...)` 改为对应的异常子类(例如 `ConflictError`)
2) 保持 `message_key/category/severity` 语义一致(能用默认值则不显式传参)

---

## Task 5: 文档修正(Errors 不作为 layer)

**Files:**

- Modify: `docs/Obsidian/standards/backend/layer/README.md`(将 Errors 节点调整为 shared kernel/core 的表述)
