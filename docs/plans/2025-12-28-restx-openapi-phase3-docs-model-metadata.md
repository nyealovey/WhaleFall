# RestX OpenAPI Phase 3 Docs/Model Metadata Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 补齐关键 RestX/OpenAPI model 的 `description/example`, 并为 "认证/CSRF 使用说明" 增加稳定文档入口, 完成 `004-flask-restx-openapi-migration-progress` 的 Phase 3 文档项.

**Architecture:** 以 `app/api/v1/namespaces/**.py` 的 `ns.model(...)` 与 `app/routes/**/restx_models.py` 的 `fields.*` 定义为主入口补齐字段 `description/example`; 新增 `docs/reference/api/authentication-and-csrf.md` 并在 `docs/reference/api/README.md` 提供入口; 最后更新迁移进度文档勾选项与变更日志.

**Tech Stack:** Flask, Flask-RESTX(OpenAPI schema via `fields`), Markdown

---

### Task 1: 增加 "认证/CSRF 使用说明" 文档入口

**Files:**
- Create: `docs/reference/api/authentication-and-csrf.md`
- Modify: `docs/reference/api/README.md`
- (Optional) Modify: `docs/reference/api/api-routes-documentation.md` (将 CSRF header 名称对齐为 `X-CSRFToken`)

**Step 1: 写文档页面**
- 覆盖内容:
  - 认证方式概览 (cookie session vs JWT 的现状与边界)
  - CSRF 获取与提交 (`GET /api/v1/auth/csrf-token` + `X-CSRFToken`)
  - `curl` 示例 (cookie jar + token header)
  - Swagger UI 使用提示 (浏览器 cookie + 手动填 header)
  - 常见错误 (401/403/429)

**Step 2: 将新页面加入 API 参考索引**
- 在 `docs/reference/api/README.md` 的 "索引" 小节追加条目.

**Step 3: (可选) 修正路由索引文档中的 CSRF header 名称**
- 将 `X-CSRF-Token` 统一为 `X-CSRFToken`, 避免与实现不一致.

---

### Task 2: 补齐关键 model 的 description/example

**Files:**
- Modify: `app/api/v1/namespaces/auth.py`
- Modify: `app/api/v1/models/envelope.py` (如发现字段缺示例/描述)
- Modify: `app/routes/tags/restx_models.py`
- Modify: `app/routes/instances/restx_models.py`
- Modify: `app/routes/accounts/restx_models.py`
- Modify: `app/routes/credentials_restx_models.py`
- Modify: `app/routes/common_restx_models.py`
- Modify: `app/routes/capacity/restx_models.py`
- Modify: `app/routes/databases/restx_models.py`
- Modify: `app/routes/history/restx_models.py`
- Modify: `app/routes/dashboard_restx_models.py`
- Modify: `app/routes/partition_restx_models.py`
- Modify: `app/routes/scheduler_restx_models.py`

**Step 1: 给 auth namespace 的 request/response model 增加字段说明**
- `LoginPayload`/`ChangePasswordPayload` 等: 补 `description` + `example` (用户名/密码用占位示例, 避免误导为真实值).
- `CsrfTokenData`/`MeData`: 补齐时间戳字段示例 (ISO8601).

**Step 2: 给各域 `*_restx_models.py` 的字段定义补齐 description/example**
- 原则:
  - `id/*_id`: 用整数示例 (如 `1`)
  - `*_at/*_time`: ISO8601 示例 (如 `2025-01-01T00:00:00`)
  - `is_*`: `True/False`
  - `db_type`: `mysql/postgres/sqlserver/oracle` (按项目使用口径)
  - `Raw` 类型: 给 `description`, `example` 只放安全的简化结构
  - List/Nested: 补 `description`, 必要时补示例 (避免巨大 payload)

**Step 3: 保持不改变运行时行为**
- 仅修改 `fields.*` 的 metadata (description/example/required), 不调整 key 名/结构.

---

### Task 3: 更新迁移进度文档 (Phase 3)

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

**Step 1: 勾选 Phase 3 的两个 TODO**
- `补齐关键 model 的 description/example`
- `增加"认证/CSRF 使用说明"文档入口`

**Step 2: 在末尾追加当日变更日志**
- 记录日期与完成项 (保持既有格式).

---

### Task 4: 验证

**Step 1: 格式化 (如仓库已配置)**
Run: `make format`
Expected: exit 0

**Step 2: Python 语法检查**
Run: `python -m compileall app`
Expected: exit 0

**Step 3: 单元测试 (最小契约)**
Run: `pytest -m unit`
Expected: exit 0
