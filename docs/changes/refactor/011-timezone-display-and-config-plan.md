# Timezone Display and Configuration Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/static/js/common/time-utils.js`, `app/utils/time_utils.py`, `app/templates/history/**`, `app/static/js/modules/views/history/**`, `app/settings.py`, `docs/standards/ui/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P2-04)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** All timestamps displayed in the UI are timezone-explicit. Users can always answer "these times are shown in which timezone", and cross-timezone collaboration can align logs/sessions without guesswork.

**Architecture:** Introduce a single source of truth for "display timezone" and "timezone label" (backend settings -> template injection -> `timeUtils` -> UI badges/tooltips). Long-term, support per-user display timezone without changing backend timestamp storage.

**Tech Stack:** Flask templates, Day.js + timezone plugin, Python `zoneinfo`.

---

## 1. 动机与范围

### 1.1 动机

- 前端 `timeUtils` 固定将时间转换到 `Asia/Shanghai`, 且所有格式化输出不包含时区标识.
- 在跨地区协作或日志对齐场景, 用户容易把时间误解为本地时区, 导致对"何时触发/持续多久"产生错误判断.

证据:

- `app/static/js/common/time-utils.js` 内 `const TIMEZONE = "Asia/Shanghai";`.

### 1.2 范围

In-scope:

- 会话中心/日志中心/详情面板等时间密集页面: 明确展示时区标识.
- `timeUtils` 输出能力: 提供 timezone label/offset 信息, 支持统一格式化策略.
- 长期: 用户设置中允许切换"显示时区"(display timezone), 且全站生效.

Out-of-scope(本计划不优先做):

- 改变后端存储时间的方式(仍按既有约定存储, 优先保证显示一致性).
- 重写所有页面的时间渲染为同一个组件(允许渐进迁移).

---

## 2. 不变约束(行为/契约/性能门槛)

- 行为不变: 同一个 timestamp 在同一 display timezone 下应显示同一时刻, 只增加时区标识与可配置能力.
- 兼容性: 允许接口返回 ISO 字符串或历史格式字符串, 但必须逐步收敛到可解析且可定位的结构.
- 性能门槛: 不新增重型依赖, 不显著增加首屏脚本体积.

---

## 3. 目标体验口径(长期要达到的状态)

### 3.1 全局原则

- MUST: UI 必须显式标注时区, 不允许"靠用户猜".
- SHOULD: 相对时间(例如 "3 分钟前")可继续使用, 但应提供绝对时间 + 时区的对照入口(tooltip/详情).
- MUST: 同一个 timestamp 在不同页面显示一致(格式与时区口径一致).

### 3.2 推荐展示形式

推荐在页面级别展示一次, 避免每行重复:

- 页面 header 或列表卡片 header 增加一个 chip: `UTC+08:00 Asia/Shanghai`.
- 对于详情面板: 在时间字段旁显示同一时区标识, 或在面板顶部显示统一的 timezone chip.

---

## 4. 方案选项(2-3 个)与推荐

### Option A: 仅增加 UI 时区标识(保持固定 Asia/Shanghai)

做法:

- 在会话中心/日志中心/详情面板增加 timezone chip, 文案例如 `UTC+08:00 Asia/Shanghai`.
- `timeUtils` 仍固定 `Asia/Shanghai`, 仅补齐 label 输出函数.

优点:

- 改动面小, 风险低, 立即降低误读风险.

缺点:

- 仍无法满足跨时区用户的个性化显示需求(比如希望显示 UTC 或本地时区).

### Option B: 引入 display timezone 配置(默认 Asia/Shanghai), 支持用户切换(长期)

做法:

- 将 display timezone 从前端 hardcode 改为配置驱动.
- 后端提供默认 timezone, 前端可基于用户偏好覆盖(例如 localStorage/用户设置).

优点:

- 兼顾默认口径与跨地区协作需求.

缺点:

- 需要更明确的配置来源优先级与回归验证(防止不同页面显示不一致).

