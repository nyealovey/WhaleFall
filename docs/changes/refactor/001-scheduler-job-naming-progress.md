# 001 调度任务命名重构进度

关联方案: [001-scheduler-job-naming-plan.md](001-scheduler-job-naming-plan.md)

> 状态: Active
> 负责人: @apple
> 创建: 2026-01-20
> 最后更新: 2026-01-20
> 范围: 调度器内置任务(id/function/task_key), 以及相关 UI/文档/测试

---

## 当前状态(摘要)

- 已完成: 代码重命名 + 配置/服务/UI/文档同步更新, 单测已通过.
- 已确认: 采用强制迁移策略, 不做旧名称兼容.
- 待处理: 执行 jobstore 迁移(reload_jobs 或清理 `userdata/scheduler.db`), 使 scheduler jobs 列表使用新 id.

## Checklist

### Phase 0: 盘点与确认

- [x] `rg` 盘点旧名称引用点(代码, 文档, tests, canvas).
- [x] 确认迁移策略: 强制迁移 job id, 不保留旧名称兼容.

### Phase 1: 代码与配置重命名(不保留兼容)

- [x] 更新 `app/config/scheduler_tasks.yaml` 的 id/name/function/description.
- [x] 更新 `app/scheduler.py` 的 `TASK_FUNCTIONS`(仅保留新 key).
- [x] 更新 tasks: `sync_databases`, `calculate_database_aggregations`, `calculate_account_classification`.
- [x] 更新 scheduler constants/services/actions/templates 的 job id 白名单与映射.
- [x] 更新 TaskRun 写入的 task_key/task_name.
- [x] 运行门禁: `make format`, `make typecheck`, `uv run pytest -m unit`.

### Phase 2: job id 迁移(强制)

- [ ] 执行 scheduler reload(或清理 `userdata/scheduler.db`), 确保新 id 生效.
- [ ] 验证 scheduler jobs 列表不再出现旧 id.

### Phase 3: 文档与可视化材料更新

- [x] 更新 `docs/Obsidian/architecture/flows/**` 任务名称.
- [x] 更新 `docs/Obsidian/operations/**` 任务名称.
- [x] 更新 `docs/Obsidian/canvas/**` 文本节点.
- [x] 更新 `docs/optimization/**` 与相关 `docs/plans/**` 引用.

### Phase 4: 清理旧名称残留(必须)

- [x] 删除旧名称在 UI/文档/测试中的残留.

## 变更记录

- 2026-01-20: 创建 plan/progress 文档.
- 2026-01-20: 确认采用强制迁移策略, 不做旧名称兼容.
- 2026-01-20: 完成命名重构与全仓库引用更新; 单测通过; 等待执行 jobstore 迁移.
