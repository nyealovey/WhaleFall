# Backend P2: Structured Logging + YAML Config Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 补齐“结构化日志最小字段 schema + 可验证门禁”，并对 YAML 配置读取入口引入一次性校验/规范化，减少运行期散落的 `or` 兜底链。

**Architecture:**  
1) 日志：以 `app/models/unified_log.py::LogEntryParams` 与 `app/utils/logging/handlers.py::_build_log_entry` 为单一真源，文档化最小字段集合，并用单测固化输出结构。  
2) YAML 配置：为 `scheduler_tasks.yaml`、`account_filters.yaml`、`database_filters.yaml` 建立 pydantic schema，在读取入口完成一次性 canonicalization/校验后再下发给业务逻辑。

**Tech Stack:** Python, pydantic, PyYAML, pytest(unit)

---

### Task 1: 结构化日志最小字段 schema + 门禁

**Files:**
- Create: `docs/Obsidian/standards/backend/structured-logging-minimum-fields.md`
- Test: `tests/unit/utils/test_structlog_log_entry_schema.py`

**Step 1:** 定义最小字段集合（`timestamp/level/module/message/context/traceback`）与来源（`_build_log_entry`）。  
**Step 2:** 单测覆盖 `_build_log_entry` 对不同输入形态的稳定输出与 debug drop 行为。

---

### Task 2: YAML 配置 pydantic schema

**Files:**
- Create: `app/schemas/yaml_configs.py`

**Step 1:** 定义 `SchedulerTasksConfigFile` / `SchedulerTaskConfig`。  
**Step 2:** 定义 `AccountFiltersConfigFile` / `AccountFilterRuleConfig`（仅固化必须字段，其余 `extra="ignore"`）。  
**Step 3:** 定义 `DatabaseFiltersConfigFile` / `DatabaseFilterRuleConfig`（同上）。

---

### Task 3: 改造 YAML 读取入口（只做一次 canonicalization）

**Files:**
- Modify: `app/scheduler.py`
- Modify: `app/services/accounts_sync/accounts_sync_filters.py`
- Modify: `app/services/database_sync/database_filters.py`

**Step 1:** scheduler 默认任务读取：`safe_load -> schema 校验 -> 产出 typed config -> 注册任务`。  
**Step 2:** filters：`safe_load -> schema 校验 -> 产出标准化 rules -> 业务侧只消费已规整结构`。

---

### Task 4: 单测 + 验证

**Files:**
- Test: `tests/unit/services/test_yaml_config_validation_scheduler_tasks.py`
- Test: `tests/unit/services/test_yaml_config_validation_filters.py`

**Step 1:** 覆盖“缺 key/类型错误/空文件”等失败场景与错误信息。  
**Step 2:** 运行 `uv run pytest -m unit` 确保门禁通过。

