---
title: MetricCard 指标卡标准
aliases:
  - metric-card-standards
tags:
  - standards
  - standards/ui
status: active
enforcement: design
created: 2026-01-22
updated: 2026-01-22
owner: WhaleFall Team
scope: "`app/templates/**` 中所有顶部指标/统计卡片，以及其组件样式与 JS 更新方式"
related:
  - "[[standards/ui/gate/design-token-governance]]"
  - "[[standards/ui/gate/template-event-binding]]"
---

# MetricCard 指标卡标准

## 目的

- 统一全站“顶部指标/统计卡片”的结构与视觉基线，避免每个页面一套私有 `*-stat-card` 样式。
- 让 JS 更新指标值的定位方式稳定（`id` / `data-stat-key` / `[data-role="metric-value"]`），便于门禁与重构。

## 适用范围

- 任何“label + value + 可选 meta”形式的指标卡（仪表盘、容量统计、日志中心、运行中心、标签管理、调度器等）。

## 规则（MUST/SHOULD/MAY）

### 1) 模板结构（MUST）

- MUST：使用 `MetricCard` 组件（`app/templates/components/ui/metric_card.html`）或 `metric_card` macro。
- MUST：组件根节点包含 `wf-metric-card` 基准 class（用于统一样式与门禁）。
- MUST：指标值节点包含 `data-role="metric-value"`；若需要 JS 更新，MUST 同时具备稳定锚点：
  - Prefer：`id="xxx"`（页面唯一）。
  - 或：在卡片根节点设置 `data-stat-key="xxx"`（用于批量更新/列表型 stats）。

### 2) 视觉与 CSS（MUST/SHOULD）

- MUST：卡片视觉（border/shadow/padding/typography）只能由组件 CSS `app/static/css/components/metric-card.css` 定义。
- MUST NOT：在页面 CSS 中新增/恢复 `.xxx-stat-card { border/shadow/padding/... }` 这类视觉覆盖。
- SHOULD：页面 CSS 仅负责布局（`row/grid/gap`），例如 `.xxx-stats-row` / `.xxx-stats-grid`。

### 3) Tone 与状态色（SHOULD）

- SHOULD：使用 `data-tone="success|warning|danger|info|muted"` 控制数值颜色（由组件 CSS 映射到 `--status-* / --text-*`）。
- SHOULD：meta 区域使用现有 `status-pill` / `chip-outline`，避免引入新 badge 体系。

### 4) JS 更新方式（MUST）

- MUST：JS 更新指标值时，优先定位到卡片（`[data-stat-key="..."]`）再更新其内部 `[data-role="metric-value"]`，避免依赖页面私有 class（例如 `.tags-stat-card__value`）。
- MUST NOT：为更新值而引入新的“页面私有 value class”（例如 `.xxx-stat-card__value`）。

## 示例

### 基础用法（无 meta）

```html
{% from 'components/ui/macros.html' import metric_card %}

{{ metric_card('总日志数', value=0, value_id='totalLogs', icon_class='fas fa-list') }}
```

### 带 meta slot（推荐）

```html
{% from 'components/ui/macros.html' import metric_card %}

{% call metric_card('启用标签', value=stats.active, tone='success', data_stat_key='active') %}
  <span class="status-pill status-pill--success"><i class="fas fa-check-circle"></i>启用</span>
{% endcall %}
```

## 门禁/检查方式

- `pytest -m unit`（包含模板/JS 扫描测试）

