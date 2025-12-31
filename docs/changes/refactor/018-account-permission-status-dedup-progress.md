# Account Permission Status And Attributes Dedup Progress

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: 同 `018-account-permission-status-dedup-plan.md`
> 关联: `018-account-permission-status-dedup-plan.md`, `017-account-permissions-refactor-v4-plan.md`, `017-account-permissions-refactor-v4-progress.md`

关联方案: `018-account-permission-status-dedup-plan.md`

---

## 1. 当前状态(摘要)

- 结论已确认: 最终形态采用 Option B(删除 `account_permission.is_superuser/is_locked`, 查询统一基于 `permission_facts.capabilities`).
- SQLServer: 已补齐 `type_specific` 登录状态采集字段(禁用/连接引擎/密码策略与状态); adapter 不推导 `is_locked`, 且本期 `LOCKED` capability 不使用 `is_disabled`.
- 已完成 Phase 0-3: facts v2/capabilities 真源, 读侧与查询切换, migration 删除结构化列并新增 capabilities GIN 索引.

## 2. Checklist

### Phase 0: Contract 对齐与去重门禁

- [x] 定义 `permission_facts v2` schema, 引入 `LOCKED` capability
- [x] `dsl_v4.is_superuser()` 改为 `has_capability("SUPERUSER")`
- [x] 新增门禁: `type_specific` 禁止字段清单校验(至少拦截 `is_superuser`, `is_locked`, `roles`, `privileges`)

### Phase 1: adapters 输出标准化(type_specific 去权限化, 去锁定态重复)

- [x] MySQL: 删除 `type_specific.is_locked`/`type_specific.can_grant` 等重复/权限字段
- [x] PostgreSQL: 删除 `type_specific.can_*` 等权限属性(统一保留在 `role_attributes`)
- [x] Oracle: 确保不写入 `type_specific.is_locked/is_superuser`
- [x] SQLServer: 补齐 `type_specific` 采集(禁用/连接引擎/密码策略与状态), 且不写入 `type_specific.is_locked/is_superuser`

### Phase 2: 读侧切换(从 columns/facts keys 切到 capabilities)

- [x] API 输出: `is_superuser/is_locked` 从 `capabilities` 推导
- [x] Repository filters: 过滤与排序统一走 capabilities + query helper
- [x] 删除所有 `type_specific` 锁定态兜底推导逻辑

### Phase 3: 删除结构化列(Option B 落地)

- [x] migration: 删除 `account_permission.is_superuser/is_locked`
- [x] 索引: 为 `permission_facts.capabilities` 准备 GIN 索引(及必要的表达式索引/排序兜底方案)
- [x] 清理 ORM / repository 中对结构化列的引用

### Phase 4: 清理与收尾

- [x] 删除 `permission_facts.is_superuser/is_locked` 相关存量兼容代码
- [ ] 更新 reference 文档, 明确 `type_specific` 与 `capabilities` 的职责边界

## 3. 变更记录

- 2025-12-31: 初始化进度文档, 以 `018-account-permission-status-dedup-plan.md` 为真源.
- 2025-12-31: 方案结论调整为 Option B(最终删除结构化列), Option C 仅作为性能兜底.
- 2025-12-31: SQLServer adapter 补齐 `type_specific` 采集: `connect_to_engine`, `password_policy_enforced`, `password_expiration_enforced`, `is_locked_out`, `is_password_expired`, `must_change_password`.
- 2025-12-31: SQLServer `LOCKED` capability 推导规则调整: 暂不使用 `type_specific.is_disabled`, 仅保留原始字段落库.
- 2025-12-31: 完成 Phase 0-3: capability 真源切换, repositories 查询改造, migration 删除结构化列并新增 GIN 索引.
