# Account Classification Statistics Page Refactor Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.
>
> Status: Draft  
> Owner: WhaleFall FE  
> Created: 2026-01-22  
> Updated: 2026-01-22  
> Scope: 账户分类统计页面(`/accounts/statistics/classifications`)的筛选栏布局, 默认趋势展示, 规则列表口径, 图表样式统一.  
> Related:
> - docs/Obsidian/standards/ui/color-guidelines.md (FilterCard 栅格约束)
> - docs/Obsidian/standards/ui/layout-sizing-guidelines.md (chart-stage height tier)
> - app/templates/capacity/instances.html (容量统计趋势图 UI 参考)
> - app/static/js/modules/views/components/charts/chart-renderer.js (Chart.js options 参考)
> - app/static/css/components/charts.css (chart-stage/chart-canvas)

**Goal:** 彻底重构"账户分类统计"页面, 解决筛选栏不符合标准, 未选分类时趋势空白, 规则列表口径误导, 图表样式不统一等问题, 并对齐"容量统计趋势图"的图表体验.

**Architecture:** 前端以"FilterCard 标准栅格 + 多态趋势图(单分类/全分类) + 规则列表口径调整 + Chart.js 样式抽象"为主线, 后端补齐"全分类趋势"查询与"规则列表最新周期值"字段, 保持现有单分类/单规则趋势接口兼容.

**Tech Stack:** Flask(Jinja2), Chart.js, Vanilla JS, SQLAlchemy.

**Decisions (confirmed):**
- 规则列表主数值: 最新周期"均值"(weekly/monthly/quarterly), daily 为最新一天整数值.
- 未选分类时的"全分类趋势": 继续受 `period_type`/`db_type`/`instance_id` 筛选影响.

---

## 1. 问题与现状(As-is)

### 1.1 筛选栏宽度不符合 FilterCard 标准

- 现状: `app/templates/accounts/classification_statistics.html` 中, "账户分类"使用 `col-md-4`, "数据库类型"使用 `col-md-3`, 明显违反 `docs/Obsidian/standards/ui/color-guidelines.md` 的 FilterCard 约束(所有筛选控件必须 `col-md-2 col-12`).
- 影响: 组件视觉不一致, 首屏信息密度偏低, 筛选栏易换行且对齐混乱.

### 1.2 未选分类时, 分类趋势为空

- 现状: `app/static/js/modules/views/accounts/classification_statistics.js` 在 `!state.classificationId` 时直接 `renderEmptyState()` 并销毁图表.
- 期望: 未选择分类时, "分类趋势"应展示"所有分类"的趋势, 有几个分类就有几条线.

### 1.3 规则列表展示窗口累计, 易被误解

- 现状: 左侧规则列表展示 `window_value_sum`(窗口累计命中), 右上角标签展示 `window_start ~ window_end`, 容易被理解为"最新命中"或"当前周期命中".
- 期望: 列表主数值展示"最后一次命中数"(最新周期/最新统计点), 而不是窗口累计. (可选: 以 tooltip/次级信息保留窗口累计, 方便排查.)

### 1.4 图表样式与容量统计趋势图不一致

- 现状: 本页面自行 build Chart.js config, 与容量统计的 `CapacityStatsChartRenderer` 在 legend, tooltip, grid, axis title, no-data 占位等方面不一致.
- 期望: 尽量对齐容量统计趋势图的视觉与交互(配色来源, legend 行为, tooltip 风格, 网格线与 0 线强调, chart-stage 高度 tier).

---

## 2. 重构目标 / 非目标

### 2.1 目标(To-be)

- FilterCard 栅格对齐标准: 所有筛选控件采用 `col-md-2 col-12`.
- 分类可选:
  - 未选分类: 上图展示"所有分类"趋势(多条折线).
  - 已选分类: 上图展示该分类趋势(单条折线).
- 规则列表口径调整: 默认展示"最新周期命中"(最后一次命中数), 替代窗口累计.
- 图表样式统一: 参考容量统计趋势图, 统一 Chart.js options, 使用 `chart-stage`/`chart-canvas` 组件 class, 并提供 no-data 占位.

### 2.2 非目标(Out of scope, 本次不做)

- 不新增"最近 N 个周期"切换(7/14/30)控件(当前页面默认 7, 后续如需再单独开需求).
- 不重做双栏整体布局结构(继续沿用"左规则列表 + 右图表区"信息架构, 仅调整必要的对齐与样式统一).
- 不调整统计口径(分类去重, 规则命中, 周/月/季按均值展示)与后端数据写入逻辑(仅优化读接口与展示).

---

## 3. 方案设计(To-be)

## 3.1 FilterCard(筛选栏)

### 交互规则

- "账户分类"改为可选, placeholder 改为"全部分类".
- "实例"仍受 "数据库类型"联动: 未选 `db_type` 时 disabled, 并显示同样的 helper text.
- 刷新规则:
  - classification 为空: 仅刷新上图(分类趋势), 左栏规则列表与下图保持空状态.
  - classification 有值: 刷新规则列表 + 上下图(现有行为).

