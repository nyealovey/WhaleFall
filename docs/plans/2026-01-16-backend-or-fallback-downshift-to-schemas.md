# Backend `or` Fallback Downshift To Schemas Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan.

**Goal:** 将“数据结构兼容/默认值/字段别名/迁移”从 `app/services/**` / `app/repositories/**` 收敛到 `app/schemas/**`（Pydantic v2 单入口 canonicalization），系统性降低 `or` truthy 兜底链带来的语义漂移风险，并为兼容分支建立可测试、可退出的迁移路径。

**Architecture:**
- **写路径**：`parse_payload(...)` 只做“取参形状 + 基础 sanitize”；业务语义默认值/字段 alias/形状迁移/类型规整全部下沉到 `PayloadSchema`（Pydantic v2）。Service 入口第一步 `validate_or_raise(...)`，之后只消费 typed payload。
- **读路径 / internal contract**（snapshot/cache/JSON column）：在读入口建立 `adapter/normalizer`（`app/schemas/internal_contracts/**`），以 `version` 驱动迁移；未知版本默认 fail-fast，best-effort 链路必须返回 `InternalContractResult(ok=false, ...)`，禁止 `{}`/`[]` silent fallback。
- **外部依赖/采集 adapter**：把外部驱动返回的“脏 dict”解析/默认值/兼容收敛到 `app/schemas/**` 的 adapter schema（建议 `app/schemas/external_contracts/**`），service/adapter 层只处理 IO 与编排。

**Tech Stack:** Python 3.11, Pydantic v2 (`pydantic==2.12.5`), `app/utils/request_payload.py::parse_payload`, `app/schemas/validation.py::validate_or_raise`, `pytest -m unit`, Ruff, Pyright.

---

## 当前进度（截至 2026-01-17）

> 依据 `git log`（最新 commit: `c9243578`）与文件现状整理；本节作为“推进记录 + 下一步入口”。

- ✅ Task 1（可复跑扫描基线）：已落地 `scripts/audits/python_or_fallback_scan.py` + `docs/plans/2026-01-16-or-fallback-baseline.md`。
- ✅ Task 2（决策表 + 门禁脚本）：已落地 `docs/Obsidian/standards/backend/or-fallback-decision-table.md` 与 `scripts/ci/or-fallback-pattern-guard.sh`，并已接入 pre-commit（本次补齐）。
- ✅ Task 3（internal contract 未知版本 silent fallback）：`permission_snapshot(v4)` 已拆分 categories/type_specific 的 `parse/normalize` 单入口；业务层不再 `return {}`/`[]` 继续消费，而是把 contract error 记录到 `meta/errors` 并保持输出稳定（best-effort 链路）。本次补齐 schema 层的 type_specific 单测。
- ✅ Task 4（外部 account adapter 下沉）：`app/schemas/external_contracts/*_account.py` 已建立并在各 adapter 中使用，unit tests 已覆盖缺失/空 dict/非法 shape 等关键场景。
- ✅ Task 5（写路径 `payload or {}` 清理）：`parse_payload(payload or {})` 形态在 `app/services/**` 已清零（可用 `rg` 验证）。
- ✅ Task 6（目录治理 Batch）：已完成多批“query 参数规范化下沉到 schema”（instances/capacity/databases + history_sessions + credentials + users + partition + tags + accounts + history_logs 等）。`python_or_fallback_scan.py` 在：
  - `app/api/v1/namespaces/**` 的 `or` chains/candidate 已清零（验收点：API query 入口不再出现 truthy 兜底链）。
  - `app/services/**` / `app/repositories/**` 的 `""/0/False/[]/{}` 候选链已清零（验收点：业务层不再通过 `or` 覆盖合法 falsy 值）。
  - 其中 `... or {}` / `... or []` 已清零，并已纳入 `scripts/ci/or-fallback-pattern-guard.sh` 门禁，防止回归。
  - 复跑命令：
    - `uv run python scripts/audits/python_or_fallback_scan.py --paths app/api/v1/namespaces --exclude 'tests/**' --format json`
    - `uv run python scripts/audits/python_or_fallback_scan.py --paths app/services app/repositories --exclude 'tests/**' --format json`
- ✅ Task 7（internal contract version/backfill）：已对 `sync_details` / `account_change_log_diff` / `account_permission.type_specific` 等 internal payload 引入 version + backfill（见 `da2449e3`/`d470b52f`/`524b97eb`）。

