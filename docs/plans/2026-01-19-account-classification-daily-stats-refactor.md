# Account Classification Daily Stats + Rule Versioning Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 新增“按规则评估命中(B口径)”的每日统计能力，并引入“分类 code/display_name”与“规则不可变版本化”，保证历史统计口径稳定；支持按「分类/规则/db_type/instance」组合查询；同一天多次执行仅保留最后一次结果。

**Architecture:**
- **统计与分配解耦**：每日统计按“规则表达式评估为 True 的账户数”计算，不依赖最终 `assignments` 写入形态。
- **规则不可变**：更新规则不再 UPDATE 原记录；改为新增新版本(新 `rule_id`)，旧版本自动归档(`is_active=false`)。
- **分类稳定口径**：分类引入 `code`(不可变) + `display_name`(可改)，后续统计/规则引用以 `code/id` 为稳定口径。
- **每日聚合表**：
  - `daily_rule_match_stats`：维度到 `(date, rule_id, db_type, instance_id)`，存“规则命中数”。
  - `daily_classification_match_stats`：维度到 `(date, classification_id, db_type, instance_id)`，存“分类命中去重账号数”。
- **幂等与一天只留最后一次**：两张日表均以唯一键 upsert 覆盖(同一天多次运行写入同一键)，实现“最后一次覆盖”。

**Tech Stack:** Flask, SQLAlchemy, Alembic, APScheduler, Pydantic v2, pytest (`uv run pytest -m unit`).

---

## 需求推演：四种统计查询是否可实现

结论：全部可实现，且无需依赖 `assignments` 的最终归因。

1) **某一个分类的日统计**
- 口径：分类命中去重账号数
- 数据来源：`daily_classification_match_stats`，按 `stat_date` 聚合

2) **某一个分类 + 某一条规则 的日统计**
- 口径：该规则表达式命中账号数(评估 True)
- 数据来源：`daily_rule_match_stats`，过滤 `classification_id + rule_id`

3) **某一个分类 + 某一条规则 + 某一个 db_type 的日统计**
- 数据来源：`daily_rule_match_stats`，额外过滤 `db_type`

4) **某一个分类 + 某一条规则 + 某一个 db_type + 某一个 instance 的日统计**
- 数据来源：`daily_rule_match_stats`，额外过滤 `instance_id`

> 说明：规则不可变后，`rule_id` 天然代表“特定逻辑版本”，避免“同一个 rule_id 被 update 后口径变化”导致历史趋势混淆。

---

## 统一口径定义(必须写入文档与测试)

- **规则日统计(B口径)**：对每条规则，统计“当日评估命中的账户数”。
  - 允许规则之间重叠：同一账号可被多条规则同时计数。
  - 与 `assignments` 最终写入/覆盖无关。

- **分类日统计(去重口径)**：对每个分类，统计“当日命中该分类任意规则的账号去重数”。
  - 若一个账号命中该分类下多条规则，只计 1 次。

- **时区与日期切分**：`stat_date` 以 `Asia/Shanghai` 的“当天日期”为准(与调度器一致)。

- **一天只记录最后一次**：同一天同一维度键的统计被后一次执行覆盖(覆盖策略必须单测)。

---

## 数据模型变更

### 1) 分类：`account_classifications`

目标：支持 `code/display_name`。

- 现状：仅有 `name`(唯一) 作为名称。
- 方案：
  - 保留列名 `name`，语义升级为 `code`(不可变，唯一)。
  - 新增列 `display_name`(可改，仅展示)。
  - 迁移期兼容：若 `display_name` 为空则展示 `name`。

建议约束：
- `name`(code) 创建后不可改；`display_name` 可改。

### 2) 规则：`classification_rules`

目标：规则不可变版本化。

新增字段建议：
- `rule_group_id` (String(36) / UUID)：同一规则的版本组
- `rule_version` (int)：版本号，从 1 开始递增
- `superseded_at` (timestamptz, nullable)：被替代时间(可选)

