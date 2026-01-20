# Account Classification Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将账户分类管理重构为「6 个系统内置分类 + 6 级风险等级 + code(不可变) + display_name(可变)」，并彻底移除“显示颜色”。

**Architecture:** 账户分类仍使用 `account_classifications` 单表，新增/重命名字段为 `code`(唯一、不可变)、`display_name`(可变)。系统内置通过 `is_system=true` 锁定：仅允许改 `display_name/description/priority`；自定义允许改 `risk_level/icon_name/priority/display_name/description`。风险等级改为整数 1-6。颜色相关字段与 API/前端全部删除。

**Tech Stack:** Flask + Flask-RESTX, SQLAlchemy, Alembic, Pydantic, Vanilla JS.

---

## Invariants / Decisions

- 系统内置 6 类 `code`（全小写，页面与 DB 一致）：`super`, `highly`, `sensitive`, `medium`, `low`, `public`
- `code` 创建后不可修改（自定义也不可改），用于统计口径。
- 风险等级 `risk_level`：整数 1-6（1 最高，6 最低）。
- 取消分类“显示颜色”：删除 `color` 列与所有衍生字段（`color_value/color_name/css_class`、`/colors` API、前端颜色下拉/预览、统计/台账里的颜色展示）。
- `priority` 仅影响排序；文案与 help_text 去掉“影响规则匹配顺序”的描述。

---

### Task 1: 更新类型/常量（先让类型对齐）

**Files:**
- Modify: `app/core/constants/classification_constants.py`
- Modify: `app/core/types/accounts_classifications.py`
- Modify: `app/core/types/orm_kwargs.py`

**Step 1: Write the failing test**

（本 Task 以类型对齐为主，不单独写测试；由后续 service/API contract 测试覆盖。）

**Step 2: Implement minimal changes**

- 将 `RISK_LEVEL_OPTIONS` 改为 1-6 的 options（label 用中文，例如 `1级(最高)`…`6级(最低)`）。
- `AccountClassificationListItem`：
  - `risk_level: int`
  - 删除 `color` / `color_key`
- `AccountClassificationOrmFields`：
  - `name -> code`
  - `risk_level: int`
  - 删除 `color`

**Step 3: Run typecheck**

Run: `make typecheck`
Expected: PASS（如失败，按报错逐个修正引用类型）。

---

### Task 2: 重构 ORM 模型（name -> code、移除 color、risk_level=1..6 int）

**Files:**
- Modify: `app/models/account_classification.py`

**Step 1: Write the failing test**

在 `tests/unit/routes/test_api_v1_accounts_ledgers_contract.py`（或新建模型单测）增加断言：`account_classifications` 表包含列 `code`、不包含列 `color`。

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_accounts_ledgers_contract.py -q`
Expected: FAIL（列名不匹配）。

**Step 3: Write minimal implementation**

- `AccountClassification.name` 改为 `code`（列名 `code`）
- `risk_level` 改为 `db.Integer`/`SmallInteger`，默认 4，NOT NULL
- 删除 `color` 列与 `color_value/color_name/css_class` 相关 property/导入
- `to_dict()`/`__repr__()`/`AccountClassificationAssignment.__repr__/to_dict` 内部引用从 `name` 改为 `code`（展示名仍优先 `display_name`）

**Step 4: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_accounts_ledgers_contract.py -q`
Expected: PASS

---

### Task 3: 更新 repository/service（写路径加系统内置字段白名单）

**Files:**
- Modify: `app/repositories/accounts_classifications_repository.py`
- Modify: `app/services/accounts/account_classifications_write_service.py`
- Modify: `app/services/accounts/account_classifications_read_service.py`
- Modify: `app/repositories/account_statistics_repository.py`
- Modify: `app/repositories/ledgers/accounts_ledger_repository.py`
- Modify: `app/schemas/account_classifications.py`

**Step 1: Write the failing test**

在 `tests/unit/services/test_account_classification_write_service.py` 增加：

```python
def test_update_system_classification_rejects_risk_level_change(monkeypatch):
    ...
```

期望：`is_system=True` 时更新 `risk_level/icon_name` 报错（message_key 建议 `FORBIDDEN` 或新 key）。

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_account_classification_write_service.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- `AccountClassificationCreatePayload`：
  - `code` 必填（自动 `.strip().lower()`）
  - `risk_level` 改为 int（1-6）
  - 删除 `color`
- `AccountClassificationUpdatePayload`：
  - 仍禁止修改 `code`
  - 删除 `color`
- write_service:
  - create：写入 `code/display_name/description/risk_level/icon_name/priority`
  - update：若 `classification.is_system`，仅允许更新 `display_name/description/priority`，否则抛 `ValidationError`
