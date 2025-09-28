# 账户分类管理功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 管理账户分类全生命周期：创建、编辑、删除、查看、优先级调整、系统分类保护。
- 提供按分类/数据库类型分组的规则管理与匹配统计。
- 支持自动分类及分类分配查询，关联权限配置与缓存维护。
- 所有核心操作均记录结构化日志并受严格权限控制。

### 1.2 代码定位
- 路由：`app/routes/account_classification.py`
- 模板：`app/templates/account_classification/management.html`
- 脚本：`app/static/js/pages/account_classification/account_classification.js`
- 模型：`app/models/account_classification.py`、`account_classification_assignment.py`、`classification_rule.py`
- 服务：`app/services/account_classification_service.py`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 前端 UI (management.html)   │
│  - 分类卡片、规则列表      │
│  - 模态框、自动分类入口    │
└───────▲───────────┬──────┘
        │AJAX        │
┌───────┴───────────▼──────┐
│ Flask 路由 (account_bp)    │
│  - /classifications CRUD   │
│  - /rules、/permissions    │
│  - /auto-classify(*)       │
│  - /assignments            │
└───────▲───────────┬──────┘
        │SQLAlchemy │服务
┌───────┴───────────▼──────┐
│ 模型/服务层               │
│  - AccountClassification  │
│  - ClassificationRule     │
│  - AccountAssignment      │
│  - AccountClassificationService│
└────────────────────────────┘
```

### 2.2 权限与缓存
- 所有接口使用 `@login_required`，视图/写操作叠加 `view/create/update/delete_required`（路由 19-24）。
- 规则创建/更新后调用 `AccountClassificationService.invalidate_cache()`（323-399）清理缓存。

## 3. 前端实现

### 3.1 页面结构（`management.html`）
- 左侧分类列表（33-53）通过 JS 载入。
- 右侧规则管理卡片（56-441）含新增按钮、列表、模态框。
- 自动分类按钮（21-24）仅管理员可见。
- 匹配账户、查看/编辑规则等模态框块 373-527。

### 3.2 分类交互（`account_classification.js`）
- 初始化加载：`DOMContentLoaded` 调用 `loadClassifications()` 与 `loadRules()`（31-35）。
- 列表渲染：`loadClassifications()` + `displayClassifications()`（40-111）。
- CRUD：
  - 创建 `createClassification()` -> POST `/classifications`（114-149）。
  - 编辑 `editClassification()`（152-210）获取详情并弹窗；`updateClassification()`（213-257）PUT 更新。
  - 删除 `deleteClassification()`（260-280）。
- UI 使用徽章颜色表示风险，管理员才显示操作按钮。

### 3.3 规则管理
- 加载规则：`loadRules()`（286-300）调用 `/rules`，`displayRules()`（320-416）按数据库分组展示。
- 权限配置：
  - `loadPermissions()`（440-473）根据数据库类型请求 `/permissions/<db_type>`。
  - `displayPermissionsConfig()`（476-767）按类型渲染复选框（MySQL 全局/库权限、SQL Server 角色/权限、PostgreSQL 角色属性、Oracle 系统/角色等）。
- 创建规则：`createRule()`（771-938）组装 `rule_expression`（type+权限列表+operator），POST `/rules`。
- 编辑规则：`editRule()`（941-990）加载详情，`setSelectedPermissions()`（993-1096）勾选已保存权限。
- 更新规则：`updateRule()`（1098-1267）PUT `/rules/<id>`；删除 `deleteRule()`（1777-1801）。
- 查看规则：`viewRule()`（1516-1556）调用 `displayViewPermissions()`（1559-1774）生成只读展示。

### 3.4 匹配账户与分页
- `viewMatchedAccounts()`（1272-1292）请求 `/rules/<id>/matched-accounts`，带分页/搜索参数。
- `displayMatchedAccounts()`（1295-1385）渲染表格、搜索框；`generatePagination()`（1398-1488）生成分页按钮；支持回车搜索 1503-1513。

### 3.5 自动分类入口
- `autoClassifyAll()`（1803-1858）POST `/auto-classify`，按钮在处理时禁用；成功后显示提示并刷新页面。

## 4. 后端路由（`account_classification.py`）

### 4.1 分类接口
- `GET /classifications`（47-90）：返回分类及规则数。
- `POST /classifications`（92-133）、`GET /classifications/<id>`（135-162）、`PUT`（165-188）、`DELETE`（191-211）。删除禁止系统分类。

### 4.2 规则接口
- 条件过滤：`GET /rules/filter`（214-253）。
- 分组列表：`GET /rules`（256-294）含匹配数量统计。
- CRUD：`POST /rules`（300-332）、`GET /rules/<id>`（339-366）、`PUT`（372-405）、`DELETE`（516-532）。创建/更新后清缓存（323-399）。
- 匹配账户：`GET /rules/<id>/matched-accounts`（408-513）基于 `AccountClassificationAssignment` + `CurrentAccountSyncData` + `Instance` 分页查询，并支持搜索。

### 4.3 自动分类与分配
- `POST /auto-classify` 与 `/auto-classify-optimized`（535-639）调用 `AccountClassificationService.auto_classify_accounts_optimized`，记录日志。
- `GET /assignments` 与 `DELETE /assignments/<id>`（641-691）查询/软删除分类分配。

### 4.4 权限配置
- `GET /permissions/<db_type>`（694-705）返回指定数据库类型的权限定义，通过 `_get_db_permissions` 使用 `PermissionConfig`。

## 5. 数据模型与服务

### 5.1 模型要点
- `AccountClassification`：字段 `name/risk_level/color/icon/priority/is_system/is_active`，包含 `get_account_count()`、`get_active_rules_count()`、`can_delete()`、`create_default_classifications()`。
- `ClassificationRule`：字段 `classification_id/db_type/rule_name/rule_expression/match_count` 等；`get_rule_expression()` 解析 JSON。
- `AccountClassificationAssignment`：记录账户与分类关联，用于匹配查询与移除（assignments 路由）。

### 5.2 服务（`AccountClassificationService`）
- `get_rule_matched_accounts_count(rule_id)`：供 `/rules` 列表统计。
- `auto_classify_accounts_optimized(instance_id, created_by)`：自动分类主逻辑，路由 555-607 调用。
- `invalidate_cache()`：规则更新后清理缓存，确保读取最新数据。

## 6. 权限与安全
- 前端基于 `window.currentUserRole` 控制按钮可见性（模板 21-67、JS 88-106、382-393）。
- 系统分类 (`is_system`) 后端拒绝删除；规则操作受管理员权限限制。
- 自动分类、规则 CRUD 等行为均记录 `log_info`/`log_error`，包含用户与实例上下文（路由 546-576等）。

## 7. 缓存与性能
- 规则新增/编辑删除后调用服务缓存失效（323-399）。
- `/rules/<id>/matched-accounts` 限定 `per_page <= 100` 并提供搜索参数（424-455）。
- 权限配置按需加载，避免一次性加载全部数据库权限。

## 8. 用户体验
- `showAlert()`（1863-1881）统一提示；模态框结合 Bootstrap。
- 权限展示按数据库类型生成图标和描述便于阅读（`displayPermissionsConfig`、`displayViewPermissions`）。
- 匹配账户弹窗支持搜索、分页并高亮匹配数量。

## 9. 测试建议
- 分类 CRUD：验证系统分类保护、字段必填、优先级更新。
- 规则创建/更新：覆盖各数据库类型权限结构、缓存失效生效。
- 匹配账户分页：校验搜索过滤与分页数据正确性。
- 自动分类：模拟存在多实例场景，核对分类数量与日志记录。

## 10. 后续优化方向
- 将 `rule_expression` 统一抽象为结构化模型，方便跨数据库扩展。
- 引入匹配账户缓存及导出功能，提高大量账户环境下性能。
- 自动分类进度与错误重试信息可视化。
- 与统一搜索系统对接，实现分类或规则的全局搜索入口。