约束建议：
- Unique(`rule_group_id`, `rule_version`)
- Index(`rule_group_id`)

写入策略：
- PUT 更新规则 => 新建一条 `ClassificationRule`：
  - `rule_group_id` 复用旧规则
  - `rule_version = old.rule_version + 1`
  - 旧规则 `is_active=false`，可选写 `superseded_at`

### 3) 每日统计表

#### 3.1 `account_classification_daily_rule_match_stats`

用途：规则命中数(B口径)，维度到 instance。

字段建议：
- `stat_date` (Date)
- `rule_id` (int)
- `classification_id` (int)  # snapshot 维度，便于联查
- `db_type` (String(20))
- `instance_id` (int)
- `matched_accounts_count` (int)
- `computed_at` (timestamptz)
- `rule_snapshot` (JSON/Text，可选，包含 rule_name/expression 等展示字段)
- `classification_snapshot` (JSON/Text，可选，包含 code/display_name)

唯一键(实现“只留最后一次”)：
- Unique(`stat_date`, `rule_id`, `db_type`, `instance_id`)

#### 3.2 `account_classification_daily_classification_match_stats`

用途：分类命中去重账号数。

字段建议：
- `stat_date` (Date)
- `classification_id` (int)
- `db_type` (String(20))
- `instance_id` (int)
- `matched_accounts_distinct_count` (int)
- `computed_at` (timestamptz)
- `classification_snapshot` (JSON/Text，可选)

唯一键：
- Unique(`stat_date`, `classification_id`, `db_type`, `instance_id`)

---

## 调度与触发

新增 APScheduler 任务：每日执行“自动分类统计”。

约束(来自标准)：
- 任务函数必须在 `app.app_context()` 内执行(参见 `docs/Obsidian/standards/backend/task-and-scheduler.md`)。
- 新增任务需同时更新：
  - `app/scheduler.py::TASK_FUNCTIONS`
  - `app/config/scheduler_tasks.yaml`

建议任务：
- `id`: `collect_account_classification_daily_stats`
- `function`: `app.tasks.account_classification_daily_tasks:collect_account_classification_daily_stats`

是否同时执行“分配写入”(assignments)：本计划默认先实现“统计”，并把“最终 assignments 写入形态”的优化留作后续独立任务(避免把两个变量耦合在一次重构中)。

---

## API/查询接口(建议)

为满足“临时任务按条件查询”与“趋势展示”，建议新增只读接口：

- `GET /api/v1/accounts/statistics/classifications/daily`
  - query: `classification_id`(required), `date_from`, `date_to`, `db_type`, `instance_id`
  - 返回：按日数组(含可选维度)

- `GET /api/v1/accounts/statistics/rules/daily`
  - query: `rule_id`(required), `classification_id`(optional but recommended), `date_from`, `date_to`, `db_type`, `instance_id`
  - 返回：按日数组

> 如果你更希望先不加 API，只落表 + 用 SQL/报表工具读，也可把本节延后。

---

## 迁移与兼容策略

### 1) 分类兼容

- DB：新增 `display_name` 并回填 `display_name = name`。
- 写路径：
  - create 支持 `code`(alias `name`) + `display_name`。
  - update 禁止修改 `code`(即 `name`)；允许修改 `display_name`。
- 读路径：
  - 列表/详情 DTO 增加 `code`/`display_name` 字段；旧字段 `name` 逐步下线(保留一段兼容期)。

### 2) 规则版本化兼容

- DB：对现有每条规则生成：`rule_group_id = uuid4()`，`rule_version=1`。
- 写路径：
  - PUT 更新规则返回 `new_rule_id`(以及新规则详情)，前端/调用方需切换到新 id。
  - 旧规则保留可读(用于历史统计/回溯)，但默认不出现在“active rules 列表”。

---

## 验收标准(Definition of Done)

