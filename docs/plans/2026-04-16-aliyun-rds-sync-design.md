# Aliyun RDS Sync Integration Design

> 状态: Draft
> 负责人: Codex
> 创建: 2026-04-16
> 更新: 2026-04-16
> 范围: `aliyun_rds` 数据源接入、实例主表整合、只读生命周期、定时同步
> 关联:
> - `../Obsidian/standards/backend/standard/task-and-scheduler.md`
> - `../Obsidian/standards/backend/standard/database-migrations.md`
> - `../Obsidian/architecture/domain/instances-domain.md`
> - `../Obsidian/reference/service/instances-write-and-batch.md`
> - `../Obsidian/reference/service/scheduler-actions-and-read-services.md`

## 背景

- 现有仓库已经具备 `JumpServer`、`Veeam` 两类外部数据源的接入模式, 包括:
  - 系统设置页绑定数据源
  - 后台手动同步
  - 定时任务调度
  - 快照落库
  - 在实例列表/统计中消费外部同步结果
- 现有 `instances` 域默认把实例视为可人工增删改的本地主实体, 尚未具备“外部托管且只读”的一等概念。
- 本次新增需求是引入 `aliyun rds` 自动同步模块, 并将同步到的实例整合进现有实例主表。
- 用户已经明确:
  - 云端实例必须整合进现有实例体系
  - 这部分实例不能人工删除、修改
  - 数据应完全依赖同步自动更新
  - 云端实例消失时, 本地应软删除保留
  - 一期先做实例台账, 不接入账户/容量/审计等连接型同步链路
  - 同步放进定时任务, 默认每日执行
  - 一期按单阿里云账号全局绑定设计

## 目标与非目标

### 目标

- 新增 `aliyun_rds` 集成能力, 可从阿里云 RDS 拉取实例清单并写入本地。
- 将阿里云 RDS 实例整合进 `instances` 主表, 参与列表、详情、统计等现有只读视图。
- 为同步实例建立“只读/托管”约束, 禁止人工编辑、删除、恢复。
- 提供系统设置页绑定入口、手动同步入口和每日定时同步任务。
- 云端实例消失时对本地实例执行软删除保留; 重新出现时恢复原记录并继续更新。
- 避免现有 `accounts_sync`、`capacity_sync` 等任务误扫这批无法本地连接的实例。

### 非目标

- 一期不支持多阿里云账号、多绑定集合管理。
- 一期不接入账户同步、容量采集、审计采集、连接测试等依赖本地连接凭据的链路。
- 一期不设计“解绑后保留实例继续人工维护”的模式。
- 一期不新增实例来源筛选器, 避免搅乱现有 `managed_status=JumpServer` 语义。

## 总体方案

### 方案原则

- 复用现有 `integrations -> source_binding -> provider -> sync_actions -> task_runs -> scheduler` 骨架。
- 阿里云实例进入现有 `instances` 主表, 而不是维护一套平行实例表。
- “同步来源”和“外部主键”进入 `instances` 主表, 作为外部托管实例的稳定身份。
- 所有对同步托管实例的变更以云端为准, 本地只允许同步写入, 不允许人工改动。

### 接入结构

- 新增 `aliyun_rds` 模块族, 结构对齐现有 `jumpserver` / `veeam`:
  - `app/services/aliyun_rds/provider.py`
  - `app/services/aliyun_rds/source_service.py`
  - `app/services/aliyun_rds/sync_actions_service.py`
  - `app/repositories/aliyun_rds_repository.py`
  - `app/tasks/aliyun_rds_sync_tasks.py`
  - `app/api/v1/namespaces/aliyun_rds.py`
  - 对应系统设置页模板、JS service、view 模块
- `provider` 负责与阿里云官方接口交互:
  - 先取地域列表
  - 再按地域分页拉取 RDS 实例
  - 统一归一化为内部 `snapshot` 结构
- `sync_actions_service` 负责:
  - 准备 `TaskRun`
  - 执行全量同步
  - 写快照
  - 更新/创建/软删除 `instances`
  - 写入同步摘要和失败明细

## 数据模型设计

### 新增表

#### `aliyun_rds_source_bindings`

- 保存全局唯一数据源绑定。
- 字段建议:
  - `id`
  - `credential_id`
  - `region_strategy`
  - `region_ids_json`
  - `verify_ssl`
  - `is_enabled`
  - `last_sync_at`
  - `last_sync_status`
  - `last_sync_run_id`
  - `last_error`
  - `created_at`
  - `updated_at`

