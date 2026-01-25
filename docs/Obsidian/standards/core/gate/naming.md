---
title: 命名规范
aliases:
  - naming-standards
tags:
  - standards
  - standards/general
status: active
enforcement: gate
created: 2025-12-25
updated: 2026-01-25
owner: WhaleFall Team
scope: 仓库内所有文件/目录/符号命名(Python/Jinja2/JS/CSS/脚本)
related:
  - "[[standards/README]]"
  - "[[standards/core/guide/coding]]"
  - "[[standards/core/hard/governance]]"
---

# 命名规范

## 目的

- 降低“同一概念多种命名”的漂移成本，减少重构与搜索负担。
- 保证自动化命名巡检脚本可持续生效，避免出现不可控的历史残留前缀/后缀。
- 本文为 `enforcement: gate`: 只有门禁覆盖的条款才是 MUST, 其余命名规则以 SHOULD 为主(避免为满足形式而过度重构/过度抽象).

## 适用范围

- Python：模块/文件、类、函数、变量、常量、Flask 蓝图与路由函数。
- 前端：目录、JS/CSS 文件、变量/函数/类、模板宏、data-* 属性命名。

## 规则（MUST/SHOULD/MAY）

### 1) 通用命名指南(SHOULD)

- SHOULD：Python 模块/函数/变量使用 `snake_case`；类使用 `CapWords`；常量使用 `CAPS_WITH_UNDER`。
- SHOULD：前端 JS/CSS/目录默认使用 `kebab-case`；变量/函数使用 `camelCase`；类使用 `UpperCamelCase`；常量使用 `CONSTANT_CASE`。
- SHOULD：文件名优先使用完整英文单词，避免含义不清的缩写(会增加搜索与沟通成本)。
  - MAY: 允许常见且无歧义的缩写(示例: `id`, `url`, `api`, `db`, `ui`, `css`, `js`)。

补充说明（与现状对齐）：

- MUST：`app/static/js/modules/services/` 与 `app/static/js/modules/stores/` 目录下，文件名沿用 `snake_case.js`（现有约定），新文件需保持一致。
- SHOULD：`app/static/js/` 其他目录（`common/`、`core/`、`bootstrap/` 等）继续使用 `kebab-case.js`。

### 2) Flask 路由与蓝图命名(门禁覆盖)

- SHOULD：蓝图函数使用动词短语（例如 `list_instances`、`get_user`、`create_tag`）。
- MUST NOT：出现 `api_` 前缀或 `_api` 后缀（例如 `api_list_users`、`get_user_api`）。

### 3) 命名守卫(门禁强约束)

- MUST NOT：函数命名包含实现细节后缀 `_optimized`(如需区分实现, 用模块/类分层表达).
- SHOULD NOT：函数命名包含 `_legacy` 等长期存在的实现细节后缀(如确需保留过渡期, 参考 [[standards/backend/design/compatibility-and-deprecation]]).
- MUST：聚合类命名保持单数语义(例如 `get_instance_aggregations`), 禁止“双复数”(例如 `get_instances_aggregations`).

#### 3.1 迁移类重命名目标(门禁)

下列旧文件名如仍存在, 视为必须清理的历史残留(由门禁脚本直接拦截):

- `app/routes/database_aggr.py` -> `app/routes/database_aggregations.py`
- `app/routes/instance_aggr.py` -> `app/routes/instance_aggregations.py`

> [!note]
> `app/views/*_form_view.py` 等历史命名目标, 以门禁脚本输出为准(脚本会给出“旧 -> 新”映射).

#### 3.2 门禁覆盖范围(可执行判据)

当前命名门禁只覆盖“最容易造成长期漂移/返工”的少数高风险形态, 并不试图穷举所有命名偏好:

- Routes 中禁止: `def api_*` / `def *_api`
- 全仓禁止: `def *_optimized`
- 聚合命名禁止: `databases_aggregations` / `instances_aggregations`
- 迁移类重命名目标: 见上文 3.1

新增“命名 MUST”前 SHOULD 先做两件事:

1) 能否被脚本稳定检查(否则不要写 MUST)
2) 是否真的会造成可观测的返工/事故(否则放在 SHOULD 指南)

## 正反例

### 正例

- 文件：`app/services/accounts_sync/coordinator.py`
- 路由函数：`list_instances`、`create_credential`
- 前端目录：`app/static/js/modules/views/credentials/`

### 反例

- 文件：`app/services/form_service/credential_form_service.py`（含 `_form_service` 后缀）
- 路由函数：`api_list_users`、`get_user_api`
- 前端文件：`account_ledger.js`（下划线命名）

## 门禁/检查方式

- 命名巡检（推荐作为提交前基线）：`./scripts/ci/refactor-naming.sh --dry-run`
- 执行重命名（仅在确认影响面后使用）：`./scripts/ci/refactor-naming.sh`
- 重命名后的最小自检建议：
  - `rg -n "<旧名字>"` 全仓确认 0 命中
  - `make format`
  - `ruff check <变更文件或目录>`
  - `make typecheck`

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 统一结构，补齐 MUST/SHOULD/MAY、正反例与门禁说明。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
