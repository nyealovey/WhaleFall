# Code Simplicity Review (Audit)

生成时间：2026-01-28 13:57:21 CST  
范围：`/Users/apple/Github/WhaleFall`（代码 + 测试 + scripts + 文档）  
原则：最小化 / YAGNI / 去重样板（以“删减维护负担”为第一目标）  

## 证据（原始输出）

- 单测：`docs/reports/artifacts/pytest_unit_2026-01-28_134833.txt`
- CI guards（含 stderr）：`docs/reports/artifacts/ci-guards_2026-01-28_134740_stderr.txt`
- Ruff（quick/style/security）：  
  - `docs/reports/ruff_quick_2026-01-28_134524.txt`  
  - `docs/reports/ruff_style_2026-01-28_134530.txt`  
  - `docs/reports/ruff_security_2026-01-28_134543.txt`
- Pyright：`docs/reports/pyright_full_2026-01-28_134551.txt`
- ESLint（quick/full，均为空）：  
  - `docs/reports/eslint_quick_2026-01-28_134609.txt`  
  - `docs/reports/eslint_full_2026-01-28_134626.txt`
- 命名门禁：`docs/reports/naming_guard_report.txt`
- 文本扫描：  
  - `docs/reports/artifacts/todo_fixme_first_party_2026-01-28_134944.txt`  
  - `docs/reports/artifacts/legacy_deprecated_2026-01-28_134955.txt`

---

## Simplification Analysis

### Core Purpose

鲸落（WhaleFall）的核心目的：为 DBA 团队提供数据库资源（实例/账户/容量/调度）的统一管理与审计能力（Flask 后端 + 调度任务 + Web UI + `/api/v1/**` API）。

### Unnecessary Complexity Found

#### 1) 测试与类型检查：当前“红灯”必须先清掉（否则所有简化都没有可信回归）

- **单测失败（7 个）**（见 `docs/reports/artifacts/pytest_unit_2026-01-28_134833.txt`）
  - `tests/unit/routes/test_api_v1_task_runs_contract.py:32`
    - 问题：`from app.services.task_runs.task_runs_write_service import task_runs_write_service` 导入失败（服务单例/别名不存在）。
    - 建议：测试/路由改为注入 `TaskRunsWriteService()`，避免模块级单例（减少隐藏依赖）。
  - `tests/unit/routes/test_form_service_message_key_contract.py:43`
    - 问题：创建分类期望 `201`，实际 `400`，错误为“分类标识(code)不能为空”。
    - 建议：统一写入口字段：要么彻底改为 `code + display_name`（更新测试/前端）；要么在**单一入口**做兼容映射（避免 service 层散落兼容）。
  - `tests/unit/schemas/test_databases_query.py:18`、`tests/unit/schemas/test_databases_query.py:73`、`tests/unit/schemas/test_databases_query.py:117`
    - 问题：期望 `offset` 参数触发 `ValidationError("不支持 offset")`，实际未抛错（被静默忽略）。
    - 根因：`app/schemas/base.py:16` 的 `PayloadSchema` 采用 `extra="ignore"`，而 query schema 继承了该基类，导致未知 query 字段被吞掉。
    - 建议：拆分 `PayloadSchema` vs `QuerySchema`（query 默认 `extra="forbid"`），从结构上消灭“offset 兼容/静默”分支。
  - `tests/unit/services/test_account_classification_write_service.py:79`、`tests/unit/services/test_account_classification_write_service.py:172`
    - 问题：测试仍用 legacy 字段 `name`（期望代表展示名/或用于触发 priority 校验），但当前实现不再接受/不再按原顺序校验。
    - 建议：删除 legacy `name` 分支（更符合 YAGNI），并把测试改为传 `display_name`，同时为 priority 类型校验提供完整必填字段（避免“缺字段先报错”导致断言失真）。

- **Pyright 新增诊断（门禁失败）**
  - `tests/unit/routes/test_api_v1_task_runs_contract.py:32`（见 `docs/reports/pyright_full_2026-01-28_134551.txt`）
  - 建议：同上，移除 `task_runs_write_service` 这种“模块级单例别名”，改为显式实例/注入。

#### 2) 脚本门禁：同一仓库“Python 版本不一致”导致门禁脚本不可用

- `python3 --version` 为 **3.9.6**，但单测运行在 `.venv/bin/python` **3.13.7**（仓库声明也为 3.13）。
- **直接后果：部分门禁脚本在本机无法运行（Crash）**（见 `docs/reports/artifacts/ci-guards_2026-01-28_134740_stderr.txt`）
  - `scripts/ci/account-classification-auto-tasks-guard.sh`
    - 报错：`TypeError: zip() takes no keyword arguments`（脚本使用 `zip(..., strict=False)`，需要 Python≥3.10）。
  - `scripts/ci/db-session-rollback-allowlist-guard.sh`
    - 报错：`AttributeError: module 'ast' has no attribute 'Match'`（脚本使用 `ast.Match`，需要 Python≥3.10）。
  - 建议（最小化）：所有 `scripts/ci/*` 默认解释器优先使用 `.venv/bin/python`（若存在），其次才 fallback 到系统 `python3`；避免每台机器“门禁是否生效”随机。