- 能生成并写入两张日表；同一天重复执行会覆盖而不是累加。
- 支持四类查询维度组合(分类 / 分类+规则 / +db_type / +instance)。
- 规则 update 会生成新 `rule_id`；旧规则 `is_active=false`；历史统计仍可按旧 `rule_id` 查询。
- 分类支持 `code/display_name`；`code` 创建后不可改(服务层校验 + unit test)。

---

## 重构进度表(建议里程碑)

| 里程碑 | 内容 | 关键产出 | 依赖 | 预计 | 状态 |
| --- | --- | --- | --- | --- | --- |
| M1 | 分类 code/display_name + code 不可改 | migration + schema/service + unit tests | 无 | 0.5-1d | TODO |
| M2 | 规则不可变版本化 | migration + update_rule 改造 + API 返回 new_rule_id + unit tests | M1 | 1-2d | TODO |
| M3 | 日统计表落地 | 2 张日表 migration + model | M2 | 0.5-1d | TODO |
| M4 | 规则命中统计计算引擎 | service + repository(upsert) + unit tests | M3 | 1-2d | TODO |
| M5 | 定时任务接入调度器 | task + scheduler 注册 + 可手动 run | M4 | 0.5d | TODO |
| M6 | 查询接口(API 可选) | read service + routes + contract tests | M4 | 1d | OPTIONAL |
| M7 | 文档/验收/回滚说明 | docs + runbook | 全部 | 0.5d | TODO |

---

# Implementation Tasks (TDD, bite-sized)

### Task 1: 分类 code/display_name

**Files:**
- Modify: `app/models/account_classification.py`
- Modify: `app/schemas/account_classifications.py`
- Modify: `app/services/accounts/account_classifications_write_service.py`
- Modify: `app/services/accounts/account_classifications_read_service.py`
- Create: `migrations/versions/YYYYMMDDHHMMSS_add_account_classification_display_name.py`
- Test: `tests/unit/services/test_account_classification_write_service.py`

**Step 1: Write failing tests (code immutable + display_name supported)**

在 `tests/unit/services/test_account_classification_write_service.py` 新增用例(伪代码示例)：
```python
def test_update_classification_rejects_code_change(app, db_session):
    # create classification(name as code)
    # call update with payload {"code": "new"} or {"name": "new"}
    # assert raises ValidationError(message_key="FORBIDDEN" or "VALIDATION_ERROR")
    ...
```

**Step 2: Run tests to see them fail**

Run: `uv run pytest -m unit tests/unit/services/test_account_classification_write_service.py -q`
Expected: FAIL (display_name/code logic not implemented)

**Step 3: Implement minimal code**

- `app/models/account_classification.py`: add column `display_name` + update `to_dict()` include `display_name`/`code`.
- `app/schemas/account_classifications.py`:
  - create payload: accept `code`(alias `name`) + optional `display_name`.
  - update payload: allow `display_name`; if payload contains `code`/`name` -> raise.
- `app/services/accounts/account_classifications_write_service.py`: update_classification 禁止改 code.

**Step 4: Run tests to pass**

Run: `uv run pytest -m unit tests/unit/services/test_account_classification_write_service.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/models/account_classification.py app/schemas/account_classifications.py app/services/accounts/account_classifications_write_service.py app/services/accounts/account_classifications_read_service.py migrations/versions/* tests/unit/services/test_account_classification_write_service.py
git commit -m "feat: add classification display_name and lock code"
```

---

### Task 2: 规则不可变版本化(新版本 rule_id)

**Files:**
- Modify: `app/models/account_classification.py`
- Modify: `app/schemas/account_classifications.py`
- Modify: `app/services/accounts/account_classifications_write_service.py`
- Modify: `app/api/v1/namespaces/accounts_classifications.py`
- Create: `migrations/versions/YYYYMMDDHHMMSS_add_classification_rule_versioning.py`
- Test: `tests/unit/services/test_classification_rule_write_service.py`

