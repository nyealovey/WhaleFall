# 仪表盘容量汇总改为“最新记录口径”设计

> 状态: 已确认
> 创建: 2026-01-16
> 目标模块: `app/services/dashboard/dashboard_overview_service.py`
> 关联页面: 系统仪表盘（DashboardOverviewPage）

## 背景

目前仪表盘“总容量”在服务端使用 `now_china() - 7 天` 作为起始时间窗口，导致容量汇总口径与“容量统计(实例)”页面（按最新记录 + 用户选择的周期）不一致。需求明确：仪表盘应采用**最新数据口径**，仅“错误/告警日志趋势图”保留最近 7 天统计。

## 目标

- 仪表盘容量汇总取**每个活跃实例的最新一条容量记录**，不受日期窗口限制。
- 日志趋势图仍保持最近 7 天区间。
- 变更范围尽量小，不引入新的防御性逻辑或复杂配置。

## 决策

采用方案 1：
- 继续使用 `CapacityInstancesRepository.summarize_latest_stats(...)` 作为汇总入口；
- 在 `get_system_overview()` 中**移除 `start_date` 过滤**（不再传 `recent_date`）。

该方案改动小、行为清晰，可直接实现“最新记录口径”。

## 方案设计

### 数据口径

- 汇总来源：`instance_size_stats` 表中**每个实例最新的 `collected_at` 记录**。
- 过滤条件：实例需 `is_active = true` 且 `deleted_at is null`（沿用现有逻辑）。
- 不设置 `start_date/end_date`，即不限制时间范围。

### 代码改动点

- `app/services/dashboard/dashboard_overview_service.py`：
  - 删除 `recent_date = now_china() - 7 days` 的时间窗口；
  - `InstanceAggregationsSummaryFilters` 不再传入 `start_date`。

### 日志趋势图保持 7 天

- 仍由 `fetch_log_trend_data(days=7)` 提供。
- 不改 `dashboard_charts_service` 与日志统计逻辑。

## 数据流说明

1. 仪表盘页面加载 → `get_system_overview()`。
2. `CapacityInstancesRepository.summarize_latest_stats()`：
   - 对每个实例取最新 `collected_at` 记录；
   - 汇总 `total_size_mb / avg / max`。
3. 前端模板展示：`total_gb` → `TB`。

## 错误处理

- 保持现有日志记录与回退逻辑（SQLAlchemy 异常时总容量为 0）。
- 本次不新增新的兜底分支。

## 缓存策略

- 维持 `@dashboard_cache(timeout=300)`。
- 若后续需要更强实时性，再单独评估“强制刷新/缩短缓存”。

## 测试建议

- 服务层单测：
  - 构造两个实例的多条 `InstanceSizeStat`；
  - 验证 `get_system_overview()` 取**最新记录**而非时间窗口；
  - 不受日期限制时总量正确。
- 回归确认：日志趋势图仍显示 7 天。

## 影响评估

- 对外接口不变，仅容量汇总口径变化。
- 依赖“实例容量采集/同步”是否及时更新；历史未采集的实例仍会被计入（最新记录可能较旧）。

