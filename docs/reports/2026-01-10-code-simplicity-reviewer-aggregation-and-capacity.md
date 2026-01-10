# Aggregation and Capacity Simplicity Audit (code-simplicity-reviewer)

> 状态: Draft  
> 负责人: team  
> 创建: 2026-01-10  
> 更新: 2026-01-10  
> 范围: `docs/Obsidian/reference/service/aggregation-pipeline.md`, `capacity-*.md`, `database-sync-*.md` -> `app/services/aggregation/**`, `app/services/capacity/**`, `app/services/database_sync/**`

## app/services/aggregation/aggregation_service.py

## Simplification Analysis

### Core Purpose
统一编排周期聚合: 计算 period window, 调用 runner 执行 database/instance 聚合, 汇总状态, 对外提供查询接口.

### Unnecessary Complexity Found
- 周/月/季等大量 wrapper 方法在 `app/**` 内未见调用(疑似 YAGNI), 但占据了大量行数与维护面.
- `_ensure_partition_for_date()` 明确为占位返回(117-126), 但仍作为 runner 注入依赖, 属于接口性复杂度.
- 同构逻辑在 database vs instance 两套 runner API 之间重复(多个 `calculate_*` wrapper).

### Code to Remove
- 删除未使用的 wrapper, 或保留单一 `calculate(period_type, scope, ...)` 并让路由层做映射.
- 若分区逻辑在当前环境无意义, 移除 `_ensure_partition_for_date` 依赖注入, runner 直接不依赖.
- Estimated LOC reduction: 150-300

### Simplification Recommendations
1. 保留最小 public API
   - 建议保留: `aggregate_current_period`, `calculate_daily_*`(若确实被调用), `get_*` 查询接口.
2. 收敛 period dispatch
   - Current: 多处构造 mapping(`_database_methods`, `period_funcs`) + 多个 wrapper.
   - Proposed: 单一 mapping 常量 + 单一执行入口.
3. 推动 runner 承担更多职责
   - Service 只做参数校验与汇总, runner 负责实际执行, 避免 service 变成 God module.

### YAGNI Violations
- 为未来周期提前准备的 wrapper, 如果没有现存调用路径, 建议按需再加回.

### Final Assessment
Total potential LOC reduction: 15-30%  
Complexity score: High  
Recommended action: Proceed with simplifications(先删未引用 wrapper, 再做结构化拆分)

## app/services/capacity/current_aggregation_service.py

## Simplification Analysis

### Core Purpose
为 "手动触发当前周期聚合" 提供事务与会话编排: 创建 SyncSession/records, 绑定 runner callbacks, 收敛结果结构.

### Unnecessary Complexity Found
- 强制 period_type 为 daily 并忽略 request 中的 requested_period_type(70-103), 行为与接口面不一致.
- service 内依赖 `flask_login.current_user` 获取 created_by, 引入隐式全局依赖, 降低可测性与可复用性.
- 多处构造近似相同的 `sync_details` dict(例如 result/error/finalize 分支), 重复.

### Code to Remove
- 统一 `sync_details` 构造 helper.
- 将 created_by 从 request 或调用方注入, 移除对 `current_user` 的依赖.
- Estimated LOC reduction: 40-80

### Simplification Recommendations
1. 明确 API 契约
   - 要么支持 requested_period_type, 要么从 request 类型移除该字段.
2. 让 service 无 web context 依赖
3. 将 callbacks 与 state 结构最小化

### YAGNI Violations
- 既暴露 requested_period_type 又强制覆盖, 容易变成长期技术债.

### Final Assessment
Total potential LOC reduction: 10-20%  
Complexity score: Medium  
Recommended action: Proceed with simplifications

## app/services/capacity/instance_capacity_sync_actions_service.py

## Simplification Analysis

### Core Purpose
编排单实例容量同步: connect -> inventory -> collect stats -> save -> best-effort trigger aggregation.

