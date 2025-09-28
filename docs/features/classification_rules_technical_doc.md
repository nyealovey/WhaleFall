# 分类规则引擎技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供分类规则的CRUD操作，支持JSON格式的规则表达式定义。
- 实现规则与账户的匹配逻辑，支持多种数据库类型的权限规则。
- 提供规则测试、匹配统计、缓存管理等功能。
- 支持规则的优先级排序和冲突解决。

### 1.2 代码定位
- 路由：`app/routes/account_classification.py`（规则相关接口）
- 模型：`app/models/classification_rule.py`、`app/models/account_classification.py`
- 服务：`app/services/account_classification_service.py`
- 前端：`app/static/js/pages/account_classification/account_classification.js`
- 模板：`app/templates/account_classification/management.html`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 前端规则管理界面             │
│  - 规则列表/编辑            │
│  - 规则测试/预览            │
│  - 匹配账户查看             │
└───────▲───────────┬──────┘
        │AJAX        │
┌───────┴───────────▼──────┐
│ Flask 路由 (account_classification)│
│  - /rules CRUD           │
│  - /rules/<id>/matched-accounts │
│  - /permissions/<db_type> │
└───────▲───────────┬──────┘
        │SQLAlchemy │服务调用
┌───────┴───────────▼──────┐
│ 数据层与服务              │
│  - ClassificationRule     │
│  - AccountClassification  │
│  - AccountClassificationService│
└────────────────────────────┘
```

### 2.2 权限控制
- 所有接口使用 `@login_required`，查看操作需 `@view_required`，写操作需 `@create_required`、`@update_required`、`@delete_required`。

## 3. 数据模型（`classification_rule.py`）

### 3.1 核心字段
- `id`：主键
- `classification_id`：关联的分类ID（外键）
- `db_type`：数据库类型（mysql、postgresql、sqlserver、oracle）
- `rule_name`：规则名称
- `description`：规则描述
- `rule_expression`：规则表达式（JSON格式）
- `priority`：优先级（数值越大优先级越高）
- `is_active`：是否激活
- `match_count`：匹配次数统计
- `evaluation_count`：评估次数统计

### 3.2 关键方法
- `get_rule_expression()`：解析JSON格式的规则表达式
- `set_rule_expression(expression)`：设置规则表达式
- `increment_match_count()`：增加匹配次数
- `increment_evaluation_count()`：增加评估次数
- `to_dict()`：序列化为字典格式

## 4. 路由实现（`account_classification.py`）

### 4.1 规则管理接口
- `GET /rules`（256-294）：获取所有分类规则，按数据库类型分组，包含匹配数量统计。
- `POST /rules`（300-332）：创建新规则，验证规则表达式JSON格式，创建后清理缓存。
- `GET /rules/<id>`（339-366）：获取单个规则详情。
- `PUT /rules/<id>`（372-405）：更新规则，支持规则表达式更新，更新后清理缓存。
- `DELETE /rules/<id>`（516-532）：删除规则。

### 4.2 规则匹配接口
- `GET /rules/<id>/matched-accounts`（408-513）：
  - 获取规则匹配的账户列表，支持分页和搜索。
  - 基于 `AccountClassificationAssignment` + `CurrentAccountSyncData` + `Instance` 关联查询。
  - 支持按账户名、实例名搜索过滤。

### 4.3 权限配置接口
- `GET /permissions/<db_type>`（694-705）：获取指定数据库类型的权限定义。
- 通过 `_get_db_permissions()` 方法使用 `PermissionConfig` 模型获取权限配置。

## 5. 服务层实现（`account_classification_service.py`）

### 5.1 规则匹配服务
- `get_rule_matched_accounts_count(rule_id)`：获取规则匹配的账户数量统计。
- `auto_classify_accounts_optimized(instance_id, created_by)`：优化的自动分类算法。
- `invalidate_cache()`：清理分类相关缓存。

### 5.2 规则表达式处理
- 规则表达式以JSON格式存储，支持复杂的条件组合。
- 支持AND、OR、NOT逻辑运算符。
- 支持多种匹配模式：精确匹配、包含匹配、正则表达式等。

## 6. 前端实现（`account_classification.js`）

### 6.1 规则管理功能
- `loadRules()`（286-300）：加载规则列表，按数据库类型分组显示。
- `displayRules()`（320-416）：渲染规则卡片，显示规则信息、匹配数量、操作按钮。
- `createRule()`（771-938）：创建规则，组装规则表达式JSON。
- `editRule()`（941-990）：编辑规则，加载规则详情并填充表单。
- `updateRule()`（1098-1267）：更新规则，PUT请求提交修改。
- `deleteRule()`（1777-1801）：删除规则，带确认提示。

### 6.2 权限配置功能
- `loadPermissions()`（440-473）：根据数据库类型动态加载权限配置。
- `displayPermissionsConfig()`（476-767）：渲染权限配置界面，支持复选框选择。
- `setSelectedPermissions()`（993-1096）：设置已保存的权限选择状态。

### 6.3 规则测试功能
- `viewMatchedAccounts()`（1272-1292）：查看规则匹配的账户列表。
- `displayMatchedAccounts()`（1295-1385）：渲染匹配账户表格，支持分页和搜索。
- `generatePagination()`（1398-1488）：生成分页控件。

## 7. 规则表达式语法

### 7.1 JSON格式结构
```json
{
  "type": "mysql|postgresql|sqlserver|oracle",
  "permissions": ["permission1", "permission2"],
  "operator": "AND|OR",
  "conditions": [
    {
      "field": "username",
      "operator": "contains|equals|regex",
      "value": "admin"
    }
  ]
}
```

### 7.2 支持的匹配操作符
- `contains`：包含匹配
- `equals`：精确匹配
- `regex`：正则表达式匹配
- `in`：在列表中
- `notIn`：不在列表中

### 7.3 数据库类型特定规则
- **MySQL**：支持全局权限、数据库权限、表权限等。
- **SQL Server**：支持服务器角色、数据库角色、权限等。
- **PostgreSQL**：支持角色属性、权限等。
- **Oracle**：支持系统权限、角色权限等。

## 8. 缓存管理

### 8.1 缓存策略
- 规则创建/更新后调用 `AccountClassificationService.invalidate_cache()`（323-399）。
- 使用 `CacheManager` 管理规则评估缓存。
- 支持按数据库类型的缓存分组。

### 8.2 缓存键设计
- 规则缓存：`classification_rules:{db_type}`
- 账户缓存：`accounts_by_db_type:{db_type}`
- 规则评估缓存：`rule_eval:{rule_id}:{account_id}`

## 9. 性能优化

### 9.1 查询优化
- 使用索引优化规则查询性能。
- 分页查询避免大量数据加载。
- 缓存频繁访问的规则数据。

### 9.2 前端优化
- 按需加载权限配置，避免一次性加载全部。
- 使用防抖技术优化搜索输入。
- 异步加载匹配账户数据。

## 10. 错误处理

### 10.1 后端错误处理
- 规则表达式JSON解析错误处理。
- 数据库查询异常处理。
- 权限验证失败处理。

### 10.2 前端错误处理
- AJAX请求错误处理。
- 表单验证错误提示。
- 用户操作确认提示。

## 11. 测试建议

### 11.1 功能测试
- 规则CRUD操作的完整性。
- 规则表达式解析的正确性。
- 匹配逻辑的准确性。

### 11.2 性能测试
- 大量规则的查询性能。
- 规则匹配的执行效率。
- 缓存机制的有效性。

## 12. 后续优化方向

### 12.1 功能增强
- 添加规则版本管理。
- 实现规则导入/导出功能。
- 支持规则模板和快速创建。

### 12.2 性能优化
- 实现规则评估的异步处理。
- 添加规则执行统计和监控。
- 优化大量账户的匹配性能。

### 12.3 用户体验
- 提供规则表达式可视化编辑器。
- 添加规则测试和调试工具。
- 实现规则执行日志和审计。
