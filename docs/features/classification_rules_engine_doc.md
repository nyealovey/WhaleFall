# 分类规则引擎技术文档

## 1. 功能概述

### 1.1 功能描述
分类规则引擎是鲸落系统的**智能决策核心**，专门负责规则的定义、解析、评估和执行。该引擎基于权限匹配的规则表达式系统，支持多种数据库类型的复杂权限匹配逻辑，实现账户的自动分类功能。

### 1.2 主要特性
- **规则CRUD管理**：创建、查看、编辑、删除分类规则
- **多数据库支持**：MySQL、PostgreSQL、SQL Server、Oracle四种数据库
- **权限表达式系统**：基于JSON的权限匹配规则定义
- **实时规则评估**：规则匹配账户预览和统计
- **自动分类引擎**：OptimizedAccountClassificationService优化服务
- **规则优先级**：支持规则优先级排序和冲突解决
- **批量分类处理**：支持按实例或全量的批量自动分类

### 1.3 技术特点
- 基于权限的规则匹配算法
- 支持AND/OR逻辑运算符
- 数据库类型特定的权限结构
- 缓存优化的规则评估
- 异步批量处理能力

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   规则定义层    │    │   规则引擎核心  │    │   数据适配层    │
│                 │    │                 │    │                 │
│ - 规则编辑界面  │◄──►│ - 规则解析器    │◄──►│ - 账户数据源    │
│ - 权限配置UI    │    │ - 条件评估器    │    │ - 权限数据源    │
│ - 规则测试器    │    │ - 批量处理器    │    │ - 实例数据源    │
│ - 匹配预览      │    │ - 缓存管理器    │    │ - 数据转换器    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **规则管理**：规则CRUD操作和权限配置界面
- **规则引擎**：OptimizedAccountClassificationService核心服务
- **匹配算法**：基于权限的账户匹配逻辑
- **批量处理**：ClassificationBatchService批次管理

## 3. 前端实现

### 3.1 页面结构
- **规则管理界面**：集成在`app/templates/account_classification/management.html`中
- **样式文件**：`app/static/css/pages/account_classification/account_classification.css`
- **脚本文件**：`app/static/js/pages/account_classification/account_classification.js`

### 3.2 核心组件

