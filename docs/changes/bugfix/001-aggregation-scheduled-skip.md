---
title: 统计聚合定时任务误判"所有周期均已聚合"导致跳过
status: draft
owner: WhaleFall Team
created: 2026-01-14
updated: 2026-01-14
scope: scheduler + aggregation (calculate_database_size_aggregations)
related:
  - app/tasks/capacity_aggregation_tasks.py
  - app/services/aggregation/capacity_aggregation_task_runner.py
  - app/repositories/aggregation_repository.py
  - app/services/scheduler/scheduler_actions_service.py
---

# 统计聚合定时任务误判"所有周期均已聚合"导致跳过

## 症状与影响

### 症状

- 定时任务 `calculate_database_size_aggregations` 按 cron 配置在 04:00 (Asia/Shanghai) 触发,但日志提示: "所有周期均已聚合,任务直接跳过".
- 通过管理后台"手动执行"同一任务时,任务可以正常执行并产出聚合结果.

### 影响

- 定时任务可能在"聚合数据不完整"时提前跳过,导致容量聚合数据缺失/不更新.
- 现场排查容易被误导: "手动执行成功"并不代表"定时任务判断正确",因为手动执行会走不同分支(见根因分析).

## 复现步骤

> 说明: 复现依赖数据库中存在"部分聚合落库"的状态,常见于历史运行中部分实例失败/未处理,或只对少量实例进行了手动聚合.

1. 保证存在多个 `is_active=true` 的实例.
2. 构造某个 period 的聚合落库为"部分完成":
   - `instance_size_aggregations` 中仅有部分实例在 `period_type=X && period_start=Y` 的记录.
   - `database_size_aggregations` 中也仅有部分实例在 `period_type=X && period_start=Y` 的记录(任意数据库即可).
3. 触发定时任务入口(模拟调度器调用): `calculate_database_size_aggregations(manual_run=false, periods=None)`.
4. 观察返回值/日志: 可能出现 "所有周期均已聚合,任务直接跳过".
5. 触发手动执行(模拟后台"立即执行"): `calculate_database_size_aggregations(manual_run=true, periods=None)`.
6. 观察行为: 任务继续执行,并对已有聚合做 update 或补齐缺失实例的聚合记录.

## 根因分析

### 关键分支差异: scheduled vs manual

- 定时任务入口在满足条件时会启用"已聚合则跳过"逻辑:
  - 位置: `app/tasks/capacity_aggregation_tasks.py:60-68`.
  - 条件: `manual_run=false` 且 `periods is None`.
- 管理后台"手动执行"会强制注入 `manual_run=true`,从而绕过上述跳过逻辑:
  - 位置: `app/services/scheduler/scheduler_actions_service.py:107-113`.

### "已聚合"判定过于宽松,导致误判

- 跳过逻辑会对每个 period 计算 `period_start`(使用上一周期):
  - 位置: `app/services/aggregation/capacity_aggregation_task_runner.py:104-109`.
  - 具体周期计算: `app/services/aggregation/calculator.py:get_last_period`.
- 当前 `has_aggregation_for_period(period_type, period_start)` 的实现只检查"是否存在任意一条记录":
  - 位置: `app/repositories/aggregation_repository.py:24-48`.
  - 判定规则: 同 `period_type + period_start` 下:
    - `database_size_aggregations` 只要存在任意一行即视为数据库级聚合存在.
    - `instance_size_aggregations` 只要存在任意一行即视为实例级聚合存在.
  - 问题: 该判定没有校验"是否覆盖所有活跃实例",因此当只有部分实例完成聚合时,仍可能被认为"该周期已聚合",进而导致 scheduled 分支跳过.

## 修复方案

### 修复目标

- scheduled 分支只在"目标周期已完成聚合(覆盖口径明确)"时才跳过,避免误判导致的数据缺失.
- 保持任务幂等: 即使重复执行,也只会 update/补齐,不产生不一致.
- 保持 manual 分支语义: 手动执行继续可以强制重算/补齐(不受跳过逻辑影响).