#### 3) tasks 层直查库/直写库：违反分层，同时造成大量重复样板

`./scripts/ci/tasks-layer-guard.sh` 直接失败（见 `docs/reports/artifacts/ci-guards_2026-01-28_134740_stderr.txt`），命中点过多（节选）：

```text
app/tasks/capacity_aggregation_tasks.py:212
app/tasks/capacity_aggregation_tasks.py:240
app/tasks/capacity_aggregation_tasks.py:275
app/tasks/capacity_aggregation_tasks.py:281
app/tasks/capacity_aggregation_tasks.py:332
app/tasks/capacity_aggregation_tasks.py:439
app/tasks/capacity_collection_tasks.py:46
app/tasks/capacity_collection_tasks.py:51
app/tasks/capacity_collection_tasks.py:121
app/tasks/capacity_collection_tasks.py:231
app/tasks/capacity_collection_tasks.py:283
app/tasks/capacity_collection_tasks.py:299
app/tasks/account_classification_auto_tasks.py:44
app/tasks/account_classification_auto_tasks.py:66
app/tasks/account_classification_auto_tasks.py:121
app/tasks/account_classification_auto_tasks.py:167
app/tasks/account_classification_auto_tasks.py:233
app/tasks/account_classification_auto_tasks.py:238
app/tasks/account_classification_auto_tasks.py:259
app/tasks/accounts_sync_tasks.py:69
app/tasks/accounts_sync_tasks.py:88
app/tasks/accounts_sync_tasks.py:93
app/tasks/accounts_sync_tasks.py:256
app/tasks/accounts_sync_tasks.py:303
app/tasks/accounts_sync_tasks.py:307
app/tasks/account_classification_daily_tasks.py:38
app/tasks/account_classification_daily_tasks.py:57
app/tasks/account_classification_daily_tasks.py:70
app/tasks/account_classification_daily_tasks.py:98
app/tasks/account_classification_daily_tasks.py:113
app/tasks/account_classification_daily_tasks.py:237
app/tasks/account_classification_daily_tasks.py:242
app/tasks/account_classification_daily_tasks.py:293
app/tasks/account_classification_daily_tasks.py:336
app/tasks/account_classification_daily_tasks.py:341
app/tasks/capacity_current_aggregation_tasks.py:50
app/tasks/capacity_current_aggregation_tasks.py:72
app/tasks/capacity_current_aggregation_tasks.py:102
app/tasks/capacity_current_aggregation_tasks.py:158
app/tasks/capacity_current_aggregation_tasks.py:163
```

问题：
- tasks 层一边“调度/编排”，一边“查库/写库/commit”，导致每个任务都复制粘贴 `TaskRun.query/filter_by/all()` 的样板。

建议（最小化）：
- tasks 只做“调度入口 + 可观测性”，查库/写库下沉到 repository/service。
- 统一 `TaskRun/TaskRunItem` 的读取/写入入口（减少重复样板与语义漂移）。

#### 4) Service 层直查库：门禁明确禁止（且当前已命中）

`scripts/ci/services-repository-enforcement-guard.sh` 失败（见 `docs/reports/artifacts/ci-guards_2026-01-28_134740_stderr.txt`）：

- `app/services/accounts/account_classification_daily_stats_read_service.py:137`（`AccountClassification.query...`）
- `app/services/accounts/account_classification_daily_stats_read_service.py:320`（`ClassificationRule.query...`）
- `app/services/accounts/account_classification_daily_stats_read_service.py:454`（`ClassificationRule.query...`）
- `app/services/task_runs/task_runs_write_service.py:52`
- `app/services/task_runs/task_runs_write_service.py:116`
- `app/services/task_runs/task_runs_write_service.py:176`
- `app/services/task_runs/task_runs_write_service.py:200`

建议：
- 所有 `*.query` 下沉到 repository（或新增 write-repository），service 只负责业务编排。

#### 5) Error/message 互兜底链：典型“防御式复杂度”，且已触发门禁

`scripts/ci/error-message-drift-guard.sh` 失败：

- `app/tasks/capacity_collection_tasks.py:198`：`payload.get("error") or payload.get("message") or "实例容量同步失败"`
- `app/tasks/capacity_current_aggregation_tasks.py:233`：`payload.get("message") or payload.get("error") or "聚合失败"`

问题：
- 读端写互兜底链会把“字段漂移”永久化；每新增一个来源就多一个 `or`，长期只会更乱。

建议（最小化）：
- 统一 payload/error schema：只认一个字段（例如 `error_message`），在单一入口做映射/报错，不允许各处散落 `or` 链。

#### 6) Lint 噪音：中文 docstring 与 D400/D415 的冲突，会逼着你“为了 lint 写文字”

- `app/services/cache/cache_actions_service.py:96`、`app/services/cache/cache_actions_service.py:102`：中文句号 `。` 被判定为“不以 period 结尾”。
- `app/services/common/options_cache.py:34` + 大量 `D102/D107`：对一堆机械 get/set 要求补 docstring，明显是在制造“文档负担”。

