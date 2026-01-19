# services/dashboard + services/statistics + services/aggregation + routes/dashboard + templates/dashboard

## Core Purpose

- Dashboard：为仪表盘页面与 `/api/v1/dashboard/*` 提供 overview/status/charts 等只读聚合数据。
- Statistics：为 dashboard/charts 与统计页面提供“可复用的统计计算/查询封装”。
- Aggregation：后台/任务侧的周期聚合计算（daily/weekly/monthly/quarterly）与查询服务。
- routes/templates：仅做页面渲染与参数透传，不承载查询拼装。

## Unnecessary Complexity Found

- `app/services/dashboard/dashboard_activities_service.py:1-16`：空数组占位 Service（仅用于 API 返回 `[]`）。
  - 这是“为未来扩展预留接口”的典型 YAGNI；目前只会增加一个文件/类/依赖点。

- `app/api/v1/namespaces/dashboard.py:284-305`：`/activities` endpoint 通过 Service 取值，但当前恒定为空列表。
  - 可以直接在 endpoint 内返回 `[]`，不需要额外 service 层。

- `app/services/statistics/log_statistics_service.py:14-18, 85-88, 112-115`：
  - `LOG_STATISTICS_EXCEPTIONS` 使用 `BaseException` 类型元组 + `safe_exc` 冗余。
  - 实际捕获的异常均为 `Exception` 子类；可直接捕获并记录。

- `app/services/statistics/partition_statistics_service.py:51-67`：
  - `get_partition_statistics()` 完全是 `get_partition_info()` 的字段重复拷贝（仅键顺序不同）。

- `app/services/statistics/database_statistics_service.py:1-216`：
  - 当前仓库内无引用（`rg database_statistics_service` 无命中），属于“未被使用的统计服务”。
  - 其中还包含大量 `getattr/类型兜底` 的分页解析样板，若无调用点则属于纯负担。

## Code to Remove

- `app/services/dashboard/dashboard_activities_service.py:1-16`：删除占位 Service，改为 endpoint 内直接返回 `[]`（可删 LOC 估算：~16）。
- `app/services/statistics/log_statistics_service.py:14-18, 85-88, 112-115`：删除 `LOG_STATISTICS_EXCEPTIONS` 与 `safe_exc` 样板（可删 LOC 估算：~6-10）。
- `app/services/statistics/partition_statistics_service.py:51-67`：删除重复 dict 组装，直接返回 `get_partition_info()`（可删 LOC 估算：~10-15）。
- `app/services/statistics/database_statistics_service.py:1-216`：删除未引用模块（可删 LOC 估算：~216）。

## Simplification Recommendations

1. Dashboard activities：直接返回常量空列表
   - Current: 额外 Service 文件/类，仅返回 `[]`。
   - Proposed: 在 `/api/v1/dashboard/activities` 内直接 `activities: list[dict[str, object]] = []`。
   - Impact: 少一个 service 入口点、少一层抽象，行为不变。

2. Stats 异常处理：只保留必要异常捕获
   - Current: `BaseException` + `safe_exc` 防御样板。
   - Proposed: 直接 `except (SQLAlchemyError, ValueError, TypeError) as exc:` 并记录 `exc`。

3. Partition statistics：去掉“同结构 dict 重组”
   - Current: 复制一遍 dict 字段。
   - Proposed: 直接复用 `get_partition_info()` 的结果。

4. 删除未引用模块：优先删死代码再谈重构
   - Current: `database_statistics_service.py` 在仓库内无引用。
   - Proposed: 删除文件并依赖全量 unit test 验证无回归。

## YAGNI Violations

- `app/services/dashboard/dashboard_activities_service.py:1-16`：为“未来可能有活动流”预留服务层，但当前没有任何业务逻辑。
- `app/services/statistics/database_statistics_service.py:1-216`：无调用点仍保留完整服务模块。

## Final Assessment

- 可删 LOC 估算：~250+
- Complexity: Medium -> Low（dashboard/statistics 边缘抽象与死代码清理后）
- Recommended action: Proceed（先删占位与未引用模块；不触碰 aggregation 主流程以避免行为风险）。

