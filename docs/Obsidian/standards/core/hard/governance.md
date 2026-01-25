---
title: Standards 治理与 enforcement 分级
aliases:
  - standards-governance
  - enforcement-levels
tags:
  - standards
  - standards/governance
status: active
enforcement: hard
created: 2026-01-25
updated: 2026-01-25
owner: WhaleFall Team
scope: "`docs/Obsidian/standards/**` 下所有标准文档的编写、分级与执行方式"
related:
  - "[[standards/README]]"
  - "[[standards/doc/guide/documentation]]"
---

# Standards 治理与 enforcement 分级

## 目的

- 把“标准/设计/指南/门禁”分开: 减少过度设计与过度约束导致的工程负担.
- 让 `MUST` 回到“高风险不变量”的位置: 避免把偏好/经验法则写成硬约束.
- 让能自动化的规则尽量自动化: 标准只描述原则与门禁入口, 由脚本守住底线.

## 适用范围

- `docs/Obsidian/standards/**` 下所有文档(含索引类 README).
- 本文只约束“标准如何写/如何执行”, 不替代具体业务/技术标准.

## enforcement 分级(必填字段)

所有 standards 文档的 YAML frontmatter MUST 包含 `enforcement` 字段, 且取值只能为:

- `hard`: 硬标准(高风险不变量/对外契约/安全与一致性)
- `gate`: 门禁标准(以 `scripts/ci/*-guard.sh` 等自动化门禁为主要执行方式)
- `guide`: 指南(建议/经验法则, 允许例外, 不做硬拦截)
- `design`: 设计(架构/模式/默认路径 + 取舍, 不应写成“必须这样做”)

> [!note]
> `enforcement` 表达“这份文档的执行强度与执行方式”, 不是“文档的重要性”.

## 规则(MUST/SHOULD/MAY)

### 1) `MUST` 的使用边界

- MUST: `hard` 文档才允许大量使用 `MUST/MUST NOT`.
- MUST: `gate` 文档中的 `MUST/MUST NOT` 必须能被门禁脚本检查(或能明确给出可执行的自查命令).
- SHOULD: `guide/design` 文档避免使用 `MUST`, 优先用 `SHOULD` 或“默认做法/推荐/例外”.
- MUST NOT: 把“主观偏好/审美/局部经验”写成 `MUST`(典型症状: 促使为满足标准而提前抽象/拆层/写模板代码).

### 2) 门禁优先

- SHOULD: 能自动化检查的规则优先落在 `scripts/ci/*-guard.sh`(或已有工具链), 文档只保留:
  - 规则的意图与风险解释(为什么需要)
  - 门禁入口(运行命令)
  - 常见修复方式
- MUST: `gate` 文档必须在“门禁/检查方式”章节列出对应脚本.
- MUST NOT: 在没有门禁且难以人工判定时, 把规则写成 `MUST`(会导致执行口径漂移).

### 3) 设计与标准分离

- SHOULD: 下列内容更适合写为 `design` 而不是 `hard/gate`:
  - 分层方案/目录组织/模块化策略
  - UI 交互模式与组件生态(例如 Grid/Modal CRUD 的默认方案)
  - 第三方库封装策略与升级策略
- MUST: `design` 文档需要包含“取舍/替代方案/何时例外”, 而不是“必须这样做”.

### 4) 减负优先(反过度设计)

- MUST: 标准的默认形态是“最小约束集”, 只覆盖:
  - 线上风险(安全/数据一致性/可观测性/对外契约)
  - 团队协作摩擦(命名/目录/错误口径)中最容易造成返工的部分
- SHOULD: 任何新标准在引入前写清:
  - 它要防止的具体事故/返工类型
  - 不遵守的真实成本
  - 如何门禁化/如何验证

## 正反例

### 正例: hard(契约/安全/一致性)

- `standards/backend/hard/error-message-schema-unification`: 防止 `error/message` 漂移, 下游不再写互兜底链.

### 正例: gate(自动化门禁)

- `standards/ui/gate/layout-sizing` + `./scripts/ci/inline-px-style-guard.sh`: 禁止新增 inline px 布局, 用 token/class 替代.

### 正例: design(默认方案 + 取舍)

- `standards/ui/gate/grid`: 属于“页面架构/生态”, 文档应更强调默认入口与插件化, 允许少量例外, 关键底线交给门禁脚本守.

### 反例: guide 写成 hard

- 把文本/格式偏好(例如标点/缩写/行数限制)写成大量 `MUST` 且无门禁, 会迫使代码与文档为满足形式而过度改造.

## 门禁/检查方式

- SHOULD: 后续新增一个轻量 lint(或脚本)检查:
  - standards 文档必须包含 `enforcement`
  - `enforcement=gate` 时必须包含至少一个 `scripts/ci/*-guard.sh` 引用

## 变更历史

- 2026-01-25: 初始化, 引入 enforcement 分级, 作为 standards 减负与治理入口.
