# Permission Config Version Tags Refactor Progress

> 状态: Draft
> 负责人: @codex
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: account-classification 规则页面权限配置, `permission_configs` 选项注册表, `/api/v1/accounts/classifications/permissions/<db_type>`
> 关联: `./019-permission-config-version-tags-plan.md`

## 当前状态(摘要)

- 已对齐版本基线: SQL Server 2008+, PostgreSQL 11+, Oracle 11g+(MySQL 仍按 spec 5.7+)
- 已完成方案文档: `./019-permission-config-version-tags-plan.md`
- 已完成 Phase 0-3: schema/API/seed/UI/版本禁用提示 均已落地

## Checklist

### Prep: 文档与口径

- [x] 更新支持版本基线与 plan 文档
- [x] 明确 Oracle 11-21 的在线文档抓取入口(roles + system privileges)与 diff 口径(不导出)

### Phase 0: schema + API(不改 UI)

- [x] Alembic migration: `permission_configs` 增加 `introduced_in_major`(nullable)
- [x] 后端输出: `PermissionConfig.to_dict()` 和 `get_permissions_by_db_type()` 返回 `introduced_in_major`
- [x] 单测: API 输出结构包含 `introduced_in_major`(默认 null)

### Phase 1: 种子数据补齐(已知差异)

- [x] SQL Server: 追加 2022 新 fixed server roles, 标记 `introduced_in_major="2022"`
- [x] PostgreSQL: 标记 predefined roles 的 14/15 引入版本
- [x] MySQL: 标记 8.0 引入的管理类 global privileges(`introduced_in_major="8.0"`)
- [x] Oracle: 基于 11/12/18/19/21 官方在线文档补齐 roles/system privileges 的 `introduced_in_major`(本次仅对文档可判定项打标; 其余保持 NULL)

### Phase 2: UI badge 展示

- [x] UI: 权限项右侧展示 `introduced_in_major` badge
- [x] 回归: 新建/编辑规则流程不受影响(checkbox value/表达式构建不变)

### Phase 3(可选): 按实例版本过滤/提示

- [x] 版本映射: SQL Server `major.minor` -> 年份(例如 16.0 -> 2022)
- [x] UI: 对高于"最旧实例版本(floor)"的权限项显示 disabled + tooltip(默认不隐藏)
- [x] 文档: 补齐各 db_type 的比较/过滤口径与边界案例

## 变更记录

- 2025-12-31:
  - 初始化 progress 文档
  - 对齐支持版本基线: SQL Server 2008+, PostgreSQL 11+, Oracle 11g+
  - 更新方案文档的官方文档引用与版本差异结论
  - 明确 Oracle 使用在线文档抓取 + diff(不导出)的后期落地方式
  - Phase 0: 增加 `permission_configs.introduced_in_major`, API 输出包含该字段, 单测补齐
  - Phase 1: seed 增加 SQL Server 2022 roles, 并为 MySQL/PG/SQL Server/Oracle 写入版本标识
  - Phase 2: UI 权限项展示版本 badge
  - Phase 3: API 返回 `version_context.min_main_version`(启用且未删除实例的最旧版本), UI 对高于 floor 的权限项禁用并提示
