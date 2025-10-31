# DatabaseSizeAggregationService 重构提案

> 面向现有 `DatabaseSizeAggregationService`（约 1.6k 行）的瘦身计划，目标是拆分出职责明确的组件，让代码更易读、更易测、更易扩展。

## TL;DR
- 维持单一入口：`DatabaseSizeAggregationService` 对外接口保持不变，定时任务与手动按钮两处调用无需改动。
- 内部分层：拆分日期计算、数据库聚合、实例聚合、结果封装，让核心逻辑可单独测试。
- 数据模型复用：继续使用现有 ORM 模型，并将 `PeriodSummary` 等数据类抽出复用，避免一次性大迁移。
- 渐进式落地：阶段化改造，每一步可独立合入、随时回滚。
- 缓存沿用现有 Redis 封装（`CacheManager` 等），新增的“当前周期”能力直接复用当前基础设施。

---

## 当前痛点
- **文件过大**：同一个类同时负责日期推算、分区管理、SQL 查询、数据格式化。
- **重复逻辑多**：Daily/Weekly/Monthly/Quarterly 复制粘贴，实例级与数据库级高度相似。
- **调用语义混乱**：两个入口（定时任务、后台按钮）都走 `calculate_daily_aggregations()` 等方法，语义依赖调用场景。
- **测试困难**：核心逻辑夹杂日志、DB 访问、分区操作，难以编写细粒度单元测试。

---

## 重构目标
1. 将“算什么”和“怎么算”解耦，核心计算逻辑可单独测试。
2. 提供语义清晰的入口方法，调用者看到接口即可理解行为。
3. 保持数据库结构、任务调度不变，聚焦 Python 代码重构。
4. 对外行为保持与现有实现一致（接口、返回结构、日志字段）。
5. 留出后续性能优化（批量查询、缓存）的扩展点。

---

## 调用入口与影响范围
- 定时任务：调度器周期性调用 `DatabaseSizeAggregationService`，需验证改造后行为一致。
- 后台按钮：管理端触发聚合的接口同样走 Facade，改造后路线保持不变，只更新内部装配。

## 目标架构
```
DatabaseSizeAggregationService  (Facade, 入口不变)
├── PeriodCalculator            # 处理 daily/weekly/... 的日期范围
├── DatabaseAggregationRunner   # 针对 DatabaseSizeStat 的批量聚合
├── InstanceAggregationRunner   # 针对 InstanceSizeStat 的批量聚合
└── Result builders             # PeriodSummary / InstanceSummary 等数据类
```

### 组件职责简表
| 模块 | 职责 | 备注 |
| --- | --- | --- |
| `PeriodCalculator` | 计算每日/每周/每月/每季度的时间范围，以及“上一周期” | 纯函数，可单测 |
| `DatabaseAggregationRunner` | 聚合数据库级数据，返回 `PeriodSummary` | 共享查询/聚合工具 |
| `InstanceAggregationRunner` | 聚合实例级数据，返回 `PeriodSummary` | 共享查询/聚合工具 |
| `results.py` | 数据类：`AggregationStatus`、`PeriodSummary`、`InstanceSummary` | 抽离自现有 service，供 Runner/Facade 共用 |
| `DatabaseSizeAggregationService` | 门面：组合调用上述组件，对外暴露旧接口 | 负责装配与日志 |

> **模块组织**：创建 `app/services/aggregation/` 包，内含 `database_size_aggregation_service.py`（Facade）、`calculator.py`、`database_runner.py`、`instance_runner.py`、`results.py` 等组件，对外通过 `app.services.aggregation` 暴露 Facade，所有调用方统一从新包导入。

---

## 核心流程（以每日聚合为例）
1. `service.calculate_daily_aggregations()` 调用 Facade。
2. Facade 使用 `PeriodCalculator` 计算今日日期范围。
3. Facade 将范围传给 `DatabaseAggregationRunner.aggregate_period()`。
4. Runner 批量查询 `DatabaseSizeStat`，按实例 + 数据库分组后计算指标。
5. Runner 写入 `DatabaseSizeAggregation` 后返回 `PeriodSummary`。
6. Facade 组合多个周期结果，返回与现在相同的数据结构。

> **实例聚合** 复用同样的流程，只是底层 Runner 不同，处理 `InstanceSizeStat`。

---

## 数据源假设
- 所有聚合数据均来自 PostgreSQL（`DatabaseSizeStat` / `InstanceSizeStat`），无需区分异构数据库类型。
- Runner 直接复用统一字段进行统计，如未来出现新类型，可再引入适配层扩展，但本轮改造不引入额外抽象。

---

