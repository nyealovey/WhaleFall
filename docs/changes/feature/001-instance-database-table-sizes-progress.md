# 001 实例数据库表容量进度

> 状态: Draft
> 负责人: WhaleFall 团队
> 创建: 2026-01-04
> 更新: 2026-01-04
> 范围: 实例详情页(数据库容量标签页), API v1 实例相关接口, 表容量采集与快照
> 关联方案: `../../plans/2026-01-02-instance-database-table-sizes.md`
> 关联: `docs/standards/changes-standards.md`, `docs/standards/documentation-standards.md`

---

## 当前状态(摘要)

- 已完成后端数据模型/API + 前端模态框接入, 并通过门禁验证.
- 待补齐: 手工回归(实例详情页 -> 数据库容量 -> 表容量 -> 刷新).

## 检查清单

### 阶段 0: 基线与验收口径

- [x] 明确验收口径: 实例详情页的数据库容量列表新增"表容量"入口, 支持查看快照与手动刷新
- [x] 明确表容量字段口径: `size_mb/data_size_mb/index_size_mb/row_count` 的单位与可空约束
- [x] 记录基线门禁结果(改动前): `make typecheck`, `uv run pytest -m unit`

### 阶段 1: 数据表结构 + 读模型

- [x] 迁移: `database_table_size_stats` 表(含唯一约束/索引)
- [x] 模型: `DatabaseTableSizeStat`
- [x] 类型: `app/types/instance_database_table_sizes.py`
- [x] 仓库层: 快照列表查询(分页/过滤/排序/collected_at)
- [x] 服务层: `fetch_snapshot(...)`

### 阶段 2: 刷新采集与落库

- [x] 适配器接口: `fetch_table_sizes(...)`
- [x] MySQL 适配器: `information_schema.TABLES`
- [x] PostgreSQL 适配器: `pg_total_relation_size`(连接到目标数据库)
- [x] SQL Server 适配器: sys tables 计算 reserved/data/index
- [x] Oracle 适配器: `dba_segments` 聚合(以 tablespace 作为 database_name), 权限不足时降级 `all_segments/user_segments`
- [x] 协调器: upsert + 删除已不存在的表记录, 记录 `elapsed_ms`

### 阶段 3: API v1 + 测试

- [x] GET 快照: `/api/v1/instances/<id>/databases/<database_name>/tables/sizes`
- [x] POST 刷新: `/api/v1/instances/<id>/databases/<database_name>/tables/sizes/actions/refresh`
- [x] 权限 + CSRF: 与现有容量同步口径一致
- [x] 契约测试: `tests/unit/routes/test_api_v1_instances_contract.py`

### 阶段 4: 前端(UI)

- [x] 服务方法: `fetchDatabaseTableSizes(...)`, `refreshDatabaseTableSizes(...)`
- [x] 模板: 在 `app/templates/instances/detail.html` 增加模态框结构
- [x] 控制器: `database-table-sizes-modal.js`, 并在实例详情页绑定动作
- [x] 交互: 打开/刷新展示加载中, 刷新成功更新 `collected_at`, 刷新失败保留原快照

### 阶段 5: CSS + 手工回归

- [x] CSS: 模态框布局辅助, 表列表可滚动(可选表头吸顶)
- [ ] 手工回归: 打开模态框 -> 读取快照 -> 刷新 -> 列表更新 -> 权限/异常提示正常

### 阶段 6: 门禁验证

- [x] `make format`
- [x] `make typecheck`
- [x] `uv run pytest -m unit`
- [x] `./scripts/ci/eslint-report.sh quick` (如改动 JS)

## 变更记录

- 2026-01-04: 初始化进度文档, 基于 `docs/plans/2026-01-02-instance-database-table-sizes.md` 拆分检查清单.
- 2026-01-04: 完成后端(模型/迁移/采集协调器/API)与前端(模态框/按钮/刷新)接入, 通过 `make format`/`make typecheck`/`uv run pytest -m unit`/`./scripts/ci/eslint-report.sh quick` 门禁验证.
- 2026-01-04: Oracle 刷新补充防御与回退: `dba_*` 不可用时自动降级, 仍失败则返回 409 并输出更明确的错误信息, 避免 500.