说明:

- 一期虽然按单账号全局设计, 仍建议保留 `region_strategy` / `region_ids_json` 这类最小扩展位, 便于后续从“全地域”平滑演进到“指定地域”。
- 一期默认策略可直接使用 `all_regions`。

#### `aliyun_rds_instance_snapshots`

- 保存最近一次成功同步到的实例快照。
- 字段建议:
  - `id`
  - `external_id`
  - `region_id`
  - `instance_name`
  - `db_type`
  - `engine`
  - `engine_version`
  - `host`
  - `port`
  - `vpc_id`
  - `vswitch_id`
  - `zone_id`
  - `pay_type`
  - `instance_status`
  - `raw_payload`
  - `sync_run_id`
  - `synced_at`
  - `created_at`
  - `updated_at`

约束建议:

- `external_id` 唯一
- `(db_type, host, port)` 索引
- `synced_at` 索引

### 扩展 `instances` 主表

- 新增通用同步托管字段:
  - `sync_source`
  - `sync_external_id`
  - `is_sync_managed`
  - `sync_last_seen_at`

约束建议:

- 为 `(sync_source, sync_external_id)` 建唯一约束
- 对 `sync_source`、`is_sync_managed` 建索引

语义约定:

- 手工实例:
  - `sync_source IS NULL`
  - `sync_external_id IS NULL`
  - `is_sync_managed = false`
- 阿里云同步实例:
  - `sync_source = 'aliyun_rds'`
  - `sync_external_id = <aliyun dbinstance id>`
  - `is_sync_managed = true`

## 同步写入规则

### 实例归一化

从阿里云实例标准化为本地实例写入载荷时, 一期至少映射:

- `name`
- `db_type`
- `host`
- `port`
- `database_name` 置空
- `description` 由云端信息拼装为只读说明文本
- `is_active`
- `main_version`
- `database_version`
- `sync_source`
- `sync_external_id`
- `is_sync_managed`
- `sync_last_seen_at`

### Upsert 规则

同步写入必须遵循固定优先级:

1. 先按 `sync_source + sync_external_id` 命中已有同步实例
2. 若未命中:
   - 仅当存在且仅存在一条手工实例满足 `(db_type, host, port)` 精确匹配时, 接管该实例
   - 接管后写入 `sync_source` / `sync_external_id` / `is_sync_managed`
3. 如果没有可接管实例, 则创建新实例
4. 若出现以下歧义, 本条实例同步失败, 不做 silent fallback:
   - 同名不同源实例冲突
   - `(db_type, host, port)` 命中多条候选
   - 已有实例被其他同步源占用

### 名称冲突策略

- 禁止基于名称自动合并
- 禁止为避冲突自动重命名
- 冲突必须进入 `TaskRunItem.details_json` / `summary_json`, 给出明确原因

### 云端删除策略

- 同步完成后, 对所有 `sync_source='aliyun_rds'` 且本轮未 `last_seen` 的实例执行:
  - `deleted_at = now`
  - `is_active = false`
- 若后续同步再次命中该外部实例:
  - 清空 `deleted_at`
  - 恢复 `is_active` 为云端映射值
  - 保持原主键不变

## 实例域只读约束

### 写路径拦截

以下服务需要显式拒绝 `is_sync_managed=true` 的实例:

- `InstanceWriteService.update`
- `InstanceWriteService.soft_delete`
- `InstanceWriteService.restore`
- `InstanceBatchDeletionService.delete_instances`

返回语义:

- 使用明确业务错误, 文案统一为“同步托管实例不支持人工修改/删除/恢复”
- 不做 silent ignore

### 页面与接口表现

实例列表和详情需要新增字段:

- `sync_source`
- `is_sync_managed`

实例详情额外增加:

- `source_snapshot`

`source_snapshot` 一期至少提供:

- `external_id`
- `region_id`
- `engine`
- `engine_version`
- `instance_status`
- `host`
- `port`
- `synced_at`
- `last_seen_at`

前端表现:

- 列表增加“阿里云 RDS / 同步托管 / 只读”标识
- 详情页增加来源说明区块
- 编辑、删除、恢复按钮对同步实例隐藏或 disabled
- 批量删除时, 同步实例不可选或提交时被后端拒绝