## 支持聚合“当前周期”
- `PeriodCalculator` 在计算周期时新增 `get_current_period(period_type)`，例如本周（周一至今天）、本月（1 号至今天）。
- Facade 暴露 `aggregate_current(period_type="weekly")` 等便捷方法，供手动触发或实时需求使用（前端按钮）。
- Runner 只根据传入的日期区间聚合，不再区分“历史”与“当前”；数据点不足时按实际数据生成统计。
- 聚合指标（均值、最大值、趋势）只基于已有观测值计算，不补虚拟数据点；缺失的日期在结果元数据中标记，便于前端提示“数据不完整”。
- 现有历史任务仍调用 `get_last_period`，实现与当前周期逻辑并存，避免行为混淆。

### 手动按钮交互设想
1. 前端触发 `POST /aggregations/current?period=monthly`。
2. 路由调用 Facade 的 `aggregate_current(period_type)`。
3. Facade 获取当前周期范围，并将 `strict=False` 传给 Runner，允许缺失数据。
4. Runner 汇总真实存在的数据点：
   - 平均值：实际数据求平均（`sum(values) / len(values)`）。
   - 最大/最小值：对已有观测取极值。
   - 变化率：与上一周期对比时若上一周期也存在缺口，则只在两个周期都有值的情况下才计算百分比，否则返回 `None` 并在消息中说明。
5. 返回 `PeriodSummary`，其中 `processed_instances` 统计有数据的实例，`skipped_instances` 记录无数据或仅有部分数据导致无法判断趋势的实例。

> 当前周期聚合默认保持轻量：不写入数据库，只生成即时汇总即可，避免与定时任务写入冲突。

### 性能与缓存策略
- 统计范围有限：当前周期数据量通常只覆盖最近几天/几周，远小于历史全量聚合，查询压力可控。
- 默认使用短期缓存：复用现有 Redis 封装（如 `CacheManager`），缓存键建议统一为 `db_size_agg:current:{period_type}` 或加实例 ID。
- 手动触发前调用缓存管理器清理对应键，再写入新的缓存快照；Facade 内部可在极短时间内（二次点击）直接返回缓存。
- 若未来需要持久化，可引入可选 `persist=True` 参数，将结果写入快照表，后台异步清理过期记录。

---

## 渐进式实施计划

### 阶段 0：准备
- 新建 `app/services/aggregation/`，放置数据类与工具组件。
- 将现有 `AggregationStatus`、`PeriodSummary`、`InstanceSummary` 抽离到 `results.py` 并更新 Facade 引用，保持返回结构不变。

### 阶段 1：日期与结果
- 将 `_get_previous_period_dates`、周期计算逻辑迁移至 `PeriodCalculator`。
- Facade 继续沿用旧方法名称，但内部从 `PeriodCalculator` 取日期。
- 为 `PeriodCalculator`、`PeriodSummary` 写基础单元测试。

### 阶段 2：数据库级 Runner
- 提取 `_calculate_aggregations`、`_calculate_database_aggregation`、`_calculate_change_statistics` 至 `DatabaseAggregationRunner`。
- Runner 对外提供：`aggregate_period(period_type, start, end)`。
- Facade 中 daily/weekly/monthly/quarterly 方法只负责：求日期 → 调 Runner → 记录日志。

### 阶段 3：实例级 Runner
- 类似阶段 2，将实例相关逻辑迁移至 `InstanceAggregationRunner`。
- 合并单实例聚合代码，Runner 暴露 `aggregate_instance(instance_id, period_range)`，Facade 调用并封装返回值。

### 阶段 4：清理与文档
- 删除旧的内联方法，保留 Facade + 新组件。
- 更新任务脚本、路由引用，文档同步。
- 视情况引入批量查询 / 缓存优化，可选。

---

## 验证与测试
- **单元测试**：`PeriodCalculator`、Runner 使用工厂数据测试，聚焦纯计算逻辑。
- **集成测试**：沿用现有 `tests/integration` 用例，重点验证定时任务、后台按钮的端到端行为。
- **性能监测**：对比重构前后相同时间段的执行耗时和数据库查询数量。
- **缓存验证**：为 `aggregate_current` 添加强制缓存失效与命中场景的测试或脚本，确保与 `CacheManager` 对接正确。
- **日志核对**：确保日志字段不变，便于观察与报警。

---

## 风险与回滚
- 主要风险：Runner 数据写入逻辑偏差 → 加强集成测试；上线前执行一次对比脚本（新旧聚合结果对比）。
- 回滚策略：保留旧服务实现文件（git tag），若发现异常直接回滚 PR。

---

## 下一步建议
1. 完成阶段 0～2 后合入主干，先确保数据库级聚合稳定。
2. 阶段 3 可与实例聚合性能优化一并推进。
3. 重构完成后，将依赖文档纳入 README / 架构图，方便后续审查。