#### 3.2.1 规则列表展示
```javascript
// 显示规则列表
function displayRules(rulesByDbType) {
    const container = document.getElementById('rulesList');
    
    let html = '';
    for (const [dbType, rules] of Object.entries(rulesByDbType)) {
        const dbIcons = {
            'mysql': 'fas fa-database',
            'postgresql': 'fas fa-elephant', 
            'sqlserver': 'fas fa-server',
            'oracle': 'fas fa-database'
        };
        
        html += `
            <div class="rule-group-card">
                <div class="card">
                    <div class="card-header">
                        <h5>
                            <i class="${dbIcons[dbType]} me-2 text-primary"></i>
                            ${dbType.toUpperCase()} 规则
                            <span class="badge bg-primary ms-2 rounded-pill">${rules.length}</span>
                        </h5>
                    </div>
                    <div class="card-body">
                        ${renderRulesForDbType(rules)}
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}
```

#### 3.2.2 权限配置界面
```javascript
// 显示权限配置（按数据库类型）
function displayPermissionsConfig(permissions, prefix = '', dbType = '') {
    const container = document.getElementById(prefix ? `${prefix}PermissionsConfig` : 'permissionsConfig');
    
    let html = '<div class="row">';
    
    if (dbType === 'mysql') {
        // MySQL：全局权限 + 数据库权限
        html += `
            <div class="col-md-6">
                <h6 class="text-primary mb-3">
                    <i class="fas fa-globe me-2"></i>全局权限
                </h6>
                <div class="permission-section">
                    ${permissions.global_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" 
                                   value="${perm.name}" id="${prefix}global_${perm.name}">
                            <label class="form-check-label" for="${prefix}global_${perm.name}">
                                <i class="fas fa-globe text-primary me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '全局权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-success mb-3">
                    <i class="fas fa-database me-2"></i>数据库权限
                </h6>
                <div class="permission-section">
                    ${permissions.database_privileges.map(perm => `
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="checkbox" 
                                   value="${perm.name}" id="${prefix}db_${perm.name}">
                            <label class="form-check-label" for="${prefix}db_${perm.name}">
                                <i class="fas fa-database text-success me-2"></i>
                                <div>
                                    <div class="fw-bold">${perm.name}</div>
                                    <small class="text-muted">${perm.description || '数据库权限'}</small>
                                </div>
                            </label>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } else if (dbType === 'sqlserver') {
        // SQL Server：服务器角色 + 数据库角色 + 权限
        html += renderSqlServerPermissions(permissions, prefix);
    } else if (dbType === 'postgresql') {
        // PostgreSQL：预定义角色 + 角色属性 + 权限
        html += renderPostgreSQLPermissions(permissions, prefix);
    } else if (dbType === 'oracle') {
        // Oracle：系统权限 + 角色 + 表空间权限
        html += renderOraclePermissions(permissions, prefix);
    }
    
    html += '</div>';
    container.innerHTML = html;
}
```

### 3.3 规则创建和编辑

#### 3.3.1 规则创建
```javascript
function createRule() {
    const classificationId = document.getElementById('ruleClassification').value;
    const ruleName = document.getElementById('ruleName').value;
    const dbType = document.getElementById('ruleDbType').value;
    const operator = document.getElementById('ruleOperator').value;

    // 收集选中的权限
    const selectedPermissions = collectSelectedPermissions(dbType);

    // 构建规则表达式
    const ruleExpression = buildRuleExpression(dbType, selectedPermissions, operator);

    const data = {
        classification_id: parseInt(classificationId),
        rule_name: ruleName,
        db_type: dbType,
        rule_expression: ruleExpression
    };

    fetch('/account-classification/rules', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', '规则创建成功');
            loadRules();
        } else {
            showAlert('danger', data.error);
        }
    });
}
```

## 4. 后端实现

### 4.1 路由控制器
**文件**：`app/routes/account_classification.py`

#### 4.1.1 规则管理API
```python
@account_classification_bp.route("/rules")
@login_required
@view_required
def get_rules() -> "Response":
    """获取规则列表"""
    try:
        rules = ClassificationRule.query.filter_by(is_active=True).all()
        
        # 获取匹配账户数量
        service = OptimizedAccountClassificationService()
        result = []
        for rule in rules:
            matched_count = service.get_rule_matched_accounts_count(rule.id)
            result.append({
                "id": rule.id,
                "rule_name": rule.rule_name,
                "classification_id": rule.classification_id,
                "classification_name": (rule.classification.name if rule.classification else None),
                "db_type": rule.db_type,
                "rule_expression": rule.rule_expression,
                "is_active": rule.is_active,
                "matched_accounts_count": matched_count,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            })

        # 按数据库类型分组
        rules_by_db_type = {}
        for rule in result:
            db_type = rule.get("db_type", "unknown")
            if db_type not in rules_by_db_type:
                rules_by_db_type[db_type] = []
            rules_by_db_type[db_type].append(rule)

        return jsonify({"success": True, "rules_by_db_type": rules_by_db_type})
    except Exception as e:
        log_error(f"获取规则列表失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})

@account_classification_bp.route("/rules", methods=["POST"])
@login_required
@create_required
def create_rule() -> "Response":
    """创建分类规则"""
    try:
        data = request.get_json()

        # 将规则表达式对象转换为JSON字符串
        rule_expression_json = json.dumps(data["rule_expression"], ensure_ascii=False)

        rule = ClassificationRule(
            rule_name=data["rule_name"],
            classification_id=data["classification_id"],
            db_type=data["db_type"],
            rule_expression=rule_expression_json,
            is_active=True,
        )

        db.session.add(rule)
        db.session.commit()

        return jsonify({"success": True, "message": "规则创建成功"})
    except Exception as e:
        db.session.rollback()
        log_error(f"创建规则失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})
```

#### 4.1.2 自动分类API
```python
@account_classification_bp.route("/auto-classify-optimized", methods=["POST"])
@login_required
@update_required
def auto_classify_optimized() -> "Response":
    """使用优化后的服务进行自动分类"""
    try:
        data = request.get_json()
        instance_id = data.get("instance_id")
        batch_type = data.get("batch_type", "manual")

        service = OptimizedAccountClassificationService()
        result = service.auto_classify_accounts_optimized(
            instance_id=instance_id,
            batch_type=batch_type,
            created_by=current_user.id if current_user.is_authenticated else None,
        )

        return jsonify(result)
    except Exception as e:
        log_error("自动分类异常", module="account_classification", exception=e)
        return jsonify({"success": False, "error": str(e)})
```

### 4.2 数据模型

#### 4.2.1 分类规则模型
```python
class ClassificationRule(db.Model):
    """分类规则模型"""

    __tablename__ = "classification_rules"

    id = db.Column(db.Integer, primary_key=True)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False)
    db_type = db.Column(db.String(20), nullable=False)  # mysql, postgresql, sqlserver, oracle
    rule_name = db.Column(db.String(100), nullable=False)  # 规则名称
    rule_expression = db.Column(db.Text, nullable=False)  # 规则表达式（JSON格式）
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)

    def get_rule_expression(self) -> dict:
        """获取规则表达式（解析JSON）"""
        try:
            return json.loads(self.rule_expression)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_rule_expression(self, expression: dict) -> None:
        """设置规则表达式（保存为JSON）"""
        self.rule_expression = json.dumps(expression, ensure_ascii=False)
