# 前后端数据一致性核查手册
**版本**：v0.1｜2025-11-29｜维护人：架构治理小组

> 适用范围：所有前端通过筛选/排序/聚合控制查询范围的业务场景（实例与容量、标签管理、账户/凭据列表、报表与仪表盘等），本文定义如何系统性验证“前端输入 = 后端输出”。

## 1. 核查目标
1. **参数对等**：确保前端请求携带的所有筛选参数（日期、标签、分页、排序、搜索关键词）在后端均有明确解析与持久化条件。
2. **语义一致**：前端展示的含义（如“近 7 天”、“季度累计”）与后端 SQL/聚合语义保持一致（包含/不包含边界、时区、单位）。
3. **数据一致**：同一视图在 UI 与 API/数据库层面抽样校验，允许的误差（例如舍入）有明确定义并落库。
4. **可追溯**：出现不一致时能定位到“前端构造请求 → API 层 → 服务/模型 → SQL”的具体断点。

## 2. 通用核查流程
| 步骤 | 动作 | 产出 |
|------|------|------|
| 1 | 在浏览器 DevTools → Network 捕获页面请求，记录 URL、Query、Body、时间范围、标签、分页参数 | `request_trace.json`（保存到 issue 附件） |
| 2 | 在 API 层（如 `app/routes/...`) 对应视图函数打点，确认 `request.args`/`request.get_json()` 中字段是否齐全，并记录 `request_id` | 访问日志（结构化 JSON） |
| 3 | 在服务层（如 `app/services/...`) 找到负责查询的函数，查明 ORM 条件（`filter`, `join`, `between` 等）与参数映射关系 | “参数→SQL 条件”表 |
| 4 | 使用 `psql`/`sqlite`/`pytest` fixture 重放相同参数，直接查询数据库校验记录数与样本行 | SQL/pytest 输出 |
| 5 | 将 API 响应与基线结果比对，允许差异需写明原因（聚合口径、舍入、缓存延迟） | 对账表/工单 |

## 3. 常见不一致来源与解决方式
1. **时区/日期边界**（例：容量页面）  
   - 后端大量使用 `time_utils.now_china()`（UTC+8）。若前端基于本地浏览器时区，需要在请求中携带 ISO 日期并统一转换。  
   - 检查点：`app/routes/capacity/instances.py` 在解析 `start_date` 时使用 `_parse_iso_date` 并对 `time_range` 参数做减法；确保 UI 侧计算方式一致，且说明“包含起止日”。
2. **标签/权限过滤**  
   - 多数列表（实例、凭据、容量）在查询前都会对标签做 `JOIN Tag` 或 `instance_tags` 过滤。例如 `app/routes/instances/manage.py` 在 300 行附近 `query.join(Instance.tags)`。需要确认前端勾选的标签集合能准确反映到 `Tag.name.in_(tags)` 条件，并在响应里同时返回 `selected_tags` 供 UI 校验。
3. **分页/排序**  
   - 统一约定 `page` 从 1 开始、`per_page` 最大 100。核查 `page * per_page` 大于记录总数时是否返回空列表。若 UI 使用无限滚动，注意缓存 Layer 是否遗漏 `offset`。
4. **聚合粒度**  
   - `app/services/aggregation/aggregation_service.py` 的日聚合使用 `use_current_period=True`，而 `weekly/monthly/quarterly` 默认上一周期。确保 Dashboard 提供的“近 7 天/上月/上季度”文案与真实取数一致；如需固定“上一完整周期”，不要调用 `aggregate_current_period`。
5. **缓存/异步**  
   - 账户自动分类、容量聚合等存在缓存或异步任务。核查时要注明数据快照时间，并确定 UI 是否展示“上次更新时间”。