- read_service：输出字段改为 `code=classification.code`，移除 `color/color_key`
- repository：`exists_classification_name` 重命名为 `exists_classification_code`（并同步调用点）
- statistics/ledger：移除对 `AccountClassification.color` 的引用与输出字段

**Step 4: Run tests**

Run: `uv run pytest -m unit tests/unit/services/test_account_classification_write_service.py -q`
Expected: PASS

---

### Task 4: 更新 REST API（移除 /colors，risk_level=1..6，字段名对齐）

**Files:**
- Modify: `app/api/v1/restx_models/accounts.py`
- Modify: `app/api/v1/namespaces/accounts_classifications.py`

**Step 1: Write the failing test**

更新 `tests/unit/routes/test_api_v1_accounts_classifications_contract.py`：
- 删除 `/colors` 相关断言
- 创建分类 payload 改为 `{ "code": "demo", "display_name": "demo", "risk_level": 4, "icon_name": "fa-tag", "priority": 0 }`
- 断言返回字段包含 `code/display_name/risk_level/icon_name/priority/is_system`

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_accounts_classifications_contract.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- RESTX fields：
  - `risk_level` 改为 Integer
  - 删除 `color/color_key`
- namespace：
  - 删除 `/colors` Resource 与相关 import/model
  - `_serialize_classification` 改为输出 `code`（来自 `classification.code`）且不输出颜色
  - `AccountClassificationWritePayload` 删除 `color`，`risk_level` 用 Integer

**Step 4: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_accounts_classifications_contract.py -q`
Expected: PASS

---

### Task 5: 更新前端（页面展示 code；表单新增 code；移除颜色；系统内置字段禁用）

**Files:**
- Modify: `app/templates/accounts/account-classification/index.html`
- Modify: `app/templates/accounts/account-classification/classifications_form.html`
- Modify: `app/templates/accounts/account-classification/modals/classification-modals.html`
- Modify: `app/static/js/modules/views/accounts/account-classification/index.js`
- Modify: `app/static/js/modules/views/accounts/account-classification/modals/classification-modals.js`
- Modify: `app/static/js/common/validation-rules.js`
- Modify: `app/routes/accounts/classifications.py`
- Modify: `app/views/form_handlers/account_classification_form_handler.py`
- Modify: `app/forms/definitions/account_classification.py`

**Step 1: Manual verification checklist**

- 分类卡片：展示 `display_name` + 下面一行 `code`（小号/等宽）
- 新建分类：必须填写 `code`（小写），可选 `display_name`；风险等级 1-6；可选图标；priority 仅影响排序
- 编辑系统内置分类：仅可改 `display_name/description/priority`，risk/icon 禁用且不提交
- 页面不再出现“显示颜色”与颜色预览

**Step 2: Implement**

- 移除 route/index 对 `ThemeColors` 的依赖与传参
- 删除 Jinja 模板里的颜色 select/preview 片段
- JS 模态收集 payload：
  - create: `{code, display_name, description, risk_level, icon_name, priority}`
  - update: 系统内置只提交 `{display_name, description, priority}`；自定义提交全部（但不包含 code）
- 更新风险等级 pill 渲染：支持 1-6
- validation-rules：新增 `classification.code` 规则，移除 `classification.color`
- 修正优先级 help_text：去掉“规则匹配顺序”

---

### Task 6: 新增 Alembic 迁移（DB：name->code、drop color、risk_level int、seed 6 系统内置）

**Files:**
- Create: `migrations/versions/20260120xxxxxx_refactor_account_classifications_code_and_risk_levels.py`

**Step 1: Implement migration**

Upgrade:
- `ALTER TABLE account_classifications RENAME COLUMN name TO code`
- `UPDATE account_classifications SET code = lower(code)`
- `ALTER TABLE ... DROP COLUMN color`
- 将 `risk_level` 从 varchar 转为 smallint：
  - 先 `UPDATE` 把旧值映射为 1-6（或统一置为 4）
  - `ALTER COLUMN risk_level TYPE SMALLINT USING risk_level::smallint`
  - `ALTER COLUMN risk_level SET DEFAULT 4`
  - 添加 `CHECK (risk_level BETWEEN 1 AND 6)`
- upsert 6 条系统内置分类（`is_system=true`、`is_active=true`、`code` 固定为上面 6 个）

Downgrade:
-（如必须支持）反向恢复：risk_level->varchar、加回 color（可为 NULL）、code->name。

**Step 2: Verification**

Run: `uv run pytest -m unit -q`
Expected: PASS

---

### Task 7: 全量验证

**Step 1: Lint/Typecheck**

Run: `make format && make typecheck`
Expected: PASS

**Step 2: Unit tests**

Run: `uv run pytest -m unit`
Expected: PASS