### Option C(推荐): "时间展示规范" + 单一真源 + 渐进迁移

做法:

- 先建立标准与单一真源(配置 + timeUtils 输出 + UI 入口), 再逐页迁移.
- 标准覆盖: 格式, 时区标注, 相对/绝对时间切换, tooltip 口径.

优点:

- 长期可治理, 可避免口径漂移.

缺点:

- 需要分阶段推进, 不适合一次性大改.

推荐结论:

- 以 Option C 为总路线, Phase 1 先落地 Option A 的最小可用, 再推进 Option B 的配置与用户切换.

---

## 5. 分阶段计划(长期路线图)

### Phase 1: Single source of truth + time zone badge(基础能力)

验收口径:

- 会话中心/日志中心/详情面板可见明确 timezone 标识.
- `timeUtils` 提供 `getDisplayTimezone()` 与 `getTimezoneLabel()`(或等价 API), 且 label 与实际转换时区一致.

建议实现要点:

- 后端新增设置项(示例命名):
  - `APP_DISPLAY_TIMEZONE`(default: `Asia/Shanghai`)
  - `APP_DISPLAY_TIMEZONE_LABEL`(default: `UTC+08:00 Asia/Shanghai`, 或由后端计算 offset)
- 在 `base.html` 注入到前端:
  - `<meta name="app-display-timezone" content="...">`
  - 或 `window.APP_DISPLAY_TIMEZONE = "...";`
- `timeUtils` 从注入配置读取 timezone, fallback 到 `Asia/Shanghai`, 避免 hardcode 分散.

### Phase 2: 用户设置支持切换 display timezone

验收口径:

- 用户可在设置中切换显示时区(至少: `Asia/Shanghai`, `UTC`, `browser local`).
- 切换后全站生效且显示一致, 且 UI 总是显示当前 timezone label.

建议实现要点:

- 配置优先级(建议):
  1) 用户设置(持久化, server-side)或 localStorage
  2) 后端默认设置
  3) fallback: `Asia/Shanghai`
- 为避免歧义: 切换只影响显示, 不改变后端记录与 API timestamp.

### Phase 3: 形成 UI 标准 + 回归策略

验收口径:

- 有一份 UI 标准文档定义时间展示口径(格式, 时区标识, 相对/绝对切换).
- 新增页面在 code review/门禁中不会再出现"时间无时区标识"的回归.

建议实现要点:

- 新增标准文档: `docs/standards/ui/time-display-guidelines.md`.
- 标准应明确:
  - MUST: time zone badge 出现的位置与格式
  - SHOULD: 相对时间的 tooltip 口径(绝对时间 + timezone)
  - MUST: 列表与详情的格式一致

---

## 6. 风险与回滚

风险:

- 前端解析历史时间字符串时可能隐含本地时区语义, 一旦切换 display timezone 可能暴露存量数据不规范.
- 部分接口可能返回不带 offset 的字符串, 需要后端逐步收敛到 ISO8601(含 offset).

回滚:

- Phase 1 可先只增加 timezone badge(不引入用户切换), 保证风险可控.
- 如果用户切换引发误解, 可暂时下线切换入口, 但必须保留 timezone 显示标识.

---

## 7. 验证与验收

手工验证(最低覆盖):

- 会话中心列表与详情: 同一时间字段显示包含 timezone label.
- 日志中心列表与详情: 同一时间字段显示包含 timezone label.
- 人为切换系统时区(模拟跨时区): UI 仍明确显示当前 display timezone, 且时间展示不依赖用户猜测.

---

## 8. Open Questions(需要确认)

1. 默认 display timezone 是否必须固定 `Asia/Shanghai`, 还是应默认 "browser local" 并在 UI 标注?
2. timezone label 形式希望用 `UTC+08:00` 还是 `UTC+8`(两者都可以, 但必须全站一致).
3. 用户设置存储形态: localStorage(前端) vs 用户表字段(后端)优先?