## 4. 核查清单（按场景）
| 场景 | 前端行为 | 后端入口 | 关键字段 | 核查动作 |
|------|----------|----------|----------|----------|
| 实例容量趋势（近 N 天） | 日期组件选择 `time_range=7` | `app/routes/capacity/instances.py::list_instance_capacity` | `start_date`、`end_date`、`time_range` | 1）抓包确认请求参数；2）在 Flask 日志中检索同一 `request_id`；3）在 `InstanceSizeAggregation` 对应 `period_start` 执行 SQL，核对返回数组长度与 UI 折线点一致 |
| 数据库容量明细 | UI 选择实例 + 起始日期 | `app/routes/capacity/databases.py::list_databases_capacity` | `instance_id`、`start_date` | 1）比对响应 `totals` 汇总与 `SELECT SUM(size_mb)` 结果；2）确认过滤条件 `DatabaseSizeStat.collected_date >= start_date` 与 UI 文案一致（包含当天） |
| 标签管理列表 | 在 UI 勾选多个标签筛选实例 | `app/routes/instances/manage.py` | `tags[]=tag_a` | 1）抓包 `tags` 参数；2）确认 SQL 里 `Tag.name.in_(tags)`；3）抽样实例的 `instance.tags` 是否全包含所选标签 |
| 账户自动分类结果页 | 选择实例或全量执行 | `app/routes/accounts/classifications.py::auto_classify` | `instance_id` | 1）确认请求 Body；2）校验 `AutoClassifyService` 日志中 `normalized_instance_id`；3）对比 `AccountClassificationAssignment` 表中 `assigned_at` 在同一批次内 |
| Dashboard 趋势卡片 | 切换“季度”维度 | `app/routes/capacity/aggregations.py` | `period_type=quarterly` | 1）确认 API 是否调用 `get_current_period` 还是 `get_last_period`；2）如需“上一完整季度”，确保传参 `use_current_period=False` 或直接访问 `/tasks/capacity_aggregation_tasks.calculate_*` 导出的聚合表 |

> 建议按照以上表格为每个页面建立 Checklist，PR / 上线前至少跑一遍重点场景。

## 5. 自动化策略
1. **集成测试**：在 `tests/integration/` 下为关键 API 编写“前端视角”测试，用 `client.get` 模拟真实查询，并断言响应字段与直接 SQL 查询一致。举例：`pytest -k test_capacity_instance_filters`。
2. **对账脚本**：在 `scripts/` 新增 `verify_filters.py`（可参考 `scripts/refactor_naming.sh` 的结构），传入 API 路径与参数，脚本调用 API 与直接 SQL，对比 JSON 与查询结果。可纳入 `make quality`。
3. **结构化日志**：所有 API 必须记录 `requested_filters`（JSON），例如 `log_info("capacity_filter", module="capacity", request_id=..., filters=request.args.to_dict(flat=False))`，方便随后 grep。
4. **可视化探针**：对关键视图增加“数据快照”按钮，显示当前请求参数与服务器返回的 `period_start`、`period_end` 等信息，降低排查成本。
5. **CI 合规**：在 PR 模板新增“前后端数据一致性已核实”勾选项，要求开发附上抓包截图 + SQL 结果。

## 6. 常见问题与定位
- **症状：UI 选 2025-11-01，但 API 返回 2025-10-31 数据**  
  排查：1）确认浏览器时区；2）检查 `time_utils.parse_iso_date` 是否默认 UTC；3）确认数据库字段是否存储 UTC 并在 ORM 层转换。
- **症状：标签筛选结果包含未勾选标签的实例**  
  排查：1）看是否存在 `OR` 条件；2）检查是否 mix 了 `Tag.display_name` 与 `Tag.name`；3）确认 `JOIN` 是否导致重复并 unchecked `DISTINCT`。
- **症状：季度聚合不对**  
  排查：1）查看调用点是否使用 `aggregate_current_period`；2）打印 `start_date/end_date`；3）比对 `PeriodCalculator.get_last_period('quarterly')` 输出。

## 7. 推进计划
1. **两周内**：完成容量、实例、标签三个核心页面的一致性 Checklist，并沉淀到 `docs/architecture/`。
2. **一个月内**：为所有日期敏感 API 编写集成测试 & 对账脚本，集成至 `make quality`。
3. **持续**：上线任何新筛选功能前，必须附抓包、API 响应、SQL 三张截图或日志。

---
若巡检中发现新的不一致模式，请 PR 更新本手册并 @架构治理小组。
