# 001 调度任务命名重构方案

> 状态: Active
> 负责人: @apple
> 创建: 2026-01-20
> 更新: 2026-01-20
> 范围: 调度器内置任务(id/function/task_key), 以及相关 UI/文档/测试
> 关联: `docs/Obsidian/standards/doc/changes-standards.md`, `docs/Obsidian/standards/halfwidth-character-standards.md`

---

## 动机与范围

当前 4 个内置定时任务中, 有 3 个命名与页面文案不够贴切, 且存在语义漂移:

- `collect_database_sizes`: 实际是"容量同步", 但名称更像"只采集 size".
- `calculate_database_size_aggregations`: 名称偏长, 且"size"信息对外不一定必要.
- `calculate_account_classification_daily_stats`: 名称偏长, 且"daily_stats"属于调度频率/落库口径, 不一定需要体现在 task_key.

本次重构目标: 统一内置任务命名为更稳定的业务含义, 并在代码, 配置, UI, 文档中一致更新.

## 不变约束

- 行为不变: 任务内部业务逻辑, 计算口径, API 行为保持不变.
- 调度不变: cron 时间保持不变.
- 数据不变: 不新增/修改 DB schema, 不改历史 TaskRun 记录.
- 升级约束: 不保留旧名称兼容入口; 升级时必须迁移 scheduler jobstore(见 Phase 2).

## 命名调整清单

| 任务 | 现状(task_key/id/function) | 现状中文名 | 调整后(task_key/id/function) | 调整后中文名 |
|---|---|---|---|---|
| 账户同步 | `sync_accounts` | 账户同步 | `sync_accounts` | 账户同步 |
| 数据库同步 | `collect_database_sizes` | 容量同步 | `sync_databases` | 数据库同步 |
| 数据库聚合 | `calculate_database_size_aggregations` | 统计聚合 | `calculate_database_aggregations` | 统计数据库聚合 |
| 账户分类 | `calculate_account_classification_daily_stats` | 账户分类统计 | `calculate_account_classification` | 统计账户分类 |

说明:

- 本次约定 "job id" == "task_key" == "function name"(默认任务配置与运行记录一致), 以降低心智负担.
- 不保留旧名称 wrapper; 旧名称视为 breaking change, 通过迁移 jobstore 解决.

## 分层边界

- scheduler 层: 仅做 job 注册, 任务函数映射, 以及 job reload.
- tasks 层: 任务边界, 负责 create_app() + app_context() + TaskRun 写入.
- services/repositories 层: 承载业务逻辑与 DB 操作.

本重构仅调整 scheduler/tasks 层对外标识符, 不重命名 service/repository 方法(除非后续确认需要对齐).

## 分阶段计划

### Phase 0: 盘点与方案确认

- 明确哪些地方依赖 task_key (API contract, UI 下拉, docs/Obsidian, canvas, tests).
- 明确 jobstore 迁移策略(强制): reload_jobs 或删除 `userdata/scheduler.db`.

验收口径:

- 输出一份搜索清单, 覆盖所有旧名称引用点.

### Phase 1: 引入新名称(不保留兼容)

改动点(预期):

- `app/config/scheduler_tasks.yaml`: 更新默认任务的 `id/name/function/description`.
- `app/scheduler.py`: 更新 `TASK_FUNCTIONS`, 移除旧 key, 仅保留新 key.
- `app/tasks/*.py`: 重命名任务函数, 并同步更新 TaskRun 写入的 `task_key/task_name`.
- `app/core/constants/scheduler_jobs.py`: 更新 `BUILTIN_TASK_IDS`.
- `app/services/scheduler/*.py`: 更新 job id 白名单与 category map.
- `app/services/*_actions_service.py`: 更新 task_key, thread name, log module/task 字段.
- `app/templates/admin/scheduler/modals/scheduler-modals.html`: 更新 option value 与中文显示.

验收口径:

- `make format`
- `make typecheck`
- `uv run pytest -m unit`
- 手工验证: 通过"调度器管理页"触发一次手动执行, 生成的 TaskRun.task_key 为新名称.
- 迁移验证: 清理/重建 `userdata/scheduler.db` 后, 启动成功且 jobs 列表均为新名称.

### Phase 2: 迁移 scheduler job id(强制)

背景: APScheduler 默认会从 `userdata/scheduler.db` 读取既有 job, 如果不清理, UI 仍可能展示旧 job id.

迁移策略二选一(必须执行其一):

- 方案 A(推荐): 使用管理接口执行 reload, 先删除全部 job, 再按新配置重建.
- 方案 B: 删除 `userdata/scheduler.db` 后重启(仅适用于本地/可接受丢失自定义 job 的环境).

验收口径:

- scheduler job 列表中 id 全部为新名称.
- 旧名称不再出现在 scheduler jobs 列表(除非有自定义 job).

### Phase 3: 文档与可视化材料更新

范围(预期):

- `docs/Obsidian/architecture/flows/**`: 更新 task 名称.
- `docs/Obsidian/operations/**`: 更新操作手册里的 task id.
- `docs/Obsidian/canvas/**`: 更新 .canvas 文本节点内容.
- `docs/optimization/**` 以及 `docs/plans/**` 中的旧名称引用.

验收口径:

- `rg -n "collect_database_sizes|calculate_database_size_aggregations|calculate_account_classification_daily_stats" docs -g'!docs/changes/**'` 结果为空(或仅剩历史归档).

### Phase 4: 清理旧名称残留(必须)

验收口径:

- 全仓库搜索旧名称不再命中(允许 docs 归档区残留).
- UI 下拉/页面说明不再展示旧名称.

## 风险与回滚

主要风险:

- APScheduler jobstore 序列化: 直接删除/重命名函数, 可能导致旧 `userdata/scheduler.db` 里的 callable 无法反序列化.
- 迁移会清空 jobs: 删除 `userdata/scheduler.db` 或 reload_jobs 都会丢失自定义任务与手工调整的 cron.
- 外部引用: UI, API, docs, tests 可能硬编码 task_key.

回滚策略:

- 需要回滚时: 回滚代码与 `scheduler_tasks.yaml` 变更, 并恢复升级前备份的 `userdata/scheduler.db`(若有).
- 若无备份: 只能重新按旧版本配置重建默认任务, 自定义任务需人工重新配置.

## 验证与门禁

- 代码门禁: `make format`, `make typecheck`, `./scripts/ci/ruff-report.sh style`, `uv run pytest -m unit`.
- 文档门禁: `rg -n -P "[\\x{3000}\\x{3001}\\x{3002}\\x{3010}\\x{3011}\\x{FF01}\\x{FF08}\\x{FF09}\\x{FF0C}\\x{FF1A}\\x{FF1B}\\x{FF1F}\\x{2018}\\x{2019}\\x{201C}\\x{201D}\\x{2013}\\x{2014}\\x{2026}]" docs` 确保新增内容不引入全角/非 ASCII 标点.
