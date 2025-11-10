# 实例批量操作现状分析

> 范围聚焦 `app/routes/instance.py` 中的批量创建与批量删除接口，目的是为后续拆分专用模块/服务提供依据。

## 1. 路由与辅助函数概览

- `POST /instances/api/batch-create` → `batch_create`
  - 入口最初同时支持 JSON 与 CSV；现已调整为仅接受 CSV 文件并委托 `_create_instances`（历史实现 `_process_instances_data`）。
  - 旧版 `_process_instances_data` 直接使用 ORM 创建 `Instance` 记录，并在循环内追加到 `db.session`。
- `POST /instances/api/batch-delete` → `batch_delete`
  - 入口直接遍历 `instance_ids`，调用 `_delete_instance_related_data` 清理部分关联表，然后 `db.session.delete(instance)`。
- `_delete_instance_related_data`
  - 仅处理 `AccountClassificationAssignment`、`AccountPermission`、`SyncInstanceRecord`、`AccountChangeLog` 四张表。

整体来看，批量逻辑完全耦合在路由文件内，且与页面渲染、单个实例 CRUD、统计 API 混杂在一起。

## 2. 批量创建现状

| 关注点 | 现状/问题 |
| --- | --- |
| 数据校验 | 依赖 `DataValidator.validate_batch_data`，但函数返回的 `validation_errors` 只是附加到错误列表，没有阻断后续创建；单条数据可能部分缺字段也会继续尝试写库。 |
| 唯一性检查 | 每条记录都发起一次 `Instance.query.filter_by(name=...)`，缺少缓存或批量查询；同名但不同实例 ID 时只返回字符串错误，未对 host/db_type 做组合校验。 |
| 事务管理 | 所有新增共用一次提交。循环中任何异常只记录错误并继续，但最终 `db.session.commit()` 如果失败则整体回滚且没有区分成功/失败集合。 |
| 结构同步 | 仅写 `Instance` 主表，未补充 `InstanceDatabase`、`InstanceAccount` 等衍生表的初始化逻辑，也没有触发与同步、标签或缓存相关的后置操作。 |
| 代码耦合 | `_process_instances_data` 引 current_user、日志、验证、ORM，难以在别处复用或单测。 |

## 3. 批量删除现状

| 关注点 | 现状/问题 |
| --- | --- |
| 结构覆盖范围 | `_delete_instance_related_data` 只删除 4 张旧表：`AccountPermission`、`AccountClassificationAssignment`、`SyncInstanceRecord`、`AccountChangeLog`。随着近几次表结构重构，仍然引用 `instance_id` 的模型包括 `InstanceAccount`、`InstanceDatabase`、`InstanceSizeStat`、`InstanceSizeAggregation`、`DatabaseSizeStat`、`BaseSyncData` 子表等——目前均未清理，残留大量孤儿数据。 |
| 事务一致性 | `batch_delete` 逐条执行删除但只在循环结束后统一 `db.session.commit()`；当某条删除失败时直接 `continue`，导致前面已 `db.session.delete(instance)` 的对象仍留在 session 中，后续提交时可能触发 IntegrityError 或删除未完全清理的实例。 |
| 关联检查 | 入口阶段统计 `related_data_counts` 仅用于提示，没有阻止操作；同一轮中若 `_delete_instance_related_data` 抛异常会直接 `continue`，但没有针对用户回传可重试的信息。 |
| 权限/状态 | 无论实例是否已停用/删除都会再次删除；也未考虑软删除（`Instance.deleted_at`）或外键约束（如 `InstanceAccount.instance_id`）。 |
| 性能与日志 | 每个实例都重复查询/删除相同的表，没有批处理；清理统计信息以 Python 变量累计，没有返回失败列表。 |

## 4. 拆分方向初稿

1. **抽象服务层**  
   - 新建 `app/services/instances/batch_service.py`（或类似命名），对外暴露 `create_instances_from_payload(...)` 与 `delete_instances(instance_ids, *, force=False)`。
   - 服务内处理事务、日志、校验、回滚策略；路由仅负责解析请求与返回响应。

2. **批量删除专用清理器**  
   - 设计 `InstanceCascadeDeletionPlan`，集中列出所有需要删除/软删除的模型，并支持按数据库类型扩展。
   - 清理顺序可参考：`AccountClassificationAssignment` → `AccountPermission/AccountChangeLog` → `InstanceAccount` → `InstanceDatabase` → 统计表 (`InstanceSizeStat`/`DatabaseSizeStat`/聚合) → 其他引用 `instance_id` 的业务表 → `Instance`。
   - 考虑拆分为“预检查”（返回关联数量与阻塞原因）+“执行”两步，以便前端确认风险。

3. **批量创建优化**  
   - 引入批量校验结构，先构建 `InstancePayload` 列表并基于 set 进行重复检测，减少数据库 round-trip。
   - 支持异步导入（上传 CSV → 后台任务），便于处理上千条记录。
   - 与凭据、标签等新结构保持一致：例如 tags 不应硬编码 `{}`，而是交给 TagService 处理。

4. **文档与测试**  
   - 编写拆分后 API 行为说明（成功/失败部分返回格式、事务语义）。
   - 增加单元测试覆盖：空列表、部分失败、关联数据残留、CSV 解析异常等场景。

## 5. 立即可见的风险

- 现有批量删除在新结构下已经无法保证数据一致性，数据库中存在大量孤儿记录。
- 批量创建未同步最新字段/约束（如多租户、标签、同步策略），容易生成不可用实例，需要尽快重构。

建议先按上述分析补齐删除链路，再规划路由拆分与服务化，实现可维护的批量操作能力。

## 6. 已执行的改进（batch 分支）

- 新增 `app/services/instances/batch_service.py`，封装 `InstanceBatchCreationService` 与 `InstanceBatchDeletionService`，统一做输入校验、日志与事务管理。
- `app/routes/instance.py` 中的批量创建、批量删除以及单个删除接口已经接入服务层，路由只负责请求解析与响应封装。
- 删除流程覆盖 `AccountPermission`、`AccountClassificationAssignment`、`SyncInstanceRecord`、`AccountChangeLog`、`InstanceAccount`、`InstanceDatabase`、`InstanceSizeStat/InstanceSizeAggregation`、`DatabaseSizeStat/DatabaseSizeAggregation` 以及 `instance_tags` 关联表，避免产生孤儿数据。
***
