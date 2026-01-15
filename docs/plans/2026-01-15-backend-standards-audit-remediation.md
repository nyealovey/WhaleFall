# Backend Standards Audit Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 一次性修复 `docs/reports/2026-01-15-backend-standards-audit-fixlist.md` 中列出的标准冲突/歧义与 `app/**` 违规点，并用迁移 + 单测 + 退出机制把兼容/回退分支收敛为可审计、可移除的实现。

**Architecture:** 先收敛标准口径（避免“修复方向分裂”），再按 internal contract 的“写入端单入口 + 读入口 adapter/normalizer + 数据迁移/退出条件”策略修复 DB JSON payload；最后批量复核 `silent except return` 与高风险 `or` 兜底并补门禁测试，防止回归。

**Tech Stack:** Flask, SQLAlchemy, Alembic, structlog, pytest, ruff, pyright/pyright-report.

---

### Task 0: 准备工作（工作区 + 基线验证 + 证据对齐）

**Files:**
- Reference: `docs/reports/2026-01-15-backend-standards-audit-fixlist.md`
- Reference: `docs/reports/2026-01-15-backend-standards-audit-report.md`

**Step 1: 新建分支/工作区（推荐 worktree）**

Run:
```bash
git checkout -b fix/backend-standards-audit-2026-01-15
```

Expected: 成功切到新分支。

**Step 2: 跑一次基线单测（确认当前主干是绿的）**

Run:
```bash
uv run pytest -m unit
```

Expected: 全绿（若失败，先记录失败项，避免把历史失败误判为本次引入）。

**Step 3: 记录当前扫描证据快照（便于后续验证“命中归零/下降”）**

Run:
```bash
wc -l docs/reports/artifacts/2026-01-15-app-silent-except-return.txt
wc -l docs/reports/artifacts/2026-01-15-app-or-boolop.txt
```

Expected: `silent-except-return` 为 33 行左右（含 header），`or-boolop` 为 760 行左右（含 header）。

**Step 4: Commit（仅准备工作可跳过提交；建议不提交）**

Commit message (optional): `chore: prepare backend standards audit remediation`

---

### Task 1: 修复标准冲突/歧义（STD-01 ~ STD-06）

**Files:**
- Modify: `docs/Obsidian/standards/backend/error-message-schema-unification.md`
- Modify: `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
- Modify: `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md`
- Modify: `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md`
- Modify: `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md`

**Step 1: 收敛 `error` 字段语义（STD-01）**

Edit:
- 在 `docs/Obsidian/standards/backend/error-message-schema-unification.md` 明确区分：
  - 对外 envelope：`error` 必须为 bool（固定语义）
  - 诊断字符串：改名（如 `diagnostic_error`）或仅允许内部结果对象使用

**Step 2: 收敛 `error_code` 对外边界（STD-02）**

Edit:
- 在 `docs/Obsidian/standards/backend/error-message-schema-unification.md` 或 `docs/Obsidian/standards/backend/layer/api-layer-standards.md` 增加“可执行规则”：
  - 对外 API（含 `data`）如需机器可读错误码，统一使用 `message_code`（或命名空间字段）
  - internal contract 的 `error_code` 如何映射/是否允许透出

**Step 3: 明确 parse_payload 与 schema canonicalization 分工（STD-03）**

Edit:
- 在 `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md` 或相关分层标准补“职责分界表”：
  - parse_payload：shape-level 清理（NUL、list 形状等）
  - schema：语义级 canonicalization（`"" -> None`、类型转换、默认值、alias/迁移）

**Step 4: 补齐异常类型链路示例（STD-04）**

Edit:
- 在 `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md` 加一段最小示例：
  - pydantic validator 抛 ValueError → `validate_or_raise` 捕获 → 转为项目 `ValidationError`
  - message_key/message_code 的走向说明

**Step 5: 为 Tasks “复杂/薄” MUST NOT 增加可验证判据（STD-05）**

Edit:
- 在 `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md` 增加 2~3 条触发条件（行数、循环内 I/O、多段提交等）以及例外申请方式。

**Step 6: internal contract scope 增加排除项/例外清单（STD-06）**

Edit:
- 在 `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md` 明确：日志类 JSON（至少 `UnifiedLog.context`）不纳入 version 强制要求。

**Step 7: 本地校验（用 rg 确认冲突文本已被收敛）**

Run:
```bash
rg -n "\\berror_code\\b" docs/Obsidian/standards/backend/error-message-schema-unification.md
rg -n "\\berror\\b" docs/Obsidian/standards/backend/error-message-schema-unification.md
```

Expected: 文档中出现“允许/禁止/映射策略”的明确表述，不再产生多解。

**Step 8: Commit**

```bash
git add docs/Obsidian/standards/backend/error-message-schema-unification.md \
  docs/Obsidian/standards/backend/layer/api-layer-standards.md \
  docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md \
  docs/Obsidian/standards/backend/request-payload-and-schema-validation.md \
  docs/Obsidian/standards/backend/layer/tasks-layer-standards.md