## 与现有任务的解耦

### 必须跳过的链路

一期必须显式跳过 `sync_source='aliyun_rds'` 的实例:

- `accounts_sync`
- `capacity_sync`
- `audit_sync`
- 连接测试
- 任何依赖本地 `credential_id` 的主动连接逻辑

### 跳过位置

优先放在“任务实例枚举边界”处理:

- `FilterOptionsRepository.list_active_instances`
- 或对应 task/read service 增加排除同步来源的查询能力
- 或在 action service / runner 层统一过滤

目标是:

- 不改变 `instances` 主表中存在这类实例的事实
- 只改变“哪些实例可参与连接型任务”

### 不强制下线的链路

- `veeam` 这类外部匹配型能力可继续保留
- 前提是现有逻辑基于主机/IP 匹配且不会要求本地连接凭据

## 配置与调度

### `settings.py`

新增最小配置项:

- `ALIYUN_RDS_REQUEST_TIMEOUT_SECONDS`
- `ALIYUN_RDS_VERIFY_SSL`

原则:

- 所有配置统一经 `app/settings.py` 解析、默认值、校验
- 不在 provider 中散落读取环境变量

### Scheduler

新增 builtin job:

- `sync_aliyun_rds_instances`

需要同时更新:

- `app/scheduler.py` 的 `TASK_FUNCTIONS`
- `app/core/constants/scheduler_jobs.py`
- `app/config/scheduler_tasks.yaml`

默认调度:

- 每日 `00:30`

同时保留:

- 系统设置页手动触发同步
- scheduler 管理页“立即执行”

## API 与前端

### API

新增:

- `GET /api/v1/integrations/aliyun-rds/source`
- `PUT /api/v1/integrations/aliyun-rds/source`
- `POST /api/v1/integrations/aliyun-rds/actions/sync`

变更:

- 实例列表接口新增 `sync_source`、`is_sync_managed`
- 实例详情接口新增 `sync_source`、`is_sync_managed`、`source_snapshot`

### 系统设置页

新增 `Aliyun RDS` section:

- 绑定 API 凭据
- 查看 provider 状态
- 查看最近同步状态
- 手动触发同步

一期建议不提供“解绑并清空快照”按钮, 避免与“实例由同步托管”语义冲突。

## 测试计划

### Provider

- 地域列表拉取
- 按地域分页拉取实例
- 字段归一化
- HTTP 错误、网络错误、超时、SSL 开关

### 同步服务

- 新建同步实例
- 更新已有同步实例
- 接管唯一手工实例
- 名称冲突失败
- 候选实例多命中失败
- 云端缺失触发软删除
- 云端重新出现触发恢复

### 实例写路径

- 同步托管实例更新被拒绝
- 同步托管实例删除被拒绝
- 同步托管实例恢复被拒绝
- 批量删除包含同步实例时被拒绝或跳过并明确报错

### 任务回归

- `accounts_sync` 显式排除 `aliyun_rds` 实例
- `capacity_sync` 显式排除 `aliyun_rds` 实例
- 其他连接型链路不再因无凭据持续报错

### API / 前端契约

- 系统设置页导航新增 `Aliyun RDS`
- 绑定页存在固定 DOM id / data-api-url / data-sync-api-url
- 列表 / 详情出现同步托管只读标识
- 同步实例编辑删除入口不可用

### 迁移验证

- 仅新增 migration, 不修改历史 migration
- 空库 `flask db upgrade` 可通过
- 现有库 upgrade 可通过

## 实施注意点

- 现有仓库 `docs/plans/` 中的计划文档偏实现导向, 本文保留为设计与实施基线, 后续真正编码前可再拆一份更细的 implementation plan。
- `provider` 优先使用阿里云官方 Python SDK, 不建议自写签名。
- 若后续要支持多账号多地域, 优先扩展 `source_bindings` 结构, 不要推翻 `instances` 主表上的同步身份字段。

## 参考资料

- 阿里云 RDS Python SDK 调用示例: <https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/python-sdk-call-example>
- 阿里云 RDS SDK 概览: <https://help.aliyun.com/zh/rds/sdk-overview>
- 阿里云 RDS `DescribeDBInstances` OpenAPI: <https://next.api.aliyun.com/api/Rds/2014-08-15/DescribeDBInstances?RegionId=cn-beijing&lang=PYTHON&params=%7B%7D>