```

### 4.3 核心服务层

#### 4.3.1 优化的分类服务
```python
class OptimizedAccountClassificationService:
    """优化后的账户分类管理服务"""

    def auto_classify_accounts_optimized(
        self,
        instance_id: int = None,
        batch_type: str = "manual",
        created_by: int = None,
    ) -> dict[str, Any]:
        """优化后的自动分类账户 - 全量重新分类"""
        start_time = time.time()
        
        try:
            # 1. 创建分类批次
            self.batch_id = ClassificationBatchService.create_batch(
                batch_type=batch_type,
                instance_id=instance_id,
                created_by=created_by,
            )

            # 2. 获取规则（带缓存）
            rules = self._get_classification_rules()
            if not rules:
                return {"success": False, "error": "没有找到有效的分类规则"}

            # 3. 获取账户（过滤条件）
            accounts = self._get_accounts_to_classify(instance_id)
            if not accounts:
                return {"success": False, "error": "没有找到需要分类的账户"}

            # 4. 按数据库类型优化分类
            result = self._classify_accounts_by_db_type_optimized(accounts, rules)

            # 5. 完成批次
            ClassificationBatchService.complete_batch(
                self.batch_id,
                status="completed",
                batch_details=result,
            )

            return {
                "success": True,
                "message": "自动分类完成",
                "batch_id": self.batch_id,
                **result,
            }
        except Exception as e:
            if self.batch_id:
                ClassificationBatchService.complete_batch(
                    self.batch_id, status="failed", error_message=str(e)
                )
            log_error(f"优化后的自动分类失败: {e}", module="account_classification")
            return {"success": False, "error": f"自动分类失败: {str(e)}"}
```

#### 4.3.2 规则评估算法
```python
def _evaluate_rule(self, account: CurrentAccountSyncData, rule: ClassificationRule) -> bool:
    """评估单个规则是否匹配账户"""
    try:
        rule_expression = rule.get_rule_expression()
        if not rule_expression:
            return False

        rule_type = rule_expression.get("type", "permissions")
        operator = rule_expression.get("operator", "OR")

        if rule_type == "mysql_permissions":
            return self._evaluate_mysql_permissions(account, rule_expression, operator)
        elif rule_type == "sqlserver_permissions":
            return self._evaluate_sqlserver_permissions(account, rule_expression, operator)
        elif rule_type == "postgresql_permissions":
            return self._evaluate_postgresql_permissions(account, rule_expression, operator)
        elif rule_type == "oracle_permissions":
            return self._evaluate_oracle_permissions(account, rule_expression, operator)
        else:
            # 旧版本兼容
            permissions = rule_expression.get("permissions", [])
            return self._check_permissions_match(account, permissions, operator)

    except Exception as e:
        log_error(f"规则评估失败: {e}", module="account_classification")
        return False

def _evaluate_mysql_permissions(self, account, rule_expression: dict, operator: str) -> bool:
    """评估MySQL权限规则"""
    global_privileges = rule_expression.get("global_privileges", [])
    database_privileges = rule_expression.get("database_privileges", [])
    
    matched_permissions = []
    
    # 检查全局权限
    for privilege in global_privileges:
        if self._has_mysql_global_privilege(account, privilege):
            matched_permissions.append(privilege)
    
    # 检查数据库权限  
    for privilege in database_privileges:
        if self._has_mysql_database_privilege(account, privilege):
            matched_permissions.append(privilege)
    
    # 根据操作符判断结果
    all_permissions = global_privileges + database_privileges
    if operator == "AND":
        return len(matched_permissions) == len(all_permissions)
    else:  # OR
        return len(matched_permissions) > 0
