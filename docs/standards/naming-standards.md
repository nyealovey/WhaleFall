# 命名规范

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：仓库内所有文件/目录/符号命名（Python、Jinja2、JS、CSS、脚本）

## 目的

- 降低“同一概念多种命名”的漂移成本，减少重构与搜索负担。
- 保证自动化命名巡检脚本可持续生效，避免出现不可控的历史残留前缀/后缀。

## 适用范围

- Python：模块/文件、类、函数、变量、常量、Flask 蓝图与路由函数。
- 前端：目录、JS/CSS 文件、变量/函数/类、模板宏、data-* 属性命名。

## 规则（MUST/SHOULD/MAY）

### 1) 基础命名规则

- MUST：Python 模块/函数/变量使用 `snake_case`；类使用 `CapWords`；常量使用 `CAPS_WITH_UNDER`。
- MUST：前端 JS/CSS/目录默认使用 `kebab-case`；变量/函数使用 `camelCase`；类使用 `UpperCamelCase`；常量使用 `CONSTANT_CASE`。
- MUST：文件名使用完整英文单词，禁止缩写（例如禁止 `svc`、`mgr`、`cfg` 作为文件名的一部分）。

补充说明（与现状对齐）：

- MUST：`app/static/js/modules/services/` 与 `app/static/js/modules/stores/` 目录下，文件名沿用 `snake_case.js`（现有约定），新文件需保持一致。
- SHOULD：`app/static/js/` 其他目录（`common/`、`core/`、`bootstrap/` 等）继续使用 `kebab-case.js`。

### 2) Flask 路由与蓝图命名

- MUST：蓝图函数必须为动词短语（例如 `list_instances`、`get_user`、`create_tag`）。
- MUST NOT：出现 `api_` 前缀或 `_api` 后缀（例如 `api_list_users`、`get_user_api`）。

### 3) 目录/模块约束（命名守卫）

- MUST：`app/services/form_service/` 下的文件名不得包含 `_form_service` 后缀，应使用更具体的资源名（例如 `resource_service.py`、`password_service.py`）。
- MUST NOT：函数命名包含实现细节（例如 `_optimized`、`_legacy`）；如需区分实现，使用模块/类分层表达。
- MUST：聚合类函数名保持单数语义（例如 `get_instance_aggregations`），禁止“双复数”（例如 `get_instances_aggregations`）。

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
