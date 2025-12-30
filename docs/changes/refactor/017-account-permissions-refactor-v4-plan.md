# Account Permissions Refactor V4 Plan

> 状态: Draft
> 负责人: @kiro
> 创建: 2025-12-30
> 更新: 2025-12-30
> 范围: `account_permission` snapshot v4, facts, DSL v4, 规则编辑 UI, 变更历史(diff)后置升级
> 关联: `../../plans/2025-12-30-account-permissions-refactor-v4.md`

关联方案(真源): `../../plans/2025-12-30-account-permissions-refactor-v4.md`

---

## 1. 动机与范围

本计划用于跟踪"账户权限重构 V4"的多阶段落地进度, 与 PR/Issue 对齐. 设计与实施细节以 `../../plans/2025-12-30-account-permissions-refactor-v4.md` 为单一真源.

范围包含:

- 权限存储升级为版本化 snapshot(v4)
- facts 层与跨 DB 分类 DSL v4
- 发布策略与一致性校验
- 规则编辑与规则重建
- 变更历史(diff)在新权限结构下的后置升级(Phase 6)

## 2. 不变约束

- 本期不做 legacy 旧数据兼容, snapshot 缺失必须显式暴露(错误码), 依赖后续同步覆盖.
- `account_change_log` 需求保留, 但 diff 升级后置到 Phase 6, 不阻塞 snapshot/facts/DSL 上线.
- 删除 legacy 权限列必须在 Phase 6 完成 diff 升级之后进行.

## 3. 分阶段计划(摘要)

Phase 0: 测试基础设施

- 目标: 为 snapshot/facts/DSL 的 TDD 提供 fixture, 契约测试, 校验脚本.

Phase 1: 双写 + 一致性校验

- Gate: 双写成功率 > 99.9%, 抽样一致性不一致率 < 1% (连续 7 天).

Phase 2: 切读(金丝雀)

- Gate: facts 构建错误率 < 0.1%, 分类结果与 legacy 对比一致率 > 99% (仅用于验证).

Phase 3: 同步覆盖

- Gate: snapshot 缺失率 < 0.5%, 全量一致性校验不一致率 < 0.5%.

Phase 4: DSL v4

- Gate: 规则重建完成, 分类结果与 legacy 对比一致率 > 99% (仅用于验证).

Phase 5: 清理(不含删 legacy 列)

- 目标: 移除 legacy 分类器代码, 收敛旧路径依赖.

Phase 6: 变更历史(diff)升级(不含删 legacy 权限列)

- 目标: diff 计算基于 snapshot/view, `/change-history` 在新结构下可用.

Phase 7: 删除 legacy 权限列 + 清理 `PERMISSION_FIELDS`

- 目标: 删除 legacy 权限列与 `PERMISSION_FIELDS` 硬编码(或收敛到仅剩兼容期使用点).

## 4. 风险与回滚(摘要)

- 风险: 双写阶段 legacy vs snapshot 不一致.
  - 缓解: 同一事务内写入, 一致性校验门槛, 分阶段开关.
- 回滚: Phase 1/2 按 feature flag 快速关闭 snapshot 写/读, 详见真源方案的 runbook 约定.