```

## 5. 规则表达式系统

### 5.1 MySQL规则表达式
```json
{
    "type": "mysql_permissions",
    "global_privileges": ["SUPER", "CREATE USER", "RELOAD"],
    "database_privileges": ["ALL PRIVILEGES", "CREATE", "DROP"],
    "operator": "OR"
}
```

### 5.2 SQL Server规则表达式
```json
{
    "type": "sqlserver_permissions", 
    "server_roles": ["sysadmin", "serveradmin"],
    "server_permissions": ["ALTER ANY LOGIN", "CREATE ANY DATABASE"],
    "database_roles": ["db_owner", "db_ddladmin"],
    "database_privileges": ["CONTROL", "ALTER ANY SCHEMA"],
    "operator": "OR"
}
```

### 5.3 PostgreSQL规则表达式
```json
{
    "type": "postgresql_permissions",
    "predefined_roles": ["pg_read_all_settings", "pg_read_all_stats"],
    "role_attributes": ["can_super", "can_create_db", "can_create_role"],
    "database_privileges": ["CREATE", "CONNECT", "TEMPORARY"],
    "tablespace_privileges": ["CREATE"],
    "operator": "OR"
}
```

### 5.4 Oracle规则表达式
```json
{
    "type": "oracle_permissions",
    "roles": ["DBA", "CONNECT", "RESOURCE"],
    "system_privileges": ["CREATE ANY TABLE", "DROP ANY TABLE", "ALTER SYSTEM"],
    "tablespace_privileges": ["CREATE TABLE", "ALTER TABLESPACE"],
    "tablespace_quotas": ["UNLIMITED", "100M"],
    "operator": "OR"
}
```

## 6. 批量处理机制

### 6.1 批次管理
```python
class ClassificationBatchService:
    """分类批次服务"""
    
    @staticmethod
    def create_batch(batch_type: str, instance_id: int = None, created_by: int = None) -> str:
        """创建分类批次"""
        batch_id = str(uuid4())
        batch = ClassificationBatch(
            batch_id=batch_id,
            batch_type=batch_type,
            instance_id=instance_id,
            status="running",
            created_by=created_by,
        )
        db.session.add(batch)
        db.session.commit()
        return batch_id
```

### 6.2 分类分配模型
```python
class AccountClassificationAssignment(db.Model):
    """账户分类分配模型"""

    __tablename__ = "account_classification_assignments"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("current_account_sync_data.id"), nullable=False)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # 分配人
    assignment_type = db.Column(db.String(20), nullable=False, default="auto")  # auto, manual
    confidence_score = db.Column(db.Float, nullable=True)  # 自动分配的置信度分数
    notes = db.Column(db.Text, nullable=True)  # 备注
    batch_id = db.Column(db.String(36), nullable=True)  # 批次ID
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
```

## 7. 性能优化

### 7.1 缓存策略
- 规则列表缓存：避免重复数据库查询
- 权限数据缓存：缓存账户权限信息
- 按数据库类型分组：减少无效匹配

### 7.2 批量处理优化
```python
def _classify_accounts_by_db_type_optimized(
    self, accounts: list[CurrentAccountSyncData], rules: list[ClassificationRule]
) -> dict[str, Any]:
    """按数据库类型优化分类"""
    # 1. 按数据库类型预分组
    accounts_by_db_type = self._group_accounts_by_db_type(accounts)
    rules_by_db_type = self._group_rules_by_db_type(rules)
    
    # 2. 清除所有现有分类分配
    self._clear_all_classifications(accounts)
    
    # 3. 按数据库类型处理
    total_classifications_added = 0
    for db_type, db_accounts in accounts_by_db_type.items():
        db_rules = rules_by_db_type.get(db_type, [])
        if db_rules:
            result = self._classify_single_db_type(db_accounts, db_rules, db_type)
            total_classifications_added += result["total_classifications_added"]
    
    return {
        "total_accounts": len(accounts),
        "total_rules": len(rules),
        "total_classifications_added": total_classifications_added,
    }
```

## 8. 监控和调试

### 8.1 规则匹配预览
```python
@account_classification_bp.route("/rules/<int:rule_id>/matched-accounts", methods=["GET"])
def get_matched_accounts(rule_id: int) -> "Response":
    """获取规则匹配的账户（支持分页）"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 获取匹配的账户
        service = OptimizedAccountClassificationService()
        matched_accounts = service.get_rule_matched_accounts_paginated(
            rule_id, page, per_page
        )
        
        return jsonify({
            "success": True,
            "accounts": matched_accounts["accounts"],
            "rule_name": rule.rule_name,
            "pagination": matched_accounts["pagination"]
        })
    except Exception as e:
        log_error(f"获取匹配账户失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})
```

### 8.2 性能监控
```python
def _log_performance_stats(
    self, duration: float, total_accounts: int, total_rules: int, result: dict[str, Any]
) -> None:
    """记录性能统计"""
    accounts_per_second = total_accounts / duration if duration > 0 else 0

    log_info(
        "优化后的自动分类性能统计",
        module="account_classification",
        batch_id=self.batch_id,
        duration=f"{duration:.2f}秒",
        total_accounts=total_accounts,
        total_rules=total_rules,
        accounts_per_second=f"{accounts_per_second:.2f}",
        total_classifications_added=result.get("total_classifications_added", 0),
    )
```

## 9. 错误处理和异常管理

### 9.1 规则验证
- 规则表达式JSON格式验证
- 权限名称有效性检查
- 数据库类型匹配验证

### 9.2 分类失败处理
- 批次失败回滚机制
- 单