### 方案 A (推荐): 用"实例覆盖度"替代"任意记录存在"

将 `has_aggregation_for_period()` 从"任意记录存在"升级为"周期聚合已覆盖所有应处理实例".

定义建议:

- `active_instance_ids`: 当前活跃实例集合.
- `aggregated_instance_ids_instance`: `instance_size_aggregations` 在 `period_type + period_start` 下的 `distinct(instance_id)`.
- `aggregated_instance_ids_database`: `database_size_aggregations` 在 `period_type + period_start` 下的 `distinct(instance_id)`.
- 当且仅当:
  - `active_instance_ids` 被 `aggregated_instance_ids_instance` 覆盖,且
  - `active_instance_ids` 被 `aggregated_instance_ids_database` 覆盖,
  - 才认为该 `period_type + period_start` 已完成聚合,允许 scheduled 跳过.

优点:

- 直接修复"部分实例已聚合"导致的误判.
- 实现成本低,可通过 count/distinct 查询完成.

注意点(需要在实现时确认口径):

- 若某些活跃实例在该周期没有原始统计数据(容量采集缺失),聚合表可能不会产生记录.此时严格的"active 覆盖"会导致任务每天都跑而无法满足跳过条件.
  - 可接受的 v1 行为: 宁可多跑,也不误跳过.
  - 如需优化,见方案 B.

### 方案 B (可选增强): 基于"有输入数据的实例"作为覆盖口径

在方案 A 的基础上,将 `active_instance_ids` 换成"该周期存在输入数据的实例集合",避免无数据实例导致的永久不跳过.

示例口径:

- `eligible_instance_ids_instance`: `instance_size_stats` 在 period 范围内存在记录的 `distinct(instance_id)`.
- `eligible_instance_ids_database`: `database_size_stats` 在 period 范围内存在记录的 `distinct(instance_id)`.
- 当 `eligible` 集合为空时,该周期可直接视为"无需处理"(可跳过或返回更明确的 skip 原因).

优点:

- 可以在"无输入数据"场景下稳定跳过,降低无效执行.

代价:

- 需要额外查询 stats 表,并依赖 period_end(当前过滤逻辑已计算 end_date,实现可复用).

### 日志与可观测性(建议同步修复)

当发生跳过时,建议在日志中输出:

- 计算出的 `period_start`(以及 period_end).
- active/eligible/aggregated 的实例数量对比.
- 被判定为"未覆盖"的实例 ID 列表(可截断).

目的: 让现场定位可以直接判断是"真实跳过"还是"误判风险".

## 回归验证

### 单元测试建议

- 覆盖 `filter_periods_already_aggregated()` 的关键场景:
  1. 0 条聚合记录: 不跳过.
  2. 仅 1 个实例有聚合记录,但活跃实例 > 1: 不跳过.
  3. 所有活跃实例均有聚合记录: 跳过.
  4. `manual_run=true` 或 `periods != None`: 不进入跳过逻辑(保持原行为).

### 手工验证建议

- 在管理后台观察 04:00 后的任务执行结果,确认:
  - 若存在缺失实例,scheduled 不再误跳过.
  - 若全部完成,scheduled 仍可跳过以节省执行时间.

## 风险与回滚

### 风险

- scheduled 任务可能在一段时间内更频繁执行(尤其是存在长期无数据的活跃实例时).
- 新增查询可能增加 DB 压力(可通过 count/distinct 且复用索引降低影响).

### 回滚

- 回滚点清晰: 恢复 `has_aggregation_for_period()` 为旧的"任意记录存在"判定即可.
- 若同步调整了日志/口径,回滚时需一并恢复以避免口径混乱.

## 遗留问题

- "无输入数据的活跃实例"是否应长期保持 active: 这属于数据治理/运维策略,可能需要单独规范或自动降级机制.
- 是否需要引入"周期水位线/运行快照"持久化,用于更可靠地判定某周期是否已完成聚合(避免仅靠聚合表推断).