建议（最小化）：
- 优先减少 public API 面积（把机械 get/set 收敛成少量入口），而不是补一堆 docstring。
- 或调整 Ruff 规则：对中文项目禁用/放宽 D400/D415、对特定目录/文件放宽 D102（否则只会产出无意义 docstring）。

#### 7) 明显的 YAGNI/假实现：对外宣称“清缓存”，实际是 no-op

- `app/services/cache/cache_actions_service.py:95-104`
  - `_invalidate_user_cache/_invalidate_instance_cache` 直接 `del ...` 然后 `return True`
  - 风险：对用户而言是“成功但没做事”，属于最难排查的行为。
  - 建议：要么实现，要么移除该能力/显式返回 `409/501`（避免默默成功）。

#### 8) 安全扫描误报：需要抑制，否则会把注意力从真问题上拉走

- `app/core/constants/http_headers.py:19`：`S105 Possible hardcoded password`（误报，header 键名不是密码）
- 建议：对该行加 `# noqa: S105` 或调整规则选择（否则 security scan 的信噪比会越来越低）。

---

### Code to Remove

> 下面是“删了不影响业务、还能减少维护负担”的候选（按风险从低到高排序）。

- `app/schemas/databases_query.py:13` - 删除未使用 import：`model_validator`（Estimated LOC reduction: 1）
- `app/services/cache/cache_actions_service.py:95` / `app/services/cache/cache_actions_service.py:101` - 若确认短期不做精准清理：删除/下线 no-op 清理入口或改为显式不支持（Estimated LOC reduction: 10-30，取决于接口策略）
- `tests/unit/routes/**` 中重复的 CSRF header 组装逻辑（建议提取 fixture/helper） - 主要收益是“删重复样板”，减少未来改动面（Estimated LOC reduction: 100+）
- `scripts/dev/openapi/export_api_contract_canvas.py`（文件标记 Deprecated） - 若确认迁移完成且不再需要 `.canvas` 审计：可归档/删除（Estimated LOC reduction: 300+）

### Simplification Recommendations

1. **先恢复绿灯（单测 + pyright/guards）**
   - Current: 7 个单测失败 + pyright/guards 新增诊断
   - Proposed: 先对齐 contract（字段名/别名）与 schema 严格策略，再做重构
   - Impact: 降低“重构后无法判断是否正确”的风险

2. **拆分 Schema 基类：Payload vs Query**
   - Current: `PayloadSchema` 用 `extra="ignore"`，query 继承后导致未知参数静默吞掉（offset 测试失败）
   - Proposed: 新增 `QuerySchema(extra="forbid")`，所有 query schema 改继承它（或在 query schema 内覆盖 model_config）
   - Impact: 删除 offset 兼容/兜底链的土壤；减少隐式行为

3. **移除模块级单例/别名（例如 task_runs_write_service）**
   - Current: 测试/类型检查都被“隐式全局”影响，改动面不可控
   - Proposed: 统一用显式实例/依赖注入
   - Impact: 降低隐藏依赖；让调用关系更直观

4. **把 TaskRun/TaskRunItem 的 DB Query 从 tasks/service 下沉到 repository**
   - Current: tasks/service 多处 `.query.filter_by(...)`，且门禁明确禁止（新增即失败）
   - Proposed: 建立/补齐 repository（含 write-side query），service 只做状态机编排
   - Impact: 大幅减少重复样板，降低语义漂移

5. **禁止 error/message 双字段互兜底**
   - Current: `payload.get("error") or payload.get("message") ...` 在多处出现并已触发门禁
   - Proposed: 统一为单字段（例如 `error_message`），在单一入口映射/报错
   - Impact: 消灭“永续兼容链”，让错误语义可控

6. **修正 CI 脚本默认解释器**
   - Current: 多个门禁脚本默认 `python3`，在本机跑到 3.9.6 会直接崩
   - Proposed: 默认 `.venv/bin/python`（或 `uv run python`）
   - Impact: 门禁可用性稳定；减少“本地过了/CI 挂了”的来回

### YAGNI Violations

- `app/services/cache/cache_actions_service.py:95`：清缓存入口目前是 no-op（“看起来能用”但实际没用），属于典型 YAGNI/假实现。
- `scripts/dev/openapi/export_api_contract_canvas.py`：既然 contract SSOT 已迁移到 Obsidian Markdown，该脚本若无真实使用场景应尽快归档/删除。
- `app/services/common/options_cache.py`：为每个 key 做一组 get/set 公共方法，导致 API 面积变大、文档/规则成本上升；若调用点少，建议收敛为更少入口。

### Final Assessment

- Total potential LOC reduction: 5% ~ 15%（主要来自：task/query 下沉去重 + 测试样板提取 + 删除 legacy/Deprecated 代码）
- Complexity score: **High**（不是因为业务逻辑复杂，而是“分层漂移 + 兼容链 + 样板重复”叠加）
- Recommended action: **先修复测试/门禁，后做结构性删减**（否则简化会变成“越改越不敢动”）