建议下一步（低风险、高收益顺序）：
1) 将 `python_or_fallback_scan.py` 的输出纳入 CI 产物（保留趋势），并用 `or-fallback-pattern-guard.sh` 保证“高风险形态不回归”。
2) 评估是否需要进一步收敛 `or_chains_total`（不含 falsy 候选的纯布尔/短路用法），避免把“规约治理”扩大为“机械消灭 or”。

## 背景与问题定义

- 审计报告 `docs/reports/2026-01-15-backend-standards-audit-report.md` 的 AST 统计：
  - `or` 兜底链（非 test）658 处。
  - 其中包含 `""/0/False/[]/{}` 的候选 381 处（`app/services/**` 206，`app/repositories/**` 78，`app/api/**` 50 ...）。
- 风险核心不是“用了 or”，而是 **truthy 兜底把合法 falsy 值覆盖**（例如 `""` 可能是合法输入、`0` 可能是合法数值、`[]` 可能代表“显式清空”）。
- 当前问题形态（优先处理）：
  - `data.get("new") or data.get("old")`：字段 alias/迁移散落在 service/repo。
  - `payload or {}` / `result or []`：把“缺失/None/空集合”混为一谈，语义不透明。
  - internal payload 缺失/未知版本时 silent fallback 为 `{}`：违反 internal contract 标准。

本方案与标准对齐：
- `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md`
- `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md`
- `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md`

---

## 统一约定（重构期间必须遵守）

### 1) 语义优先：明确区分三类“空”

- **缺失**：key 不存在（应由 schema 默认值处理）。
- **显式提供但为空**：例如 `""`、`[]`、`{}`（是否允许/是否代表“清空”必须按字段定义）。
- **None**：通常代表“缺省/未知”（与缺失是否等价必须按字段定义）。

> 重构目标不是“消灭所有 `or`”，而是让“默认值/兼容/迁移”变成 **可读、可测试、可退出** 的单入口策略。

### 2) `or` 兜底的替代写法（强制风格）

- 当合法值可能为 `0/""/[]/{}`：
  - 禁止：`value or default`
  - 使用：
    - **缺失默认**：交给 Pydantic 字段默认值（`field: T = default` / `default_factory`）
    - **None 默认**：`default if value is None else value`
    - **显式缺失判定**：`if key not in data: ...`
- 当语义为“空白视为缺省”：允许在 schema/adapter 单入口使用 `cleaned = raw.strip(); cleaned or None`，并补单测。

### 3) Schema/Adapter 的退出机制（防止永久化）

- 每个兼容分支必须：
  - 有单测覆盖（旧形状/旧字段名仍可解析）。
  - 记录可移除条件（建议用 `EXIT:` 注释 + 关联迁移任务/数据回填完成信号）。
- internal contract：必须可枚举支持版本集合；未知版本不得 silent fallback。

---

## 迁移蓝图（按层拆包）

### A. 写路径（HTTP payload）

目标：Service 内不再出现 `data.get(...) or ...` 的字段兼容链；默认值/alias/迁移全部在 `PayloadSchema` 内。

推荐模式：
- 只在 service 入口做一次：
  - `sanitized = parse_payload(payload, ...)`
  - `parsed = validate_or_raise(SomePayload, sanitized)`
- update/patch 语义：通过 `parsed.model_fields_set` 判断字段是否“被显式提供”。

典型替代：
```py
from pydantic import BaseModel, Field, AliasChoices

class ExamplePayload(BaseModel):
    # 新字段优先，其次旧字段
    name: str = Field(validation_alias=AliasChoices('name', 'legacy_name'))

    # 缺失 -> 默认；显式传 0 会保留 0
    limit: int = 100

    # list 默认必须用 default_factory
    tags: list[str] = Field(default_factory=list)
```

### B. internal contract（snapshot/cache/JSON column）

目标：读入口单入口 canonicalization；service/repo 不再拼兼容链。

推荐组织：
- `app/schemas/internal_contracts/<contract>_vN.py`
  - `parse_<contract>(payload) -> InternalContractResult`
  - `normalize_<contract>(...) -> canonical dict`
- best-effort 调用者必须检查 `ok`；`ok=false` 时不得继续把 `data` 当作有效 payload 消费（应记录错误并以显式错误结构/字段返回），禁止 `{}`/`[]` silent fallback。

### C. 外部依赖/采集 adapter

目标：外部 dict -> 内部 canonical typed model（或 canonical dict）

