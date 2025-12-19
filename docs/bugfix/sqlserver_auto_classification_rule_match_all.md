# SQLServer 自动分类规则“全量命中”问题修复文档

## 1. 背景与现象

在“账户分类管理”页面中，`SQLSERVER` 分组下的多条规则出现 **命中数=账户总数** 的异常现象（例如每条规则都显示 `1046 条命中`），并且无论如何调整规则勾选项，命中数都几乎不变。

该问题会进一步导致执行“自动分类”后，SQL Server 账户被错误地大范围分配到“风险账户/敏感账户/特权账户”等分类中，造成统计与报表污染。

## 2. 影响范围

- 直接影响：`db_type=sqlserver` 的规则评估与自动分类结果。
- 间接影响：规则命中数统计来自 `AccountClassificationAssignment`（规则-账户分配记录）。一旦误分配产生，页面会持续展示错误命中数，直到重新分类或清理分配数据。

## 3. 根因分析（前端 + 后端）

### 3.1 规则字段命名不一致（数据结构兼容问题）

前端在构造 SQL Server 的规则表达式时使用了 `database_privileges` 字段（来源于权限配置表 `permission_configs` 的分类字段），而后端 SQL Server 规则分类器读取的是 `database_permissions`。

结果是：当用户在“数据库权限”区域勾选权限时，后端无法从 `rule_expression` 中读取到对应条件，导致“数据库权限条件被忽略”。

- 前端位置：`app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js`
  - `SQLServerPermissionStrategy.buildExpression(...)` 生成 `database_privileges`
- 后端位置：`app/services/account_classification/classifiers/sqlserver_classifier.py`
  - 旧逻辑仅读取 `rule_expression["database_permissions"]`

### 3.2 OR 组合逻辑错误（空条件被当作 True）

SQL Server 分类器在评估规则时，固定计算 4 个维度的匹配结果：

- server_roles
- database_roles
- server_permissions
- database_permissions

在旧实现中，各 `_match_*` 方法在对应规则字段为空时直接返回 `True`。当规则 `operator=OR`（默认值）时，会出现：

`any([False, True, True, True]) == True`

也就是说，只要规则没有同时配置所有维度，就会因为“未配置维度= True”导致 **OR 恒成立**，最终匹配所有账户。

## 4. 修复策略

### 4.1 后端修复（核心）

1. **仅将“被配置过的条件”纳入组合**  
   - 规则表达式中对应字段非空才会加入 `match_results`。
   - 避免 `operator=OR` 时被空条件污染。

2. **兼容旧字段：`database_privileges` → `database_permissions`**  
   - 允许历史规则无需数据迁移即可正确生效。

3. **规则没有任何有效条件时返回 False**  
   - 避免“空规则”误匹配全量账户。

### 4.2 前端/数据层改进（可选，后续优化）

- 统一前后端字段命名（建议统一为 `database_permissions`），并在权限配置输出/API 层提供别名映射，逐步移除双字段。
- 若要做彻底统一，需要同时处理：
  - `permission_configs` 中 SQL Server 的 `category=database_privileges` 命名
  - 既有规则表达式 JSON 的字段迁移

## 5. 代码变更摘要

- `app/services/account_classification/classifiers/sqlserver_classifier.py`
  - 修复 OR 组合逻辑：只组合非空条件。
  - 兼容 `database_privileges` 旧字段。
  - 空条件时返回 False。
- 同类修复（附带收益）：`postgresql_classifier.py`、`oracle_classifier.py`
  - 同样修复“OR 被空条件污染导致全量命中”的问题，并完善 AND/OR 语义一致性。

## 6. 部署与数据修复步骤（非常重要）

仅上线代码不会自动修正已写入的历史命中结果，因为页面命中数来自分配表。

推荐流程：

1. 部署后端代码。
2. （建议）清理分类规则缓存：
   - 若已启用缓存管理接口，可调用清理接口，例如按数据库类型清理 `sqlserver`。
3. 重新执行自动分类：
   - 在“账户分类管理”页面点击“自动分类”，或调用 `/accounts/classifications/api/auto-classify`。
   - 自动分类流程会在开始阶段清理旧分配记录（删除 `AccountClassificationAssignment`），然后重新按修复后的规则生成分配。
4. 回到规则列表页确认命中数恢复合理范围（不再每条规则都等于账户总数）。

## 7. 验证清单

建议至少验证以下用例：

1. **SQLServer 单条件 OR**：仅选择一项服务器权限或数据库权限（如 `DELETE`），触发自动分类后命中数应小于总账户数。
2. **SQLServer 不存在权限**：选择一个绝不可能存在的权限名，命中数应为 0。
3. **跨维度 OR**：同时勾选服务器角色与数据库权限，命中应为两者并集。
4. 查看服务端日志：应能看到每条规则的 `matched_accounts` 与预期一致。

## 8. 回滚方案

若需要回滚到旧版本：

1. 回滚代码后，**不要直接依赖现有命中数**（可能仍是修复后重新分类得到的结果）。
2. 若回滚后仍需保持正确分配，需要保留当前分配表数据或提前导出快照。
3. 回滚后再次触发“自动分类”会重新生成分配记录；旧版本存在误匹配风险，请谨慎操作。

## 9. 兼容/回退/兜底逻辑记录（便于后续清理）

- 位置：`app/services/account_classification/classifiers/sqlserver_classifier.py`
  - 类型：兼容
  - 描述：规则字段兼容，支持 `database_permissions` 与 `database_privileges` 双 key 解析（历史规则不迁移也可生效）
  - 建议：后续统一命名并执行一次性数据迁移后删除兼容分支

