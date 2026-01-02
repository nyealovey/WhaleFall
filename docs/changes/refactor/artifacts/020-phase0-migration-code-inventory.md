# 迁移期代码 Phase 0 扫描清单

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: app/, scripts/, sql/, tests/unit/, env.example
> 关联: ../020-migration-code-cleanup-plan.md; ../020-migration-code-cleanup-progress.md

## 扫描范围与方法

- 范围: app/, scripts/, sql/, tests/unit/, env.example.
- 关键词: migration, migrate, legacy, backfill, compat, feature flag, 回填, 兼容, 迁移.
- 说明: 对 toggle, fallback, v1/v2 等高噪声关键词仅保留与迁移期逻辑相关项.

## 结论摘要

- 临时 API/路由: 未发现仍在提供的临时路由实现, 仅存在 legacy API 下线防御测试与注释.
- 回填脚本或任务: 发现运行时回填逻辑, 已改为 fail-fast(不再自动回填).
- 迁移开关: ACCOUNT_CLASSIFICATION_DSL_V4 为迁移开关, 已移除并强制 DSL v4.
- 数据格式兼容: 发现 snapshot 缺失兜底, legacy 规则表达式跳过, 旧字段/旧参数兼容等, 已按计划移除/收紧.
- MySQL5 兼容: 仅发现 MYSQL_ENABLE_ROLE_CLOSURE 开关, 明确保留.

## 清单 (待移除或评估)

| ID | 类别 | 位置 | 作用 | 风险 | 依赖方 | 处理 |
| --- | --- | --- | --- | --- | --- | --- |
| MIG-001 | data-backfill | app/services/accounts_sync/permission_manager.py:300 | 通过 username + instance/db_type 回填 instance_account_id, 用于迁移期缺失关联. | P1 | AccountPermission 数据, 同步任务 | ✅ 已移除(改为 fail-fast,缺失即报错).
| MIG-002 | data-backfill | app/services/accounts_sync/permission_manager.py:314 | snapshot 缺失或版本不为 4 时回填权限快照, 并更新同步时间. | P0 | AccountPermission 数据, 同步任务, test_account_permission_manager | ✅ 已移除(不再自动回填).
| MIG-003 | data-format-compat | app/services/accounts_permissions/snapshot_view.py:15 | snapshot 缺失时返回 SNAPSHOT_MISSING, 用于监控与回滚. | P1 | 权限快照消费方, 监控告警, test_permission_snapshot_view | ✅ 已收紧(缺失直接抛错,不兜底).
| MIG-004 | feature-flag | app/services/account_classification/flags.py:10 | DSL v4 开关, 迁移期灰度控制. | P1 | 账号分类规则评估, Settings, env.example | ✅ 已移除(强制 DSL v4).
| MIG-005 | data-format-compat | app/services/account_classification/orchestrator.py:411 | DSL v4 规则在开关关闭时直接跳过. | P1 | 账号分类规则评估, test_account_classification_orchestrator_dsl_guard | ✅ 已移除(仅支持 DSL v4).
| MIG-006 | data-format-compat | app/services/account_classification/orchestrator.py:424 | legacy 规则表达式直接跳过. | P1 | 账号分类规则数据 | ✅ 已移除(legacy 直接报错).
| MIG-007 | data-format-compat | app/services/instances/instance_write_service.py:221 | 兼容旧字段 tag_names 为 "a,b" 字符串. | P1 | 实例写入接口, 前端表单 | ✅ 已移除(仅接受数组).
| MIG-008 | data-format-compat | app/static/js/common/table-query-params.js:70 | 兼容 pageSize/limit 并发出 legacy 参数事件. | P2 | 前端列表页参数 | ✅ 已移除(仅支持 page_size).
| MIG-009 | api-compat | app/api/v1/namespaces/connections.py:48 | connection test result 兼容旧接口结构. | P1 | API 消费方 | ✅ 已移除(返回结构收口).
| MIG-010 | routing-compat | app/__init__.py:282 | CORS 兼容 /<module>/api/* 旧路径结构. | P2 | 旧 API 调用方 | ✅ 已移除(仅允许 /api/v1/**).
| MIG-011 | migration-script | scripts/ops/docker/volume_manager.sh:227 | 从 userdata 迁移到 Docker 卷的脚本. | P2 | 运维流程 | ✅ 已移除(删除 migrate 子命令及 Makefile.prod 入口).
| MIG-012 | doc-tooling | scripts/dev/docs/check_api_routes_reference.py:1 | 迁移期 API 文档校验脚本, 忽略 /api 路径. | P2 | 文档维护 | ✅ 已移除(脚本与文档引用已清理).
| MIG-013 | doc-tooling | scripts/dev/docs/generate_api_routes_inventory.py:1 | 迁移期 API inventory 工具, 绑定 004 计划文档. | P2 | 文档维护 | ✅ 已移除(脚本与文档引用已清理).

## 清单 (明确保留)

| ID | 类别 | 位置 | 作用 | 风险 | 依赖方 | 处理 |
| --- | --- | --- | --- | --- | --- | --- |
| KEEP-001 | mysql-compat | app/settings.py:81 | MYSQL_ENABLE_ROLE_CLOSURE 开关, 用于 MySQL 兼容. | P0 | MySQL5 兼容策略 | 保留.
| KEEP-002 | defense-test | tests/unit/test_frontend_no_legacy_api_paths.py:1 | 防止前端继续引用旧 /api 路径. | P2 | 前端构建 | 保留.
| KEEP-003 | defense-test | tests/unit/test_ops_no_legacy_health_api_paths.py:1 | 防止运维脚本访问旧健康检查路径. | P2 | 运维脚本 | 保留.
| KEEP-004 | defense-test | tests/unit/routes/test_legacy_api_gone_contract.py:1 | 确认旧 API 路径已下线. | P2 | 路由 | 保留.

## 备注

- MIG-004 相关配置已从 app/settings.py 与 env.example 同步清理.
- MIG-011 已移除 userdata->volume 迁移入口, 卷管理脚本保留 list/create/backup/restore/size 等能力.
- MIG-012/013 已移除, 统一以 OpenAPI 与现有文档为准.