### 布局规则

- 所有筛选控件使用 `col-md-2 col-12`.
- 页面模板禁止通过扩大列宽来"偷空间", 需要通过 option 文案优化(例如显示 `display_name`, 将 `code`放到 tooltip 或 option 的次级信息)解决可读性.

---

## 3.2 分类趋势图(上图)

### 展示逻辑

- 已选分类: 单序列折线图.
- 未选分类: 多序列折线图:
  - dataset 数量 = 分类数量(包含无数据分类, 值为 0).
  - legend 置于右侧, 支持点击 legend 隐藏/显示某条线(Chart.js 默认行为).
  - tooltip 使用 `mode: "index"` 以便同一时间点对比多个分类.

### 数据与接口

为避免前端 N 次请求(分类数次)带来的性能风险, 建议新增单次批量接口.

- 新增 API(建议, plural):
  - `GET /api/v1/accounts/statistics/classifications/trends`
  - query:
    - `period_type`: `daily|weekly|monthly|quarterly`(沿用现有约束, yearly 继续不支持)
    - `periods`: 默认 7
    - `db_type`: optional
    - `instance_id`: optional
  - response(建议结构):
    ```json
    {
      "period_type": "daily",
      "periods": 7,
      "buckets": [
        {
          "period_start": "2026-01-16",
          "period_end": "2026-01-16",
          "expected_days": 1
        }
      ],
      "series": [
        {
          "classification_id": 1,
          "classification_name": "管理员",
          "points": [
            {
              "period_start": "2026-01-16",
              "period_end": "2026-01-16",
              "value_avg": 12,
              "value_sum": 12,
              "coverage_days": 1,
              "expected_days": 1
            }
          ]
        }
      ]
    }
    ```
- 兼容策略:
  - 保留现有 `GET /api/v1/accounts/statistics/classifications/trend`(单分类)不变.
  - 前端逻辑:
    - classification 为空 -> 调用 `.../classifications/trends`.
    - classification 有值 -> 继续调用 `.../classifications/trend`.

---

## 3.3 规则列表(左栏)

### 展示口径

- 列表主数值展示"最新周期命中"(最后一次命中数), 即当前 `period_type` 下"最后一个统计点"的值:
  - `daily`: 最新一天命中账号数(整数).
  - `weekly/monthly/quarterly`: 最新周期命中均值(按现有页面口径, 1 位小数), 同时建议返回累计与覆盖用于 tooltip.
- header 的范围标签显示"最新周期范围"(而不是窗口范围):
  - `daily`: `YYYY-MM-DD`
  - `weekly/monthly/quarterly`: `YYYY-MM-DD ~ YYYY-MM-DD`

### 排序口径

- 默认按"最新周期命中"降序排序, 保持"显示什么, 就按什么排序".
- 状态筛选逻辑保持: `active|archived|all`.

### 后端字段建议

修改 `GET /api/v1/accounts/statistics/rules/overview` 返回结构, 在保留现有字段的前提下, 新增 latest 相关字段:

```json
{
  "window_start": "2026-01-16",
  "window_end": "2026-01-22",
  "latest_period_start": "2026-01-22",
  "latest_period_end": "2026-01-22",
  "latest_coverage_days": 1,
  "latest_expected_days": 1,
  "rules": [
    {
      "rule_id": 1,
      "rule_name": "mysql_super_rule",
      "db_type": "mysql",
      "rule_version": 2,
      "is_active": true,
      "latest_value_avg": 120,
      "latest_value_sum": 120,
      "window_value_sum": 1170
    }
  ]
}
```

说明:
- `latest_value_avg` 是 UI 的主展示值.
- `latest_value_sum/window_value_sum` 主要用于 tooltip/排查, UI 可选择隐藏.

---

## 3.4 下图(规则贡献/规则趋势)

- 行为保持:
  - 选中规则: 下图展示规则趋势.
  - 未选规则: 下图展示规则贡献(当前周期 TopN).
- 本次只做图表样式统一与文案对齐, 不改动现有接口与口径.

---

## 3.5 图表样式统一(对齐容量统计趋势图)

### CSS 统一

- 移除页面私有的固定高度 `.acs-chart-stage { height: 320px; }`.
- 统一改为组件 class:
  - 上图: `.chart-stage chart-stage--md` + `canvas.chart-canvas`
  - 下图: `.chart-stage chart-stage--md`(或根据实际密度改为 `--sm`) + `canvas.chart-canvas`
- 参考: `app/static/css/components/charts.css`.

### JS 统一

建议抽出可复用的 Chart.js config builder, 复用容量统计的 options 风格:

- 配色来源统一使用 `window.ColorTokens`:
  - 单序列: `ColorTokens.getChartColor(0, ...)`
  - 多序列: `ColorTokens.getChartColor(seriesIndex, ...)`
- tooltip 与 interaction:
  - `interaction.mode = "nearest"` or `"index"`(多序列时优先 `"index"`)
  - `tooltip.mode = "index"`, `intersect = false`