git commit -m "docs: resolve backend standards ambiguities for error fields and contracts"
```

---

### Task 2: 修复 `sync_details` internal contract（CODE-01）

**Files:**
- Create: `app/schemas/internal_contracts/sync_details_v1.py`
- Modify: `app/services/sync_session_service.py`
- Modify: `app/services/history_sessions/history_sessions_read_service.py`
- Test: `tests/unit/schemas/internal_contracts/test_sync_details_v1.py`
- Create: `migrations/versions/<ts>_backfill_sync_instance_record_sync_details_version.py`

**Step 1: 写 failing test（缺失 version 的 sync_details 必须被识别/迁移）**

Create `tests/unit/schemas/internal_contracts/test_sync_details_v1.py`:
```python
import pytest

from app.schemas.internal_contracts.sync_details_v1 import normalize_sync_details_v1


@pytest.mark.unit
def test_normalize_sync_details_v1_injects_version_when_missing() -> None:
    raw = {"inventory": {"created": 1}}
    normalized = normalize_sync_details_v1(raw)
    assert normalized["version"] == 1
    assert normalized["inventory"] == {"created": 1}
```

**Step 2: 运行测试，确认失败（函数不存在）**

Run:
```bash
uv run pytest -m unit tests/unit/schemas/internal_contracts/test_sync_details_v1.py -q
```

Expected: FAIL（ImportError / function not found）。

**Step 3: 实现最小 adapter/normalizer（写入口单入口）**

Create `app/schemas/internal_contracts/sync_details_v1.py`（原则：不做业务拼装，只做 version + JSON safe 的基础规范化）：
- `SYNC_DETAILS_VERSION_V1 = 1`
- `normalize_sync_details_v1(value: object) -> dict[str, object] | None`
  - `None -> None`
  - 非 dict → 抛 `TypeError`（写入口不接受脏类型）
  - dict 且缺失/非法 version → 注入 `version=1`
  - 保留原有 key（避免破坏现有 UI/服务消费）

**Step 4: 运行测试，确认通过**

Run:
```bash
uv run pytest -m unit tests/unit/schemas/internal_contracts/test_sync_details_v1.py -q
```

Expected: PASS。

**Step 5: 接入 `SyncSessionService` 写入口（集中写入最新版本）**

Modify `app/services/sync_session_service.py`：
- 在 `_clean_sync_details(...)` 内调用 `normalize_sync_details_v1(...)`（在 clean_value 前/后按需要调整）
- 确保 `complete_instance_sync(...)` 与 `fail_instance_sync(...)` 最终写入的 `record.sync_details` 必含 `version=1`

**Step 6: 增加读入口的“旧数据兼容”与退出机制**

Modify `app/services/history_sessions/history_sessions_read_service.py`：
- 输出时对 `sync_details` 进行一次 normalize（只用于“读旧数据补 version”，并记录兼容命中日志/计数）
- 退出机制：当迁移完成且观测 N 天无旧数据命中后，移除兼容分支（记录在 PR/变更说明）

**Step 7: 添加数据迁移（Backfill）**

Create migration revision（PostgreSQL 优先；按仓库约定使用 timestamp rev-id）：
- 新建迁移文件：
  ```bash
  REV_ID="$(date +%Y%m%d%H%M%S)"
  uv run flask --app app:create_app db revision --rev-id "$REV_ID" -m "backfill sync_details version"
  ```
- 对 `sync_instance_records.sync_details`：
  - `sync_details IS NOT NULL` 且缺失 `version` → 注入 `version=1`

验证建议（开发环境）：
```bash
make -f Makefile.dev init-db
```

**Step 8: Commit**

```bash
git add app/schemas/internal_contracts/sync_details_v1.py \
  app/services/sync_session_service.py \
  app/services/history_sessions/history_sessions_read_service.py \
  tests/unit/schemas/internal_contracts/test_sync_details_v1.py \
  migrations/versions/*_backfill_sync_instance_record_sync_details_version.py
git commit -m "fix: version sync_details internal payload and add backfill"
```

---

### Task 3: 修复持久化 JSON 解析的 silent fallback（CODE-02）

**Files:**
- Modify: `app/models/account_classification.py`
- Modify: `app/models/database_type_config.py`
- Test: `tests/unit/models/test_account_classification_rule_expression.py`
- Test: `tests/unit/models/test_database_type_config_features_list.py`

**Step 1: 为 `ClassificationRule.get_rule_expression` 写 failing test（非法 JSON 不得 silent fallback）**

Create `tests/unit/models/test_account_classification_rule_expression.py`:
```python
import pytest

from app.models.account_classification import ClassificationRule


@pytest.mark.unit
def test_get_rule_expression_invalid_json_is_not_silent_fallback() -> None:
    rule = ClassificationRule()
    rule.rule_expression = "{not-json"
    with pytest.raises(ValueError):
        rule.get_rule_expression()
```

**Step 2: 运行测试确认失败（当前会返回 {}）**

Run:
```bash
uv run pytest -m unit tests/unit/models/test_account_classification_rule_expression.py -q
```

Expected: FAIL（未抛异常）。

**Step 3: 最小实现：fail-fast 或显式降级但必须可观测**

Modify `app/models/account_classification.py`：
- `ClassificationRule.get_rule_expression`：把 `except ...: return {}` 改为 **fail-fast**：
  - 解析失败直接 `raise ValueError("rule_expression JSON decode failed")`（可在 message 中包含 `rule_id/rule_name`）

**Step 4: 运行测试确认通过**

Run:
```bash
uv run pytest -m unit tests/unit/models/test_account_classification_rule_expression.py -q
```

Expected: PASS。

**Step 5: 为 `DatabaseTypeConfig.features_list` 写 failing test（非法 JSON 不得 silent fallback）**

Create `tests/unit/models/test_database_type_config_features_list.py`:
```python
import pytest

from app.models.database_type_config import DatabaseTypeConfig


@pytest.mark.unit
def test_features_list_invalid_json_is_not_silent_fallback() -> None:
    cfg = DatabaseTypeConfig()
    cfg.features = "[not-json"
    with pytest.raises(ValueError):
        _ = cfg.features_list
```

**Step 6: 实现最小修复（与业务方确认策略）**

Modify `app/models/database_type_config.py`：
- 统一选择 **fail-fast**：解析失败直接抛异常（推荐 `ValueError("database_type_config.features JSON decode failed")`），由上层统一处理（禁止返回 `[]` 吞掉问题）。

**Step 7: 运行测试确认通过**

Run:
```bash
uv run pytest -m unit tests/unit/models/test_database_type_config_features_list.py -q
```

Expected: PASS。

**Step 8: Commit**

```bash
git add app/models/account_classification.py app/models/database_type_config.py \
  tests/unit/models/test_account_classification_rule_expression.py \
  tests/unit/models/test_database_type_config_features_list.py
git commit -m "fix: remove silent fallback when decoding persisted json text fields"
```

---

### Task 4: `AccountPermission.type_specific` 版本化 + 回填（CODE-04）

**Files:**
- Create: `app/schemas/internal_contracts/type_specific_v1.py`
- Modify: `app/services/accounts_sync/permission_manager.py`
- Modify: `app/services/instances/instance_accounts_service.py`
- Test: `tests/unit/schemas/internal_contracts/test_type_specific_v1.py`
- Create: `migrations/versions/<ts>_backfill_account_permission_type_specific_version.py`

**Step 1: failing test（type_specific 缺 version 时写入口必须注入 version=1）**

Create `tests/unit/schemas/internal_contracts/test_type_specific_v1.py`:
```python
import pytest

from app.schemas.internal_contracts.type_specific_v1 import normalize_type_specific_v1


@pytest.mark.unit
def test_normalize_type_specific_v1_injects_version() -> None:
    raw = {"host": "localhost"}
    normalized = normalize_type_specific_v1(raw)
    assert normalized["version"] == 1
    assert normalized["host"] == "localhost"
```

**Step 2: Run，确认失败（函数不存在）**

Run:
```bash
uv run pytest -m unit tests/unit/schemas/internal_contracts/test_type_specific_v1.py -q
```

Expected: FAIL。

**Step 3: 实现 normalizer**

Create `app/schemas/internal_contracts/type_specific_v1.py`：
- `TYPE_SPECIFIC_VERSION_V1 = 1`
- `normalize_type_specific_v1(value: object) -> dict[str, object] | None`
  - `None -> None`
  - 非 dict → 抛 `TypeError`
  - dict 缺失/非法 version → 注入 `version=1`
  - 保留原有字段（避免破坏 `instance_accounts_service` 取 `host/plugin/...`）

**Step 4: Run，确认通过**

Run:
```bash
uv run pytest -m unit tests/unit/schemas/internal_contracts/test_type_specific_v1.py -q
```

Expected: PASS。

**Step 5: 接入写入口**

Modify `app/services/accounts_sync/permission_manager.py`：
- 在写入 `record.type_specific` 前调用 `normalize_type_specific_v1(...)`

**Step 6: 读入口兼容 + 退出机制**

Modify `app/services/instances/instance_accounts_service.py`：
- 读取 `type_specific` 时：
  - 若为 dict 且缺 `version`：只在 adapter 单入口补 version 并记录兼容命中（不要在业务逻辑散落 `or`/兜底链）
  - 输出给 UI 的 shape 保持不变（仍是 dict 字段集合）

**Step 7: 数据回填迁移**

Create migration revision（PostgreSQL 优先；按仓库约定使用 timestamp rev-id）：
- 新建迁移文件：
  ```bash
  REV_ID="$(date +%Y%m%d%H%M%S)"
  uv run flask --app app:create_app db revision --rev-id "$REV_ID" -m "backfill account_permission.type_specific version"
  ```
- 对 `account_permission.type_specific`：缺失 `version` 的 dict 注入 `version=1`

**Step 8: Commit**

```bash
git add app/schemas/internal_contracts/type_specific_v1.py \
  app/services/accounts_sync/permission_manager.py \
  app/services/instances/instance_accounts_service.py \
  tests/unit/schemas/internal_contracts/test_type_specific_v1.py \
  migrations/versions/*_backfill_account_permission_type_specific_version.py
git commit -m "fix: version account_permission.type_specific and backfill existing rows"
```

---

### Task 5: `AccountChangeLog.privilege_diff/other_diff` 版本化 + 回填（CODE-03）

**Files:**
- Create: `app/schemas/internal_contracts/account_change_log_diff_v1.py`
- Modify: `app/services/accounts_sync/permission_manager.py`
- Modify: `app/services/ledgers/accounts_ledger_change_history_service.py`
- Test: `tests/unit/schemas/internal_contracts/test_account_change_log_diff_v1.py`
- Create: `migrations/versions/<ts>_backfill_account_change_log_diff_version.py`

**Step 1: failing test（legacy list 与 v1 dict 都能被读入口收敛为 list[entry]）**

Create `tests/unit/schemas/internal_contracts/test_account_change_log_diff_v1.py`:
```python
import pytest

from app.schemas.internal_contracts.account_change_log_diff_v1 import extract_diff_entries


@pytest.mark.unit
def test_extract_diff_entries_supports_legacy_list_shape() -> None:
    raw = [{"action": "GRANT", "object": "db"}]
    assert extract_diff_entries(raw) == raw


@pytest.mark.unit
def test_extract_diff_entries_supports_v1_dict_shape() -> None:
    raw = {"version": 1, "entries": [{"action": "GRANT", "object": "db"}]}
    assert extract_diff_entries(raw) == [{"action": "GRANT", "object": "db"}]
```

**Step 2: Run，确认失败（函数不存在）**

Run:
```bash
uv run pytest -m unit tests/unit/schemas/internal_contracts/test_account_change_log_diff_v1.py -q
```

Expected: FAIL。

**Step 3: 实现 adapter**

Create `app/schemas/internal_contracts/account_change_log_diff_v1.py`：
- `DIFF_VERSION_V1 = 1`
- `wrap_entries_v1(entries: list[object]) -> dict[str, object]` → `{"version": 1, "entries": entries}`
- `extract_diff_entries(value: object) -> list[object]`
  - legacy：`list` → 原样返回（并提供“兼容命中”的可观测 hook：由调用方打日志）
  - v1：`dict` 且 `version==1` → 返回 `entries`（必须为 list，否则 fail-fast 或返回空并显式错误结构）
  - 未知版本/非法类型：fail-fast（或 best-effort 错误结构，但调用方必须把它当失败）

**Step 4: Run，确认通过**

Run:
```bash
uv run pytest -m unit tests/unit/schemas/internal_contracts/test_account_change_log_diff_v1.py -q
```

Expected: PASS。

**Step 5: 写入口：写入 v1 dict（避免继续写 legacy list）**

Modify `app/services/accounts_sync/permission_manager.py`：
- 将：
  - `log.privilege_diff = privilege_diff`
  - `log.other_diff = other_diff`
  改为写入 `wrap_entries_v1(...)` 的 dict（version=1）

**Step 6: 读入口：对外仍输出 list（保持前端不改动）**

Modify `app/services/ledgers/accounts_ledger_change_history_service.py`：
- 对 `getattr(log_entry, "privilege_diff")` / `other_diff` 使用 `extract_diff_entries(...)`
- legacy list 命中时记录结构化日志（`fallback=true` + `fallback_reason="ACCOUNT_CHANGE_LOG_DIFF_LEGACY_LIST"`）

**Step 7: 数据回填迁移（把历史 list 结构升级为 v1 dict）**

Create migration revision（建议用 SQL + `jsonb_typeof` 判断 array vs object；按仓库约定使用 timestamp rev-id）：
- 新建迁移文件：
  ```bash
  REV_ID="$(date +%Y%m%d%H%M%S)"
  uv run flask --app app:create_app db revision --rev-id "$REV_ID" -m "backfill account change log diff version"
  ```
- 对 `account_change_log.privilege_diff` / `other_diff`：
  - 若 `jsonb_typeof(...) == 'array'` → 包装为 `{"version":1,"entries": <old-array>}`
  - 若已是 object 且有 version → 跳过

**Step 8: Commit**

```bash
git add app/schemas/internal_contracts/account_change_log_diff_v1.py \
  app/services/accounts_sync/permission_manager.py \
  app/services/ledgers/accounts_ledger_change_history_service.py \
  tests/unit/schemas/internal_contracts/test_account_change_log_diff_v1.py \
  migrations/versions/*_backfill_account_change_log_diff_version.py
git commit -m "fix: version account change log diff payloads and keep stable read output"
```

---

### Task 6: 关闭 REVIEW-01（32 处 silent except return）——分类、补日志或补测试

**Files:**
- Reference: `docs/reports/artifacts/2026-01-15-app-silent-except-return.txt`
- Modify/Test: 以逐条命中为准（至少覆盖 health/cache/connection 四类）

**Step 1: 按类别分组（validation vs runtime fallback）**

Run:
```bash
sed -n '1,120p' docs/reports/artifacts/2026-01-15-app-silent-except-return.txt
```

Expected: 拿到 32 个位置清单。

**Step 2: 先修“更像运行期降级”的条目（必须可观测）**

优先项示例（以实际代码为准）：
- `app/services/health/health_checks_service.py:132`
- `app/utils/cache_utils.py:210`
- `app/services/connection_adapters/adapters/*.py` 若属于 fallback

动作：
- 在边界层（route/task/worker）补 `fallback=true` + `fallback_reason`
- 或改为 fail-fast（上层捕获并返回统一错误）

**Step 3: 对“解析/验证语义”的条目补单测与注释**

典型：`app/settings.py:84`、`app/utils/time_utils.py:*` 等
- 目标：让读者能区分“这不是 fallback，是输入解析的失败语义”
- 补单测（只覆盖关键函数，不必把 32 个全写到单测里）

**Step 4: 复扫确认：silent-except-return 数量下降，或每个剩余点都有合理归因**

Run:
```bash
python3 - <<'PY'
import ast
from pathlib import Path


def walk_stmt_list(stmts: list[ast.stmt]):
    return ast.walk(ast.Module(body=stmts, type_ignores=[]))


def unparse(node: ast.AST) -> str | None:
    try:
        return ast.unparse(node)
    except Exception:
        return None


results: list[tuple[str, int, str, str | None]] = []
for path in sorted(Path("app").rglob("*.py")):
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        continue
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        continue

    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            returns = [n for n in walk_stmt_list(handler.body) if isinstance(n, ast.Return)]
            if not returns:
                continue
            calls = [n for n in walk_stmt_list(handler.body) if isinstance(n, ast.Call)]
            if calls:
                continue

            exc = "Exception" if handler.type is None else (unparse(handler.type) or "<unparse-failed>")
            for r in returns:
                results.append((str(path), r.lineno, exc, unparse(r.value) if r.value is not None else None))

print(f"silent-except-return-count={len(results)}")
PY
```

Expected: 数量下降；或至少留下的点都能在代码中找到“为何不需要 fallback log”的证据（单测/注释）。

**Step 5: Commit（可分 1~N 个 commit，按类别切）**

Commit message examples:
- `fix: add observable fallback for health/cache failures`
- `test: clarify parsing helpers are not runtime fallbacks`

---

### Task 7: 关闭 REVIEW-02（`or` 兜底 759 处）——加门禁，优先修 internal payload 相关点

**Files:**
- Reference: `docs/reports/artifacts/2026-01-15-app-or-boolop.txt`
- Test: `tests/unit/test_internal_contract_no_alias_fallback_chains.py`（新）

**Step 1: 新增门禁测试：禁止在业务层引入 `data.get("new") or data.get("old")` 形状兼容链**

Create `tests/unit/test_internal_contract_no_alias_fallback_chains.py`:
```python
import pathlib
import re

import pytest


_GET_OR_GET_PATTERN = re.compile(
    r"""\\.get\\(\\s*['"][^'"]+['"]\\s*(?:,[^)]*)?\\)\\s*or\\s*[^#\\n]*\\.get\\(\\s*['"][^'"]""",
)


@pytest.mark.unit
def test_no_internal_payload_alias_fallback_chains_in_business_layers() -> None:
    roots = [
        pathlib.Path("app/services"),
        pathlib.Path("app/repositories"),
    ]

    bad: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if _GET_OR_GET_PATTERN.search(line):
                    bad.append(f"{path}:{lineno} {line.strip()}")

    assert not bad, "Found internal payload alias fallback chains:\\n" + "\\n".join(bad)
```

说明：这是“保守门禁”，只拦截同一行里出现的 `.get(...) or ... .get(...)`；多行表达式如需覆盖，再增强规则（避免误报导致阻塞开发）。

**Step 2: Run 测试（应当直接 PASS，因为审计期未发现该模式）**

Run:
```bash
uv run pytest -m unit tests/unit/test_internal_contract_no_alias_fallback_chains.py -q
```

Expected: PASS。

**Step 3: 优先修复“覆盖合法空值”的高风险点（CODE-05 中列出的代表性位置）**

目标：把 `or` 兜底替换为 `is None`/显式缺失判定（仅当业务语义确认“空值是合法值”）。

候选起点：
- `app/tasks/accounts_sync_tasks.py:88`
- `app/tasks/accounts_sync_tasks.py:89`
- `app/routes/credentials.py:57`
- `app/services/accounts_sync/accounts_sync_service.py:299`（结合 Task 2 的 sync_details version 化策略一起改）

**Step 4: Commit**

```bash
git add tests/unit/test_internal_contract_no_alias_fallback_chains.py
git commit -m "test: guard against internal payload alias fallback chains in business layers"
```

（若同时改动 `or` 兜底点，另起 commit：`refactor: replace risky or fallbacks with explicit None checks`）

---

### Task 8: 全量验证（类型检查 + 单测 + 风格）

**Step 1: 单测**

Run:
```bash
uv run pytest -m unit
```

Expected: PASS。

**Step 2: Ruff**

Run:
```bash
./scripts/ci/ruff-report.sh style
```

Expected: PASS（或只剩可接受的告警）。

**Step 3: Typecheck**

Run:
```bash
make typecheck
```

Expected: PASS。

**Step 4: 最终 Commit（如有零散修补）**

Commit message: `chore: finalize backend standards audit remediation`
