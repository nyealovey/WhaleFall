# DatabaseAggregationRunner 单实例周期聚合增强方案

## 执行摘要

### 当前状况
- `DatabaseAggregationRunner` 已具备批量周期聚合能力（所有激活实例），并提供 `aggregate_daily_for_instance()` 处理单实例当日的数据库级聚合。
- `DatabaseSizeAggregationService` 中的 `calculate_weekly/monthly/quarterly_aggregations_for_instance()` 返回的是实例级聚合结果（写入 `instance_size_aggregations`），符合其命名含义。
- 现有接口缺少“按实例获取数据库级周/月/季聚合”能力，只能依赖批量任务或实例级聚合数据满足业务。

### 核心问题
1. ❌ 无法以数据库粒度返回单实例的周/月/季聚合数据，功能空缺。
2. ❌ 若直接重用实例级接口，会混淆调用方期望的统计维度，破坏定时任务与手动聚合 API。
3. ⚠️ `aggregate_daily_for_instance()` 被多个路径复用（例如 `calculate_daily_database_aggregations_for_instance`），贸然删除会造成运行时异常。

### 目标
1. ✅ 为 `DatabaseAggregationRunner` 增加通用的单实例周期聚合能力。
2. ✅ 为服务层补充一组**数据库级**接口，同时保留现有实例级接口，确保兼容。
3. ✅ 在路由、任务与测试层面逐步接入新能力，保证功能验证与平滑迁移。

---

## 1. 背景与角色划分

| 组件 | 主要职责 | 现有能力 |
|------|----------|---------|
| `DatabaseAggregationRunner` | 以数据库为粒度，处理 `database_size_stats` 表并写入 `database_size_aggregations` | 批量周期聚合、单实例当日聚合 |
| `InstanceAggregationRunner` | 以实例为粒度，处理 `instance_size_stats` 表并写入 `instance_size_aggregations` | 批量周期聚合、单实例周期聚合 |
| `DatabaseSizeAggregationService` | 编排两种 Runner，提供对外 API | 区分实例级与数据库级接口，但缺少“数据库级单实例周/月/季”方法 |
| 定时任务与手动聚合 API | 依赖服务层接口返回既定结构 | 当前所有“instance”接口均返回实例级统计 |

**结论**：Runner 分工明确，问题不在于接口错误使用，而是“缺少数据库级单实例多周期能力”。

---

## 2. 问题陈述

1. **功能缺口**  
   - 需求：按实例查看数据库维度的 weekly / monthly / quarterly 汇总。  
   - 现实：只能通过批量周期任务或实例级汇总获取数据，无法及时返回数据库维度的聚合结果。

2. **错误的重构方向风险**  
   - 若替换或删除 `calculate_*_aggregations_for_instance()` 现有逻辑，等同改变了实例级聚合的行为。  
   - 调度任务 `_run_period_aggregation()` 和 `/api/manual_aggregate` API 依赖这些实例级接口，修改将导致数据写入错误的表或返回结构变化。

3. **兼容性隐患**  
   - `aggregate_daily_for_instance()` 被即时聚合任务复用（例如同步完成后更新单实例数据库汇总）。  
   - 直接删除或替换，不但影响调用方，还会破坏已存在的业务流程。

---

## 3. 方案概览

### 3.1 Runner 层
- 新增 `aggregate_database_period()`（命名可根据团队惯例微调），支持 `daily/weekly/monthly/quarterly`，内部沿用现有查询与写入逻辑。
- 保留 `aggregate_daily_for_instance()`，改为调用新方法后返回结果，并标注为兼容用途，方便后续平滑迁移。

### 3.2 服务层
- 新增数据库级接口：  
  `calculate_weekly_database_aggregations_for_instance()`、`calculate_monthly_database_aggregations_for_instance()`、`calculate_quarterly_database_aggregations_for_instance()`。  
  这组方法直接调用 runner 新增的 `aggregate_database_period()`。
- 保留既有实例级方法 `calculate_*_aggregations_for_instance()`，确保任务与 API 行为不变。  
  若需要数据库维度数据，可在调用层显式使用新增方法或开放新的 API。

### 3.3 调用层
- **容量统计前端**：  
  - “容量统计（实例）”页面在触发“统计当前周期”操作（调用 `aggregate_current` 相关 API）时，固定传入 `scope="instance"`，沿用实例级当前周期汇总结构。  
  - “容量统计（数据库）”页面的“统计当前周期”操作调用同一 API，并传入 `scope="database"`，返回数据库级单实例当前周期聚合数据。
- **手动聚合 API**：  
  - 保持现有参数与返回结构，新增 `scope` 参数并默认 `instance`。  
  - `scope="database"` 时调用新增的数据库级接口；其余值沿用实例级逻辑。  
  - 返回体中增加 `scope` 字段，帮助调用方识别数据维度。
- **定时任务**：  
  - 定时任务仍然针对“上一周期”进行聚合（例如周任务处理上周数据、月任务处理上月数据），不引入数据库级单实例聚合任务。  
  - 在批量调度中按顺序执行实例级与数据库级批量聚合接口，确保数据产出节奏稳定。

### 3.4 测试与监控
- 为 Runner 与 Service 新增单元测试覆盖：空数据、单库、多库、跨天等场景。
- 集成测试验证新旧接口的共存逻辑，确保返回结构与落库表正确。
- 在上线前后比对同一实例在新旧路径下的聚合结果，确认数据一致性。

---

## 4. 详细设计

### 4.1 `DatabaseAggregationRunner` 调整

