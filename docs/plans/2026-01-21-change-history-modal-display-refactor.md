# Change History Modal Display Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 让“实例详情页 → 变更历史弹窗”的展示更易读：修复 `type_specific(数据库特性)` 变更导致的“摘要超长 + 原/现值超长”的问题，并让新生成的变更日志更结构化、更可扫读。

**Architecture:**  
后端在生成 `other_diff` 时，对 `type_specific`（当旧值与新值均为 dict）拆成“按 key 的差异条目”，避免把整个 dict stringify 后塞进一条记录；前端渲染器对历史数据里遗留的 `type_specific` “聚合字符串”进行解析，按 key 展示差异，并在“成功且有 diff”时隐藏冗余 `message`（避免重复信息噪音）。

**Tech Stack:** Python (Flask/SQLAlchemy), vanilla JS, pytest, Ruff, Pyright, ESLint.

---

### Task 1: 后端 - `type_specific` 拆分为 key 级 diff（仅修改场景）

**Files:**
- Modify: `app/services/accounts_sync/permission_manager.py`
- Test: `tests/unit/services/test_account_permission_manager.py`

**Step 1: Write the failing test**

在 `tests/unit/services/test_account_permission_manager.py` 增加用例，覆盖：
- 当 `old_snapshot.type_specific[db_type]` 与 `new_snapshot.type_specific` 都是 dict 时，`other_diff` 产出条目应按 key 拆分（例如 `type_specific.host`），而不是单条 `type_specific`。

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py::test_calculate_diff_uses_snapshot_view_not_legacy_columns -q`  
Expected: FAIL（断言仍旧命中旧行为：`type_specific` 单条）

**Step 3: Write minimal implementation**

在 `AccountPermissionManager._collect_other_changes()` 中：
- 当 `old_value` 与 `new_value` 均为 Mapping 时，按 union keys 生成多条 `OtherDiffEntry`（字段名建议 `type_specific.<key>`，label 建议 `数据库特性 · <key>`）。
- 其它情况保持现状（仍然生成单条 `type_specific`）。

**Step 4: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py::test_calculate_diff_uses_snapshot_view_not_legacy_columns -q`  
Expected: PASS

**Step 5: Commit**

Run:
```bash
git add tests/unit/services/test_account_permission_manager.py app/services/accounts_sync/permission_manager.py
git commit -m "refactor: split type_specific diff entries by key"
```

---

### Task 2: 后端 - 实例详情页变更历史接口去掉 message 的 `账户 <username>` 前缀（展示层）

**Files:**
- Modify: `app/services/ledgers/accounts_ledger_change_history_service.py`
- Test: `tests/unit/services/test_accounts_ledger_change_history_service.py` (new)

**Step 1: Write the failing test**

新增 `tests/unit/services/test_accounts_ledger_change_history_service.py`，构造一个 repository stub：
- 返回 username 为 `demo@%` 的 account
- 返回一条 change log，message 为 `账户 demo@% 权限更新:新增 1 项授权`

断言 `get_change_history()` 输出的 `history[0].message` 应为 `权限更新:新增 1 项授权`（已去掉前缀）。

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_accounts_ledger_change_history_service.py -q`  
Expected: FAIL（仍包含 `账户 demo@%`）

**Step 3: Write minimal implementation**

在 `AccountsLedgerChangeHistoryService.get_change_history()` 组装 `InstanceAccountChangeLogItem` 时：
- 对 `log_entry.message` 做前缀裁剪（逻辑与全量历史页一致：仅当 message 以 `账户 <username>` 开头时移除）。

**Step 4: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/services/test_accounts_ledger_change_history_service.py -q`  
Expected: PASS

**Step 5: Commit**

Run:
```bash
git add app/services/ledgers/accounts_ledger_change_history_service.py tests/unit/services/test_accounts_ledger_change_history_service.py
git commit -m "fix: strip redundant username prefix in ledger change history"
```

---

### Task 3: 前端 - 渲染器减少噪音 + 兼容历史 `type_specific` 聚合字符串展示

**Files:**
- Modify: `app/static/js/modules/views/components/change-history/change-history-renderer.js`
- Modify (optional): `app/static/css/pages/accounts/change-history.css`

**Step 1: Write a small verification harness (no existing JS test runner)**

由于仓库当前无 JS 单测基础设施（仅有 ESLint 门禁），本任务通过：
- 纯函数拆分（便于 `node -e` 临时验证）
- ESLint 校验
- 页面手动回归（实例详情页 + 全量历史页详情弹窗）

**Step 2: Implement renderer changes**

1) 当 `status=success/ok` 且存在 `privilege_diff` 或 `other_diff` 时，隐藏 `message`（避免重复摘要噪音）；失败状态或无 diff 时仍展示 message。  
2) 对历史数据里 `other_diff` 的 `field=type_specific` 且 `before/after` 为 `k:v; k2:v2` 形状的字符串：
   - 解析为 map，并按 key 计算差异
   - 按 key 渲染为多行（label 使用 `数据库特性 · <key>`），展示“原/现”值
   - 若无法解析则回退原渲染
3) summary 的 “属性 N 项” 计数：优先按“展示层展开后的条目数”计算（兼容历史 `type_specific` 拆分展示）。

**Step 3: Run ESLint**

Run: `./scripts/ci/eslint-report.sh quick`  
Expected: PASS

**Step 4: Manual regression**

- 实例详情页 → 点击账户行“变更历史”：
  - 成功且有 diff：不再显示超长 message
  - `数据库特性`：以 key 级行展示差异（历史数据也可读）
- 全量历史页 → 打开详情弹窗：展示一致、无报错

**Step 5: Commit**

Run:
```bash
git add app/static/js/modules/views/components/change-history/change-history-renderer.js app/static/css/pages/accounts/change-history.css
git commit -m "refactor: improve change history renderer readability"
```

---

### Task 4: 全量验证

Run:
- `uv run pytest -m unit`
- `make typecheck`
- `./scripts/ci/ruff-report.sh style`
- `./scripts/ci/eslint-report.sh quick`

Expected: 全部 PASS

