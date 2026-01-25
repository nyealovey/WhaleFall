# Remove Prometheus Client Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 删除仓库内所有 `prometheus_client` 相关代码与类型桩（`app/core/types/stubs/prometheus_client`），并移除生产依赖 `prometheus-client`。

**Architecture:** 通过 ripgrep 做全仓引用审计；移除 DSL v4 与 permission manager 的 Prometheus 指标采集逻辑；删除 `prometheus_client` stub；同步更新 `requirements-prod.txt` 与相关文档；跑 `make typecheck` + unit tests 验证不回归。

**Tech Stack:** Python 3.11 + Flask + SQLAlchemy + Pyright + pytest。

---

### Task 1: 引用审计（确保无遗漏）

**Files:**
- Modify: `docs/Obsidian/reference/service/account-classification-dsl-v4.md`
- Modify: `docs/Obsidian/reference/service/accounts-sync-permission-manager.md`
- Modify: `requirements-prod.txt`
- Delete: `app/core/types/stubs/prometheus_client/__init__.pyi`
- Modify: `app/utils/account_classification_dsl_v4.py`
- Modify: `app/services/accounts_sync/permission_manager.py`

**Step 1: 搜索 prometheus 相关引用**

Run:
```bash
rg -n "prometheus(_client)?|prometheus-client" -S .
```

Expected: 仅定位到当前 Prometheus 指标逻辑 + requirements + docs + stubs。

---

### Task 2: 移除 DSL v4 的 Prometheus 指标逻辑

**Files:**
- Modify: `app/utils/account_classification_dsl_v4.py`

**Step 1: 删除可选依赖与指标代码**

移除：
- `prometheus_client` 的 try/except import
- `_NoopMetric`、`_build_counter/_build_histogram`
- `dsl_evaluation_duration/dsl_evaluation_errors`
- `_record_error` 与 `_eval_fn` 中的 metrics 记录（含 `suppress(ValueError)`）
- 同步清理无用 import（`time`、`suppress` 等）

**Step 2: 运行相关单测（快速回归）**

Run:
```bash
uv run pytest -m unit tests/unit/services/test_account_classification_dsl_v4.py -q
```

Expected: PASS

---

### Task 3: 移除 Accounts Sync Permission Manager 的 Prometheus 指标逻辑

**Files:**
- Modify: `app/services/accounts_sync/permission_manager.py`

**Step 1: 删除可选依赖与指标代码**

移除：
- `prometheus_client` 的 try/except import
- `_NoopMetric`、`_build_counter/_build_histogram`
- `snapshot_write_success/snapshot_write_failed/snapshot_build_duration`
- 写快照时的 `inc/observe` 调用及仅用于指标的计时变量

**Step 2: 运行相关单测（快速回归）**

Run:
```bash
uv run pytest -m unit tests/unit/services/accounts_sync -q
```

Expected: PASS

---

### Task 4: 删除 prometheus_client stubs 并移除生产依赖

**Files:**
- Delete: `app/core/types/stubs/prometheus_client/__init__.pyi`
- Modify: `requirements-prod.txt`

**Step 1: 删除 stubs 目录**

Run:
```bash
rm -rf app/core/types/stubs/prometheus_client
```

Expected: 目录不存在；其余 stubs（pytest/sqlalchemy）保留。

**Step 2: 从生产依赖移除 prometheus-client**

在 `requirements-prod.txt` 删除：
- `prometheus-client==0.19.0`

---

### Task 5: 更新文档与全量验证

**Files:**
- Modify: `docs/Obsidian/reference/service/account-classification-dsl-v4.md`
- Modify: `docs/Obsidian/reference/service/accounts-sync-permission-manager.md`

**Step 1: 文档去掉 Prometheus 指标描述**

将文档中关于 `prometheus_client` 可选指标采集的内容删除或改为“不再使用”。

**Step 2: 全量验证**

Run:
```bash
make format
make typecheck
uv run pytest -m unit -q
```

Expected: 全部通过。

