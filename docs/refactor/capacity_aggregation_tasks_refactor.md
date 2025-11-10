# `app/tasks/capacity_aggregation_tasks.py` 重构方案

> 目标：在保持现有调度行为的前提下，瘦身 888 行的聚合任务脚本，充分复用 `app/services/aggregation` 目录下的聚合服务组件，降低重复逻辑、简化测试，并为后续扩展（新周期/新指标）铺路。

## 1. 现状回顾

| 维度 | 当前实现 |
| --- | --- |
| 调度入口 | `run_capacity_aggregation` / `run_capacity_instance_aggregation` 等函数手动处理锁、实例筛选、日志、错误；与 scheduler 通过函数引用绑定 |
| 周期逻辑 | 每个周期（daily/weekly/monthly/quarterly）调用 `_run_period_aggregation`，但传入的回调和状态字典处理导致大量重复代码 |
| 状态管理 | 通过 `_initialize_instance_state` + `_update_instance_state` 手动维护 `dict`，包含 record、period_results、error 列表等 |
| 与 `AggregationService` 的关系 | 任务层调用服务层，但仍在任务里实现聚合结果封装、数据库聚合调用、日志输出，造成双份逻辑 |
| 锁与重试 | 使用 Redis 锁 + try/except 管控；锁工具散落文件中，失败时只写日志，不区分永久/暂时错误 |
| 监控输出 | 自行统计 `processed_records`/`errors` 并拼接 message；服务层输出的数据结构未被完全复用 |

## 2. 重构原则

1. **任务层只负责 orchestration**：调度、锁、重试、指标上报；业务逻辑（实例/数据库聚合）全部交给 service 层。
2. **充分复用 `AggregationService`**：利用 `AggregationService` 的 `calculate_*` / `InstanceAggregationRunner` 能力，避免任务层重复统计。
3. **模块化状态机**：将 `_initialize_instance_state`/`_update_instance_state` 改写为 `AggregationTaskRunner` 类或 dataclass，用于收集结果/日志，减少散落字典操作。
4. **统一周期配置**：使用配置（如 `PERIODS = ["daily","weekly","monthly","quarterly"]`）驱动循环，而非多套几乎相同的函数。
5. **增强可测性**：拆分纯函数（实例过滤、锁获取等）以便单测；对服务层依赖注入 mock。

## 3. 拟议分层

```
tasks/capacity_aggregation_tasks.py
├── AggregationTaskRunner（新类）
│   ├── run_period(period_type)
│   ├── _collect_instance_results(...)
│   └── _collect_database_result(...)
├── run_capacity_aggregation()  # 现有 scheduler 入口
└── run_capacity_instance_aggregation()  # 若仍需要单实例模式

services/aggregation/
├── aggregation_service.py  # 现有
├── runners.py（可选合并现有 runner）
└── orchestrator.py（新，封装任务→服务调用的桥梁）
```

### AggregationTaskRunner 核心职责
- 接受 `AggregationService`、`sync_logger`、`lock_manager` 等依赖。
- 提供 `run_periods(periods: list[str])`，内部循环调用 `service.calculate_*` 或 `service.calculate_instance_*`。
- 捕获 service 返回结果，转换为统一的任务日志/指标结构（成功、跳过、失败）。
- 对接锁和任务状态的出入口（开始/结束/异常）。

## 4. 具体改造步骤

1. **整合周期驱动配置**
   - 定义 `PERIOD_CONFIG = [{"key": "daily", "service_method": "calculate_daily_aggregations", ...}, ...]`。
   - `run_capacity_aggregation` 遍历配置列表，调用 runner 方法，无需手写四个函数。

2. **封装状态与日志**
   - 新建 `AggregationTaskRunner`（可放在同文件或 `services/aggregation/task_runner.py`）：
     ```python
     class AggregationTaskRunner:
         def __init__(self, service: AggregationService, logger):
             self.service = service
             self.logger = logger
         def run_period(self, period_key: str) -> dict:
             result = getattr(self.service, f"calculate_{period_key}_aggregations")()
             self._log_period_summary(period_key, result)
             return result
     ```
   - `_log_period_summary` 负责统一的 info/warn/error 输出；`_collect_instance_results` 可直接使用 service 返回的结构。

3. **利用 service runner**
   - `AggregationService` 已提供 `InstanceAggregationRunner`/`DatabaseAggregationRunner`，任务层无需再处理 `instance_func`/`database_func` 回调。
   - 若 service 暂未暴露需要的统计，可在 service 内新增 `build_period_summary(period_type)`，返回任务层所需的 `processed/failed/etc` 字段。

4. **锁与异常管理**
   - 提炼 `_acquire_capacity_job_lock` → `CapacityLockManager`（可放 `services/aggregation/lock_utils.py`），提供 `with lock_manager.job_lock(period): ...` 上下文，减少 try/finally 代码。
   - 异常分类：判断 service 抛出的 `ValidationError` / `DatabaseError`，写入不同级别日志；必要时决定是否重试。

5. **删除冗余函数**
   - `_run_period_aggregation`、`_initialize_instance_state`、`_update_instance_state`、`_update_summary` 等函数在 runner 结构下可逐步删除或缩减。
   - 若 `records_by_instance` / `SyncInstanceRecord` 等数据只用于旧管线，可迁出到 service，任务层不再维护。

6. **编写文档与测试**
   - 在 `docs/reports/capacity_aggregation_tasks_refactor.md`（即本文）记录新版架构。
   - 增加单元测试：mock `AggregationService`，验证任务在成功/失败场景下的日志和返回值。
   - 更新调度配置/README，说明任务文件重构后的依赖。

## 5. 兼容性与风险

| 风险 | 对策 |
| --- | --- |
| scheduler 依赖旧的函数签名 | 保持 `run_capacity_aggregation()` 外部接口不变，仅内部使用 runner |
| service 返回数据结构变动 | 在 service 层先新增方法（双写），确保任务迁移完成后再移除旧逻辑 |
| 锁/事务行为改动 | 在过渡期保留原有锁工具，重构完成后再考虑引入统一的 LockManager |

## 6. 里程碑建议

1. **短期（1 PR）**：引入 `AggregationTaskRunner`，用配置表驱动周期循环；保持 service 接口不变。
2. **中期（2-3 PR）**：将 `_run_period_aggregation` 中的业务细节迁入 `AggregationService` 或新建 orchestrator，删除冗余函数。
3. **长期**：合并 `capacity_aggregation_tasks.py` 与 `services/aggregation/*` 中重复的日志/状态统计逻辑；评估将调度迁入统一任务框架。

通过以上步骤，可显著降低任务脚本复杂度，充分利用 `app/services/aggregation` 现有组件，实现“调度与业务解耦、可维护性提升”的目标。***
