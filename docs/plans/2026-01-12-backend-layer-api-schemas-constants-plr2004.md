# Backend Layer Alignment (API/Schemas/Constants/PLR2004) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 按 `docs/reports/2026-01-12-backend-layer-layer13-focus-issue-report.md` 的剩余项与用户决策落地: API 层按方案 A 迁移 query 参数解析到 `reqparse`; Schemas 层按建议移除对 Models 的反向依赖; Constants 层按方案 B 将 helper methods 下沉到 `app/utils/**`; 清理 `ruff` 的 `PLR2004` 魔法数字(26 处)并迁移为具名常量。

**Architecture:** 保持分层依赖方向不变: Constants 只保留值/枚举/静态映射; 所有基于常量映射的“查询/判定/归一化”逻辑移动到 Utils; API 端点只做薄参数解析/校验与调用 Service, query 参数统一通过 `flask_restx.reqparse.RequestParser` 并用 `@ns.expect(parser)` 生成 OpenAPI; Schemas 只依赖 `app.core.constants/app.core.types/app.utils` 不依赖 Models, 业务阈值统一从 `app/core/constants/validation_limits.py` 引用。

**Tech Stack:** Flask + Flask-RESTX + SQLAlchemy + pydantic + ruff + pyright + pytest.

---

## Verification Baseline(完成后必跑)

Run:

```bash
./.venv/bin/ruff check --select PLR2004 --output-format concise app
./scripts/ci/pyright-guard.sh
uv run pytest -m unit
```

Expected:

- `PLR2004` 0 errors(Exit 0)
- `pyright` diagnostics: 0(Exit 0)
- `pytest` Exit 0

---

## Task 1: 新增校验/阈值常量文件(承接 PLR2004 与 Schemas 解耦)

**Files:**

- Create: `app/core/constants/validation_limits.py`
- Modify: `app/core/constants/__init__.py`(必要时导出常量)

**Steps:**

1) 添加具名常量(至少覆盖: 密码长度上下限、用户名长度上下限、host/name/description 长度上限、API limit 上限、bcrypt rounds 下限、小时上限等)
2) 确认 constants 层不引入 `app.utils.*` 依赖

---

## Task 2: Schemas 层按建议移除 Models 依赖(2.2)

**Files:**

- Modify: `app/schemas/users.py`
- Modify: `app/models/user.py`(若存在“从 models 导出阈值常量”的历史出口,迁移后移除或保持兼容但不再被 schema 引用)

**Steps:**

1) 将 `MIN_USER_PASSWORD_LENGTH` 从 `app.models.user` 下沉到 `app/core/constants/validation_limits.py`
2) `app/schemas/users.py` 改为 import constants(禁止 import models)
3) 跑 `rg -n "from app\\.models\\." app/schemas` 确认 schemas 不再反向依赖 models

---

## Task 3: Constants helper methods 迁移到 Utils(2.6, 方案 B)

**Files:**

- Create: `app/utils/database_type_utils.py`
- Create: `app/utils/theme_color_utils.py`
- Create: `app/utils/user_role_utils.py`
- Create: `app/utils/status_type_utils.py`
- Modify: `app/core/constants/colors.py`
- Modify: `app/core/constants/database_types.py`
- Modify: `app/core/constants/user_roles.py`
- Modify: `app/core/constants/status_types.py`
- Modify: `app/core/constants/sync_constants.py`
- Modify: `app/core/constants/http_headers.py`
- Modify: `app/core/constants/http_methods.py`
- Modify: `app/core/constants/flash_categories.py`
- Modify: `app/core/constants/time_constants.py`
- Modify: `app/core/constants/filter_options.py`(移除对 helper methods 的调用,仅使用静态映射/枚举值)
- Modify: 受影响的 call sites(services/models/routes/views/api/schemas)

**Steps:**

1) 在 utils 中实现对应 helper 函数(例如 `normalize_database_type`, `get_theme_color_value`, `is_sync_session_status_valid` 等)
2) 全仓替换 `ThemeColors.*`/`DatabaseType.*` 等 helper 调用为 utils 调用
3) 删除 constants 类中的 helper methods(保留常量值与静态映射)
4) 确认 constants 层无 `from app.utils` 依赖,并通过 `rg -n \"from app\\.utils\" app/core/constants` 自查

---

## Task 4: API 层 query 参数解析迁移到 `reqparse`(2.1, 方案 A)

**Files:**

- Create: `app/api/v1/resources/query_parsers.py`
- Modify: `app/api/v1/namespaces/*.py`(所有使用 `request.args.get/getlist` 的端点)

**Steps:**

1) 在 `query_parsers.py` 提供可复用的 parser builder(分页/排序/布尔/标签列表等)
2) 逐文件替换 `request.args.get/getlist` 为 `parser.parse_args()` 结果
3) 为对应方法补 `@ns.expect(parser)`(保持 OpenAPI 文档稳定)
4) 允许保留 `request.args.to_dict(flat=False)` 作为审计快照,但不再用其读取具体参数
5) `rg -n \"request\\.args\\.get\\(|request\\.args\\.getlist\\(\" app/api` 确认 0 命中

---

## Task 5: 清理 `PLR2004`(26 处)并迁移为常量(4)

**Files:**

- Modify: `app/api/v1/namespaces/databases.py`
- Modify: `app/schemas/auth.py`
- Modify: `app/schemas/credentials.py`
- Modify: `app/schemas/instances.py`
- Modify: `app/services/account_classification/dsl_v4.py`
- Modify: `app/services/accounts_permissions/facts_builder.py`
- Modify: `app/services/accounts_permissions/snapshot_view.py`
- Modify: `app/services/database_sync/table_size_adapters/*`
- Modify: `app/settings.py`

**Steps:**

1) 将涉及业务语义的阈值统一改为引用 `app/core/constants/validation_limits.py`
2) 将适配器/解析形状相关的索引常量改为“模块内具名常量”(避免把实现细节塞进全局 constants)
3) 复跑 `./.venv/bin/ruff check --select PLR2004 --output-format concise app` 确认 0

---

## Task 6: 更新门禁脚本与报告

**Files:**

- Modify: `scripts/ci/api-layer-guard.sh`(scope 从 `app/api/v1` 扩展到 `app/api`)
- Modify: `docs/reports/2026-01-12-backend-layer-layer13-focus-issue-report.md`
- Modify: `docs/reports/2026-01-12-backend-layer-uncovered-python-files-recommendations.md`

**Steps:**

1) API 门禁脚本 target 改为 `app/api` 并更新提示文案
2) 基于最新扫描更新两份报告(修正“仍需处理项/PLR2004 数量/API request.args 命中数”等)