- grid 风格:
  - 使用 `ColorTokens.withAlpha(--surface-contrast, 0.08)` 作为 grid base.
  - 强调 0 线(如存在 0 轴场景)的颜色与线宽, 对齐 `chart-renderer.js` 的做法.
- axis title:
  - x: "时间"
  - y: "账号数"(或更具体: "去重账号数"/"命中账号数")
- no-data 占位:
  - 对齐 `CapacityStatsChartRenderer.renderEmptyChart`, 避免销毁图表导致空白.

---

## 4. 后端改动清单

### 4.1 新增 "全分类趋势"查询

**Files:**
- Modify: `app/api/v1/namespaces/accounts.py`
- Modify: `app/services/accounts/account_classification_daily_stats_read_service.py`
- Modify: `app/repositories/account_classification_daily_stats_read_repository.py`

**Implementation notes:**
- Repository 新增 `fetch_all_classifications_daily_totals(start_date, end_date, db_type, instance_id)`:
  - Query: group by `(classification_id, stat_date)` and sum `matched_accounts_distinct_count`.
  - Return shape: `dict[int, dict[date, int]]` 或扁平 `dict[tuple[int, date], int]`(上层再组装).
- Service 新增 `get_all_classifications_trends(period_type, periods, db_type, instance_id)`:
  - 复用 `_build_period_buckets` + `_rollup_to_buckets`.
  - 需要按 `AccountClassification.priority desc` 返回 series 顺序, 避免 legend 顺序漂移.

### 4.2 规则列表 overview 返回 latest 字段

**Files:**
- Modify: `app/services/accounts/account_classification_daily_stats_read_service.py`
- Modify: `app/repositories/account_classification_daily_stats_read_repository.py`(如需新增查询)

**Implementation notes:**
- 计算 latest period:
  - 使用 `PeriodCalculator.get_current_period(period_type)` 得到 `latest_period_start/latest_period_end`.
- 获取 latest totals:
  - 复用现有 `fetch_rule_totals_by_rule_id` 查询 latest 区间.
  - 同时用 `fetch_rule_stat_dates` 计算 `latest_coverage_days`.
- `latest_value_avg` 计算规则:
  - `daily`: `int(latest_value_sum)`
  - 其他: `round(latest_value_sum / latest_coverage_days, 1)`(coverage=0 时为 0.0)
- 默认排序改为按 `latest_value_avg`(或 `latest_value_sum`) desc.

---

## 5. 前端改动清单

### 5.1 Template/CSS

**Files:**
- Modify: `app/templates/accounts/classification_statistics.html`
- Modify: `app/static/css/pages/accounts/classification_statistics.css`

**Changes:**
- FilterCard 内所有筛选控件改为 `col-md-2 col-12`.
- "账户分类"取消 `required`.
- Chart stage 统一改为 `chart-stage chart-stage--md` + `chart-canvas`.
- 删除/收敛页面私有的 chart 高度与重复样式, 优先复用组件 CSS.

### 5.2 JS 行为与图表渲染

**Files:**
- Modify: `app/static/js/modules/services/account_classification_statistics_service.js`
- Modify: `app/static/js/modules/views/accounts/classification_statistics.js`

**Changes:**
- Service 增加 `fetchAllClassificationsTrends(...)` 方法, 指向新 API.
- 未选 classification:
  - 仅加载上图 multi-series trend.
  - 左栏与下图显示空状态文案, 并避免发起 rules/secondary 的请求.
- rules overview:
  - 使用 `latest_value_avg` 作为展示值.
  - header 显示 `latest_period_start ~ latest_period_end`(或单日).
- chart config:
  - 抽取统一的 `buildChartOptions`(参考 `CapacityStatsChartRenderer.buildOptions`).
  - 多序列时开启 legend, 单序列可隐藏 legend.
  - no-data 时渲染占位图.

---

## 6. 验收标准(Definition of Done)

- FilterCard 栅格符合标准: 所有筛选控件均为 `col-md-2 col-12`, 且不通过扩大列宽规避.
- 未选分类时:
  - 上图展示所有分类趋势(多条线), legend 可交互.
  - 左栏规则列表与下图不加载分类相关数据, 显示引导文案.
- 已选分类时:
  - 行为与现有一致(规则列表 + 分类趋势 + 规则贡献/趋势), 且图表样式统一.
- 规则列表:
  - 主数值展示最新周期命中(最后一次命中数), 不再展示窗口累计.
  - header 显示最新周期日期/日期范围.
- 图表样式:
  - 使用 `chart-stage`/`chart-canvas`, 与容量统计趋势图的 grid/tooltip/legend 风格一致.
  - no-data 时有明确占位, 不出现"空白 canvas".

---

## 7. 风险与兼容性

- API 兼容: 新增 plural API, 保留现有单分类 trend API, 降低对已有调用方的影响.
- 视觉噪声: 分类数较多时, 多序列趋势图会变得拥挤. 本需求明确"有几个分类就有几条线", 因此不做自动裁剪, 但依赖 legend 交互缓解.
- 性能: 必须避免前端 N 次请求, 否则分类数增长时会明显变慢. 该风险通过新增批量 API 化解.
