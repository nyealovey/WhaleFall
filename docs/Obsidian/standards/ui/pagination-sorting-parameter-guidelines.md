---
title: 分页与排序参数规范
aliases:
  - pagination-sorting-parameter-guidelines
tags:
  - standards
  - standards/ui
status: active
created: 2025-12-23
updated: 2026-01-08
owner: WhaleFall Team
scope: 所有列表页(GridWrapper)与后端列表 API(query params 与返回结构)
related:
  - "[[standards/backend/layer/api-layer-standards#API 命名与路径规范(REST Resource Naming)]]"
---

# 分页与排序参数规范

## 目的

- 列表页 URL 可分享且行为稳定：刷新/复制链接后分页大小不漂移。
- 前后端对分页字段达成单一约定，减少契约漂移与兼容分支。
- 逐步淘汰历史字段，同时保留可观测性（结构化日志）便于清理。

## 适用范围

- 前端：`app/static/js/common/grid-wrapper.js` 及所有列表页脚本。
- 后端：所有“列表接口”（支持分页/排序/筛选）。

## 规则（MUST/SHOULD/MAY）

### 1) 分页参数（统一）

- MUST：统一使用 `page`（从 1 开始）与 `limit`（每页数量）。
- SHOULD：`limit` 建议范围 `1~200`（具体上限以接口实现为准，后端需要做裁剪保护）。

### 2) 禁止旧字段

> [!warning]
> 不考虑兼容：`page_size` 不再作为分页大小参数解析。

- MUST NOT：前端请求与可分享 URL 禁止使用 `page_size`。
- MUST：服务端与 GridWrapper 仅使用 `limit` 作为分页大小参数。

### 3) 后端落点（强约束）

- MUST：列表接口统一通过 `app/utils/pagination_utils.py` 解析分页参数：
  - `resolve_page(...)`
  - `resolve_page_size(...)`
- SHOULD：当请求使用旧字段时记录结构化日志（`module/action`），便于统计与清理。

## 正反例

### 正例：只使用统一参数

- 仅使用 `page/limit`。

### 反例：新代码继续输出旧字段

- GridWrapper 或页面脚本继续发送 `page_size`，导致分页大小参数被忽略或行为异常。

## 门禁/检查方式

- 脚本：`./scripts/ci/pagination-param-guard.sh`
- 规则：GridWrapper 分页请求必须使用 `limit`，禁止回退为 `page_size`

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 补齐标准结构与门禁说明，统一“兼容字段”的边界与顺序。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