```python
def aggregate_database_period(
    self,
    instance: Instance,
    *,
    period_type: str,
    start_date: date,
    end_date: date,
) -> InstanceSummary:
    """为指定实例聚合数据库级周期统计"""
    ...

def aggregate_daily_for_instance(self, instance: Instance, target_date: date) -> InstanceSummary:
    """兼容旧调用，内部复用 aggregate_database_period()"""
    return self.aggregate_database_period(
        instance,
        period_type="daily",
        start_date=target_date,
        end_date=target_date,
    )
```

实现要点：
- 调用 `_query_database_stats` 与 `_persist_database_aggregation`，逻辑与批量模式一致。
- 在 `InstanceSummary.extra` 中输出周期信息，保持返回体验。
- 继续通过 `_ensure_partition_for_date` 与 `_commit_with_partition_retry` 保障分区。

### 4.2 `DatabaseSizeAggregationService` 新接口

```python
def calculate_weekly_database_aggregations_for_instance(self, instance_id: int) -> dict[str, Any]:
    instance = self._get_active_instance(instance_id)
    start_date, end_date = self.period_calculator.get_last_period("weekly")
    summary = self.database_runner.aggregate_database_period(
        instance,
        period_type="weekly",
        start_date=start_date,
        end_date=end_date,
    )
    return summary.to_dict()
```

- 复用 `calculate_daily_database_aggregations_for_instance()` 的校验与日志模式。
- 提供统一的实例获取助手 `_get_active_instance()`，减少重复代码。
- 根据业务需求，决定是否对非激活实例直接跳过或返回特定状态。

### 4.3 API 与任务扩展建议

1. **手动聚合**  
   - 增加 `scope` 参数；默认 `instance`（保持现状），当 `scope=="database"` 时调用新接口。  
   - 返回内容中加入 `scope` 字段，帮助调用方区分数据来源。
2. **定时任务**  
   - 若需要数据库级单实例聚合，可仿照现有 `_run_period_aggregation()`，增加新的调度入口或配置开关。  
   - 建议先在灰度环境中开启以评估运行时间变化。
3. **监控/观察**  
   - 为新接口打点日志（实例 ID、周期、处理的数据库数量），并在 APM 中建立仪表板观察执行情况。

---

## 5. 实施步骤（建议顺序）

1. **Runner 增强**  
   - 实现 `aggregate_database_period()`，调整 `aggregate_daily_for_instance()` 调用路径。  
   - 新增单元测试覆盖多周期场景。
2. **服务层扩展**  
   - 抽取 `_get_active_instance()` 等通用逻辑。  
   - 新增数据库级接口，撰写测试验证返回结构与数据库写入。
3. **API/任务演进**  
   - 在手动聚合 API 中接入 `scope` 参数，更新路由与序列化层测试。  
   - 协调“容量统计（实例/数据库）”页面按上述约定传参，并验证 UI 展示。  
   - 调整定时任务执行流程，确保实例级与数据库级批量聚合按顺序执行，新增日志验证顺序。
4. **验证与回归**  
   - 运行 `make test`、`make quality`。  
   - 手动比对目标实例在新旧接口下的聚合结果。  
   - 收集性能指标与日志，评估执行耗时。
5. **文档与培训**  
   - 更新 API 文档与内部 Wiki。  
   - 向运行团队说明新增接口的使用方式与监控手段。

整体预估工时：**8 小时**（含测试与文档），根据业务范围可拆分为多个小需求逐步交付。

---

## 6. 测试计划

- **单元测试**  
  - Runner：覆盖无数据、部分数据库缺数据、跨周期等场景，验证写入记录数量与字段值。  
  - Service：模拟实例不存在、未激活、正常返回等路径。
- **集成测试**  
  - 在测试数据库中预置 `database_size_stats` 数据，调用新接口验证 `database_size_aggregations` 中的写入结果。  
  - 校验 API 层新增参数的返回结构与错误处理。
- **性能测试**  
  - 选取包含多个数据库的实例，比较新老实现的执行时间。  
  - 观察数据库写入量与锁等待，确保峰值时资源可控。
- **回归测试**  
  - 运行现有的实例级周期聚合任务与 API，确认未受影响。

---

## 7. 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 数据聚合逻辑错误 | 高 | 中 | 新增单元与集成测试，灰度验证数据一致性 |
| API 行为变更导致调用失败 | 中 | 低 | 新旧接口并存、参数向后兼容、发布前通知使用方 |
| 执行耗时上升 | 中 | 中 | 增加监控、必要时限制实例/数据库数量或拆批执行 |
| 数据量激增导致分区不足 | 中 | 低 | 保留分区保障逻辑，上线前确认分区策略 |

---

## 8. 回滚策略

1. **代码回滚**  
   - 单独合并 Runner 与服务层改动，必要时通过 `git revert` 回退对应提交。  
   - 新增接口采用“增量”方式实现，不影响旧接口可用性。
2. **数据回滚**  
   - 若新接口生成异常数据，可通过周期范围删除 `database_size_aggregations` 对应记录。  
   - 重新运行既有批量聚合任务恢复数据。

---

## 9. 后续展望

- 在客户端或报表系统中引入数据库级周期视图，提升容量分析的精度。  
- 评估是否需要更细粒度的指标（如日志空间、增长趋势），借助同一通用方法快速扩展。  
- 若后续确认无调用方依赖 `aggregate_daily_for_instance()`，可在充分迁移后进行弃用流程（标注 deprecation → 统计调用量 → 删除）。

---

**文档版本**: 3.0  
**创建日期**: 2024-10-31  
**最后更新**: 2024-11-02  
**作者**: Kiro AI Assistant（更新：Codex）  
**审核状态**: 待审核
