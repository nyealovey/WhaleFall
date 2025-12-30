# Account Permissions Refactor V4 Progress

> 状态: Draft
> 负责人: @kiro
> 创建: 2025-12-30
> 更新: 2025-12-30
> 范围: 同 `017-account-permissions-refactor-v4-plan.md`
> 关联: `017-account-permissions-refactor-v4-plan.md`, `../../plans/2025-12-30-account-permissions-refactor-v4.md`

关联方案: `017-account-permissions-refactor-v4-plan.md`

---

## 1. 当前状态(摘要)

- 计划已确认: 不兼容 legacy 旧数据, 仅靠同步覆盖.
- 计划已确认: `account_change_log` diff 升级后置到 Phase 6, 不阻塞新权限结构上线.
- 进度: 未开始(等待 Phase 0).

## 2. Checklist

### Phase 0: 测试基础设施(阻塞)

- [ ] 增加 v4 snapshot fixtures(覆盖 mysql/postgresql/sqlserver/oracle, 含边界情况)
- [ ] 增加 `account_permission` model 契约测试(列, 类型, 索引)
- [ ] 增加 snapshot accessor/view 测试(缺失时返回 `SNAPSHOT_MISSING`)
- [ ] 增加一致性校验脚本(抽样对比 legacy columns vs snapshot view)

### Phase 1: 双写 + 一致性校验

- [ ] DB migration: 增加 `permission_snapshot`(jsonb) 与 `permission_snapshot_version`(default 4)
- [ ] snapshot builder: 不丢未知字段, 写入 `extra`
- [ ] 双写: legacy columns + snapshot 同一事务写入(失败则整体回滚)
- [ ] 指标: snapshot write success/failed, build duration
- [ ] Gate: 双写成功率 > 99.9%
- [ ] Gate: 抽样一致性不一致率 < 1% (连续 7 天)
- [ ] Runbook: Phase 1 rollback

### Phase 2: 切读(金丝雀)

- [ ] 读路径: 支持 snapshot read, 缺失时显式计数并返回错误码
- [ ] 金丝雀: 支持按百分比切读
- [ ] 指标: snapshot missing, facts build errors
- [ ] Gate: facts 构建错误率 < 0.1%
- [ ] Gate: 分类结果与 legacy 对比一致率 > 99% (仅用于验证)
- [ ] Runbook: Phase 2 rollback

### Phase 3: 同步覆盖

- [ ] 执行一次全量账户权限同步(覆盖所有实例/账户)
- [ ] 全量一致性校验: `scripts/verify_snapshot_consistency.py --full`
- [ ] Gate: snapshot 缺失率 < 0.5%
- [ ] Gate: 全量一致性校验不一致率 < 0.5%

### Phase 4: DSL v4(规则重建)

- [ ] DSL evaluator: 5 个核心函数
- [ ] 规则校验 API
- [ ] 规则重建: 基于 DSL v4 重建分类规则
- [ ] Gate: 分类结果与 legacy 对比一致率 > 99% (仅用于验证)

### Phase 5: 清理(不含删 legacy 列)

- [ ] 删除 legacy 分类器代码(迁移期保留的旧路径)
- [ ] 删除 `PERMISSION_FIELDS` 在分类器侧的引用(若存在)

### Phase 6: 变更历史(diff)升级 + 删除 legacy 权限列

- [ ] 前置: snapshot 缺失率满足 Gate(见 Phase 3)
- [ ] diff 升级: `account_change_log` 的 diff 计算基于 v4 snapshot/view
- [ ] 验证: `/change-history` 在新权限结构下仍可用
- [ ] 删除 legacy 权限列(migration)
- [ ] 删除 `PERMISSION_FIELDS` 硬编码(或收敛到仅剩兼容期使用点)

## 3. 变更记录

- 2025-12-30: 初始化进度文档, 以 `../../plans/2025-12-30-account-permissions-refactor-v4.md` 为真源.
- 2025-12-30: 确认不兼容 legacy 旧数据, 仅靠同步覆盖.
- 2025-12-30: 确认 `account_change_log` diff 升级后置到 Phase 6.

