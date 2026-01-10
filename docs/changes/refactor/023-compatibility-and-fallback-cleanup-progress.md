# 023 compatibility and fallback cleanup progress

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-04
> 更新: 2026-01-09
> 范围: config, api contracts, permissions snapshot/facts, logging context
> 关联方案: `023-compatibility-and-fallback-cleanup-plan.md`
> 关联: `docs/Obsidian/standards/doc/changes-standards.md`, `docs/Obsidian/standards/doc/documentation-standards.md`

---

## 当前状态(摘要)

- 已建立计划文档与分阶段目标.
- 尚未开始落地改动, 需要先跑 Phase 0 基线与生成命中点清单.

## Checklist

### Phase 0: 基线与清单冻结

- [ ] 跑通门禁: `make typecheck`
- [ ] 跑通门禁: `ruff check app`
- [ ] 跑通门禁: `uv run pytest -m unit`
- [ ] 生成命中点清单并保存到本 progress 的变更记录

### Phase 1: 先可观测, 后收敛(不改变外部行为)

- [ ] env var 历史别名命中告警: `app/settings.py:159`
- [ ] `success` 缺失命中统计: `app/api/v1/namespaces/accounts.py:262`
- [ ] 权限字段别名桥接命中统计: `app/services/accounts_sync/permission_manager.py:127`
- [ ] facts builder fallback shape 标记: `app/services/accounts_permissions/facts_builder.py:45`

### Phase 2: 契约收敛与兼容分支下线

- [ ] 下线 JWT refresh env var 历史别名并更新文档: `app/settings.py:159`, `docs/Obsidian/reference/config/environment-variables.md`
- [ ] 下线 permissions 字段别名桥接: `app/services/accounts_sync/permission_manager.py:127`
- [ ] 收敛 privileges 输入 shape: `app/services/accounts_permissions/facts_builder.py:45`
- [ ] 决策并落地 `success` 缺失策略(严格或过渡): `app/api/v1/namespaces/accounts.py:262`

### Phase 3: 分层解耦与清理(可选)

- [ ] 日志上下文采集解耦: `app/utils/logging/handlers.py:224`

## 变更记录

- 2026-01-04: 初始化 plan/progress 文档, 尚未开始落地改动.
