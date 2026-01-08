---
title: 敏感数据处理(脱敏/加密/导出)
aliases:
  - sensitive-data-handling
tags:
  - standards
  - standards/backend
status: active
created: 2025-12-25
updated: 2026-01-08
owner: WhaleFall Team
scope: 日志、错误响应、凭据存储与导出(CSV/Excel)相关代码路径
related:
  - "[[standards/backend/configuration-and-secrets]]"
---

# 敏感数据处理(脱敏/加密/导出)

## 目的

- 防止口令、令牌、密钥、连接串等敏感信息进入日志/错误响应/审计记录。
- 统一“凭据加密存储”和“导出防注入”的落点，避免业务代码各自实现。

## 适用范围

- 结构化日志：`app/utils/structlog_config.py`、`app/utils/logging/handlers.py`
- 脱敏工具：`app/utils/sensitive_data.py`
- 凭据加密：`app/utils/password_crypto_utils.py`
- 导出防注入：`app/utils/spreadsheet_formula_safety.py`
- 任何包含用户输入、连接信息、密钥信息的 API/任务/脚本

## 规则（MUST/SHOULD/MAY）

### 1) 禁止泄露敏感信息

- MUST NOT：把密码/令牌/密钥/连接串原文写入日志、错误响应或数据库日志中心。
- SHOULD：如需排障，记录“是否存在/长度/来源/变量名”等非敏感信息。

### 2) 日志脱敏（统一落点）

- MUST：日志写入前必须经过脱敏处理（当前由 `app/utils/logging/handlers.py` 统一调用 `scrub_sensitive_fields`）。
- SHOULD：新增敏感字段时，同步更新以下列表：
  - `app/utils/sensitive_data.py` 的 `DEFAULT_SENSITIVE_KEYS`
  - `app/utils/logging/handlers.py` 的 `CONTEXT_SCRUB_EXTRA_KEYS`

### 3) 凭据加密存储

- MUST：数据库连接口令必须以加密形式存储与传输，统一使用 `app/utils/password_crypto_utils.py` 的 `PasswordManager`。
- MUST：生产环境必须设置 `PASSWORD_ENCRYPTION_KEY`（缺失会导致重启后无法解密已存储凭据）。
- MUST NOT：API 返回或模板渲染中出现明文口令。

### 4) 导出防公式注入（CSV/Excel）

- MUST：导出到 CSV/Excel 的用户可控字符串必须做公式注入防护，统一使用：
  - `sanitize_csv_cell(...)`
  - `sanitize_csv_row(...)`
- SHOULD：当新增导出功能时，为典型恶意输入补齐单元测试用例。

## 正反例

### 正例：记录参数但不记录口令

- 记录 `instance_id/db_type/username` 等字段，避免记录 `password/database_url`。

### 反例：把连接串写入日志

```python
logger.info("connect_failed", database_url=database_url)
```

## 门禁/检查方式

- 单元测试：
  - `tests/unit/utils/test_sensitive_data.py`
  - `tests/unit/utils/test_spreadsheet_formula_safety.py`
- `env.example` 密钥门禁(相关标准见 [[standards/backend/configuration-and-secrets|配置与密钥]])：`./scripts/ci/secrets-guard.sh`

## 变更历史

- 2025-12-25：新增标准文档，统一脱敏列表维护、凭据加密落点与导出防注入要求。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