建议新增目录：
- `app/schemas/external_contracts/**`
  - 命名：`<source>_<domain>.py`（例如 `mysql_account.py`）
  - 仅依赖 `pydantic` + `app.core.constants/types/utils`（禁止依赖 models/services/repositories/db）

---

## Task 1: 建立可复跑的 `or` 兜底扫描基线（强烈建议先做）

**Files:**
- Create: `scripts/audits/python_or_fallback_scan.py`
- Create: `scripts/audits/README.md`

**Step 1: 新增 AST 扫描脚本（输出 JSON + Markdown）**
- 目标：在重构过程中可以持续量化：
  - 总 `or` 兜底链数量
  - “包含 `""/0/False/[]/{}` 的候选”数量
  - 目录分布/Top 文件分布

脚本最小输出（建议）：
- `--format json|md`
- `--exclude "tests/**"`
- `--paths app/services app/repositories app/api app/utils app/routes`

**Step 2: 运行基线并保存到 plans 目录（便于对照）**
- Run:

```bash
uv run python scripts/audits/python_or_fallback_scan.py --paths app --exclude 'tests/**' --format md > docs/plans/2026-01-16-or-fallback-baseline.md
```

Expected:
- 输出中至少包含与审计报告同口径的统计（658/381 的级别量级允许因忽略规则差异略有偏移，但目录分布应相近）。

---

## Task 2: 明确“哪些 `or` 必须下沉到 schema/adapter”并建立门禁规则

**Files:**
- Modify: `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md`
- Create: `docs/Obsidian/standards/backend/or-fallback-decision-table.md`
- Create: `scripts/ci/or-fallback-pattern-guard.sh`

**Step 1: 写决策表（单一真源）**
- 文档必须包含：
  - 允许 `or` 的场景（例如 `"" -> None` 的 canonicalization，仅限 schema/adapter）
  - 禁止 `or` 的场景（合法 falsy 被覆盖）
  - 推荐替代写法（默认值/`is None`/`key in dict`/Pydantic default）

**Step 2: 增加 pattern guard（只门禁高风险形态）**
- 初期只禁用：
  - `app/services/**` / `app/repositories/**` 中的 `get("new") or get("old")`
  - internal contract 相关模块中 `version` 不匹配时返回 `{}`/`[]`

示例（仅示意）：
```bash
rg -n "get\(\"[\w_]+\"\)\s*or\s*.*get\(\"[\w_]+\"\)" app/services app/repositories && exit 1 || exit 0
```

---

## Task 3: 先修 P0：internal payload 未知版本 `{}` silent fallback

**Files:**
- Modify: `app/services/accounts_permissions/facts_builder.py`
- Modify: `app/schemas/internal_contracts/permission_snapshot_v4.py`
- Test: `tests/unit/**`（新增对应测试文件）

**Step 1: 为 type_specific 增加与 categories 一致的 parse/normalize 单入口**
- 在 `app/schemas/internal_contracts/permission_snapshot_v4.py` 增加：
  - `parse_permission_snapshot_type_specific_v4(snapshot) -> InternalContractResult`
  - `normalize_permission_snapshot_type_specific_v4(db_type, type_specific) -> dict`

**Step 2: 在 `facts_builder` 中替换 `_extract_snapshot_type_specific` 的 `{}` fallback**
- 从：
  - `if snapshot.get("version") != 4: return {}`
- 改为：
  - 调用 parse 函数；`ok=false` 时不得继续把 data 当作有效 payload 消费（best-effort 链路可将错误写入 `meta/errors` 并保持返回结构稳定），禁止 `return {}`/`[]` 静默兜底后继续执行。

**Step 3: 补单测**
- 覆盖：
  - v4 正常输入
  - version 缺失/非 int
  - version != 4

**Step 4: 验证**
- Run:

```bash
uv run pytest -m unit
```

---

## Task 4: 外部 MySQL account 适配：把 `account.get(... ) or {}` 下沉到 schema

**Files:**
- Create: `app/schemas/external_contracts/mysql_account.py`
- Modify: `app/services/accounts_sync/adapters/mysql_adapter.py`
- Test: `tests/unit/services/accounts_sync/**`

**Step 1: 新增 RawAccount schema（仅负责“解析 + 默认值 + 形状规整”）**
- 约束：
  - 缺失字段默认值在 schema 内定义；禁止 adapter/service 层 `or {}`。
  - 当字段允许显式空 dict/list 时，禁止把“缺失”和“显式空”合并。

