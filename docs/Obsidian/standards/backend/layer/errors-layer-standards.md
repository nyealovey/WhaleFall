---
title: Errors 异常层编写规范
aliases:
  - errors-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-11
updated: 2026-01-11
owner: WhaleFall Team
scope: "`app/errors/**` 下所有异常类型定义"
related:
  - "[[standards/backend/layer/README|后端分层标准]]"
  - "[[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)|API 响应封套(JSON Envelope)]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/action-endpoint-failure-semantics]]"
---

# Errors 异常层编写规范

> [!note] 说明
> Errors 层承载可控业务异常类型(`AppError` 及子类)与默认元数据(HTTP status/category/severity/message_key). 它是跨层基础模块,供 Routes/API/Tasks/Services/Repositories/Utils 统一表达失败语义.

## 目的

- 统一异常类型与默认元数据,避免上层散落 magic status/message_code 与口径漂移.
- 让错误语义可结构化消费(错误封套/日志/监控),而不是依赖字符串匹配.
- 固化依赖边界: `app/errors` 只定义异常,不做 HTTP/框架适配.

## 适用范围

- `app/errors/**` 下所有异常类型定义文件.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: 只定义异常类型与其默认元数据(例如 `status_code/category/severity/default_message_key`).
- MUST: 异常默认 `message_key` 必须是稳定的机器可读标识,并能映射到 `ErrorMessages` 的同名字段.
- MUST NOT: 生成/序列化对外错误封套(JSON envelope)(该能力属于 `app/utils/response_utils.py`).
- MUST NOT: 处理 `werkzeug.HTTPException` 或任何框架异常到 HTTP status 的映射(该能力属于 `app/utils/error_mapping.py`).
- MUST NOT: 记录日志或拼装日志 payload(该能力属于 `app/utils/logging/**` 与 `app/utils/structlog_config.py`).

### 2) 依赖规则

允许依赖:

- MUST: 标准库
- MAY: `app.constants.*`(例如 `HttpStatus`, `ErrorCategory`, `ErrorSeverity`, `ErrorMessages`)
- MAY: `app.types.*`(仅用于类型注解,例如 `LoggerExtra`)

禁止依赖:

- MUST NOT: `flask.*`, `werkzeug.*`
- MUST NOT: `sqlalchemy.*`, `app` 的 `db`
- MUST NOT: `app.utils.*`, `app.services.*`, `app.repositories.*`, `app.routes.*`, `app.api.*`, `app.models.*`

### 3) 命名与组织

- SHOULD: 异常类使用 `*Error` 后缀,例如 `ValidationError`, `NotFoundError`.
- SHOULD: 将通用异常放在 `app/errors/__init__.py` 暴露,并维护稳定的 `__all__`.
- SHOULD: 不要按领域拆出大量细碎异常文件,除非异常数量已明显影响可读性.

### 4) 初始化与覆写

- SHOULD: 异常允许在实例级别覆写 `message_key/status_code/category/severity/extra`,用于表达同类错误的不同失败语义.
- MUST NOT: 引入无明确需求的防御性兜底逻辑(例如对 `ErrorMessages` 的 `hasattr` 检查).

## 门禁/检查方式

```bash
rg -n "from flask|from werkzeug|sqlalchemy|db\\.session|from app\\.utils\\." app/errors
```