**Step 1: Write failing tests (PUT update creates new rule)**

在 `tests/unit/services/test_classification_rule_write_service.py` 增加：
```python
def test_update_rule_creates_new_version(app, db_session):
    # create rule v1
    # call update_rule(v1, payload)
    # assert: old_rule.is_active == False
    # assert: new_rule.id != old_rule.id
    # assert: new_rule.rule_group_id == old_rule.rule_group_id
    # assert: new_rule.rule_version == old_rule.rule_version + 1
    ...
```

**Step 2: Run tests to fail**

Run: `uv run pytest -m unit tests/unit/services/test_classification_rule_write_service.py -q`
Expected: FAIL

**Step 3: Implement minimal code**

- migration: add `rule_group_id`, `rule_version`, `superseded_at` and backfill existing rules (`rule_version=1`, group_id random per row).
- write service: `update_rule` 改为创建新记录 + 旧记录归档。
- API: `PUT /rules/<rule_id>` 返回 `new_rule_id`(至少要让前端能拿到新 id)。

**Step 4: Run tests**

Run: `uv run pytest -m unit -q`
Expected: PASS

**Step 5: Commit**

```bash
git add app/models/account_classification.py app/schemas/account_classifications.py app/services/accounts/account_classifications_write_service.py app/api/v1/namespaces/accounts_classifications.py migrations/versions/* tests/unit/services/test_classification_rule_write_service.py
git commit -m "feat: version classification rules as immutable records"
```

---

### Task 3: 日统计表 migration + model

**Files:**
- Create: `app/models/account_classification_daily_stats.py`
- Modify: `app/models/__init__.py` (如需导出)
- Create: `migrations/versions/YYYYMMDDHHMMSS_add_account_classification_daily_stats_tables.py`
- Test: `tests/unit/routes/test_api_v1_accounts_statistics_contract.py` (仅表结构存在性)

**Step 1: Add contract test for new tables in metadata**

**Step 2: Run failing test**

**Step 3: Add models + migration**

**Step 4: Run tests**

**Step 5: Commit**

---

### Task 4: 规则命中统计计算(含分类去重)

**Files:**
- Create: `app/services/account_classification/daily_stats_service.py`
- Create: `app/repositories/account_classification_daily_stats_repository.py`
- Test: `tests/unit/services/test_account_classification_daily_stats_service.py`

**Core algorithm (must match口径):**
- 遍历 active rules
- 对每条 rule：按 `db_type` 过滤候选账户；逐个 evaluate DSL v4；命中则计入 `(rule_id, db_type, instance_id)`
- 同时维护 `classification_id` 维度的去重集合：`(classification_id, db_type, instance_id) -> set(account_id)`
- 最终写入：
  - rule stats: `matched_accounts_count = count`
  - classification stats: `matched_accounts_distinct_count = len(set)`

---

### Task 5: 定时任务接入

**Files:**
- Create: `app/tasks/account_classification_daily_tasks.py`
- Modify: `app/scheduler.py`
- Modify: `app/config/scheduler_tasks.yaml`
- Modify: `app/core/constants/scheduler_jobs.py`

要求：
- 任务函数内部自行 `create_app(init_scheduler_on_start=False)` 并包裹 `app.app_context()`。
- 任务可被 scheduler “立即执行(run)”手动触发，并覆盖同日统计。

---

### Task 6 (Optional): 提供统计查询 API

**Files:**
- Modify: `app/api/v1/namespaces/accounts.py`
- Create: `app/services/accounts/account_classification_daily_stats_read_service.py`
- Create: `app/repositories/account_classification_daily_stats_read_repository.py`
- Test: `tests/unit/routes/test_api_v1_accounts_statistics_contract.py`

---

### Task 7: 文档与运维

- 更新标准/说明：新增本能力的“口径说明 + 查询示例 SQL + 回滚策略”。