**Step 2: 在 adapter 中调用 `model_validate` 后再构造 `RemoteAccount`**
- 目标：adapter 不再处理 dict 兼容链，只做 IO 与映射。

**Step 3: 补单测**
- 覆盖至少：
  - permissions 缺失
  - permissions 为 `{}`
  - type_specific 缺失/非 dict
  - username 包含 `@` 的拆分逻辑仍正确

---

## Task 5: 清理写路径 service 的 `payload or {}`（收敛到 `parse_payload(payload)` + schema 默认）

**Files:**
- Modify: `app/services/**`（按扫描结果逐个替换）
- Test: `tests/unit/**`

**Step 1: 机械替换（先做最安全的一类）**
- 从：`sanitized = parse_payload(payload or {})`
- 改为：`sanitized = parse_payload(payload)`

理由：`parse_payload(None) -> {}` 已定义；`payload or {}` 只会引入“空 dict 与 None 合并”的语义噪音。

**Step 2: 对“空 dict 代表显式清空”的接口做补充约定**
- 如果存在业务语义：空 dict == 清空，则必须：
  - schema 明确区分（通过 Optional + validator 或 `model_fields_set`）；
  - service 里按 `model_fields_set` 驱动写入。

**Step 3: 回归测试**
- Run:

```bash
uv run pytest -m unit
make typecheck
./scripts/ci/ruff-report.sh style
```

---

## Task 6: 分批“目录治理”（把高风险兼容链从 service/repo 推到 schema）

> 建议按“Top 文件”推进：每批只做 1 个域，确保单测覆盖 + 扫描指标可下降。

**Batch 选择建议（按审计分布）：**
- Batch 1: `app/services/**` 中出现 `get("new") or get("old")` / `dict.get(...) or {}` 的文件
- Batch 2: `app/repositories/**` 中“payload 形状兼容”的文件（优先，不优先动数值 `or 0`）
- Batch 3: `app/api/**` query 参数规范化（例如 `parsed.get("search") or ""`）

**每个 Batch 的 Done 标准：**
- 兼容/迁移逻辑已移动到 `app/schemas/**`
- service/repo 内不再出现对应兼容链形态
- 单测覆盖（至少：旧字段/旧形状仍可解析；未知版本/非法形状 fail-fast 或显式错误结果）
- `python_or_fallback_scan.py` 的“候选数”与“高风险形态”下降（允许总量暂不下降，但高风险必须下降）

---

## Task 7: 数据回填与兼容退出（真正“破坏性”的部分）

**Files:**
- Create: `app/tasks/**`（回填任务）
- Create: `scripts/backfill/**`（一次性脚本，可选）
- Modify: `migrations/**`（仅当需要新增字段/索引；禁止修改历史迁移）

**Step 1: 为需要长期存储/跨模块消费的 JSON payload 增加显式 `version`（若尚未具备）**
- 写入端只写最新版本。

**Step 2: 提供回填任务把历史数据升级到最新版本**
- 关键：回填完成后才能删除 schema 内的历史兼容分支（EXIT）。

**Step 3: 删除兼容分支**
- 删除条件必须可判定（例如：回填任务完成标记 + 线上观察窗口结束）。

---

## Task 8: 验证与发布策略

**Step 1: 全量验证**
- Run:

```bash
uv run pytest -m unit
make typecheck
./scripts/ci/ruff-report.sh style
```

**Step 2: 指标验收（必须落到可量化）**
- `scripts/audits/python_or_fallback_scan.py` 输出：
  - `get("new") or get("old")` 形态在 `app/services/**`/`app/repositories/**` 命中数为 0
  - internal contract 未知版本 silent fallback 命中数为 0
  - “候选 381”应显著下降（目标值按批次推进，不要求一次归零）

**Step 3: 破坏性变更的发布说明**
- 如果对外接口语义发生改变（例如空字符串不再等价于缺失），必须：
  - 在 `docs/` 写清“行为变更点”与迁移建议
  - 提供回滚方案（至少说明：如何临时恢复旧行为/如何回退数据）

---

## 执行建议（避免一把梭）

- 先做 Task 1/2：没有可复跑扫描与门禁，重构很容易“做了很多但不可验证”。
- 每批只收敛一个域：把风险控制在单测可覆盖的范围内。
- 只对“兼容/迁移/默认值语义不清”的 `or` 下手；纯数值 `or 0` 若类型已保证可先不动，避免把重构变成“机械换写法”。