### Unnecessary Complexity Found
- 通过 `import ... as module` 再取类的方式使用 coordinator/aggregation, 增加阅读跳转成本(通常是为循环依赖兜底).
- best-effort 触发聚合使用 `except Exception` 并仅 warning, 虽合理但建议将异常面收窄到可预期类型.

### Code to Remove
- 若不存在循环依赖, 改为直接 import class, 删除 module alias.
- 统一 error result 的重复 dict 结构.
- Estimated LOC reduction: 15-40

### Simplification Recommendations
1. 让依赖更显式
2. 将 "aggregation trigger" 抽成单独 helper, 让主流程更短

### YAGNI Violations
- None(主要是组织结构与依赖可读性)

### Final Assessment
Total potential LOC reduction: 5-15%  
Complexity score: Medium  
Recommended action: Minor tweaks only

## app/services/capacity/database_aggregations_read_service.py

## Simplification Analysis

### Core Purpose
将 repository 的 ORM projection 转换为稳定 DTO, 提供分页与 summary.

### Unnecessary Complexity Found
- 28 个局部 `cast()` 变量造成明显类型噪声, 让主要逻辑(构建 DTO)难以扫描.
- pagination 的 get_all 分支与常规分支重复构造 `DatabaseAggregationsListResult`.

### Code to Remove
- 抽取 `_to_item(aggregation, instance)` 并在内部做最少的 coercion.
- 复用 `PaginatedResult` 或统一分页 result builder.
- Estimated LOC reduction: 30-60

### Simplification Recommendations
1. 将类型噪声移出主循环
2. 在 types 层提供更强的 repository return typing

### YAGNI Violations
- None

### Final Assessment
Total potential LOC reduction: 15-25%  
Complexity score: Medium  
Recommended action: Proceed with simplifications

## app/services/database_sync/database_sync_service.py

## Simplification Analysis

### Core Purpose
遍历所有活跃实例执行容量采集, 并允许 partial_success.

### Unnecessary Complexity Found
- `DATABASE_SYNC_EXCEPTIONS` 列表偏大, 与 "只要失败就记录并继续" 的语义相比维护成本高.

### Code to Remove
- 将异常捕获收敛为 `Exception` 并在日志中记录 error_type, 或只保留 domain exceptions.
- Estimated LOC reduction: 5-15

### Simplification Recommendations
1. 让异常策略更可解释: "任何异常都视为该实例失败, 继续下一个".

### YAGNI Violations
- None

### Final Assessment
Total potential LOC reduction: 0-10%  
Complexity score: Low-Medium  
Recommended action: Minor tweaks only

## app/services/database_sync/adapters/factory.py

## Simplification Analysis

### Core Purpose
根据 db_type 返回对应 capacity adapter 实例.

### Unnecessary Complexity Found
- 无

### Final Assessment
Total potential LOC reduction: 0%  
Complexity score: Low  
Recommended action: Already minimal

## app/services/database_sync/table_size_coordinator.py

## Simplification Analysis

### Core Purpose
按 database 采集表容量快照并做 upsert + cleanup, 对不同 DB 类型选择不同 table size adapter.

### Unnecessary Complexity Found
- `_InstanceConnectionTarget` 仅用于满足 connection adapter 的入参类型, 属于 workaround, 增加理解成本.
- 使用 adapter 的私有方法 `_safe_to_int`(疑似越界依赖), 会造成未来改动摩擦.
- dialect 分支(sqlite/postgres)写在 service 内, 若长期只跑一种数据库可考虑简化.

### Code to Remove
- 将 `_InstanceConnectionTarget` 替换为更直接的 connection adapter 构造接口(接收 host/port/db_name/credential).
- 把 `_safe_to_int` 提取为公共 util.
- Estimated LOC reduction: 20-60(取决于 adapter 接口演进)

### Simplification Recommendations
1. 降低 workaround 比例
2. 限制对私有方法的依赖

### YAGNI Violations
- sqlite/postgres 双分支若只是测试用途, 可评估是否上移到 repository 或 util.

### Final Assessment
Total potential LOC reduction: 5-15%  
Complexity score: Medium  
Recommended action: Proceed with simplifications(以接口清理为主)

