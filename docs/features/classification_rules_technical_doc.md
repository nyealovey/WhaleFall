# 分类规则引擎技术文档

## 1. 功能概述

### 1.1 功能描述
分类规则引擎是账户分类系统的**核心决策组件**，专门负责规则的定义、解析、评估和执行。该引擎提供强大的规则表达式系统，支持复杂的账户匹配逻辑，实现基于规则的智能分类决策。

### 1.2 主要特性
- **规则表达式引擎**：支持复杂的JSON格式规则表达式定义
- **多条件匹配**：支持AND、OR、NOT逻辑运算符
- **多种匹配模式**：精确匹配、正则表达式、包含匹配、范围匹配
- **规则优先级**：支持规则优先级排序和冲突解决
- **实时评估**：提供规则测试和实时账户匹配预览
- **缓存优化**：智能缓存规则评估结果，提升性能
- **规则调试**：提供详细的规则执行日志和调试信息

### 1.3 技术特点
- 基于JSON的声明式规则语法
- 支持嵌套条件和复合逻辑
- 高性能规则评估算法
- 规则热更新支持
- 分布式规则缓存
- 规则执行统计和监控

## 2. 规则引擎架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   规则定义层    │    │   规则引擎核心  │    │   数据适配层    │
│                 │    │                 │    │                 │
│ - 规则编辑器    │◄──►│ - 表达式解析器  │◄──►│ - 账户数据源    │
│ - 规则验证器    │    │ - 条件评估器    │    │ - 权限数据源    │
│ - 规则测试器    │    │ - 优先级管理器  │    │ - 实例数据源    │
│ - 语法高亮      │    │ - 缓存管理器    │    │ - 数据转换器    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **规则解析器**：解析JSON格式的规则表达式
- **条件评估器**：执行具体的匹配逻辑
- **优先级引擎**：处理规则冲突和优先级
- **缓存系统**：优化规则评估性能
- **执行监控**：记录规则执行统计和性能指标

## 3. 规则表达式语法

### 3.1 基础语法结构
```json
{
  "operator": "AND|OR|NOT",
  "conditions": [
    {
      "field": "字段名",
      "operator": "匹配操作符",
      "value": "匹配值",
      "type": "数据类型"
    }
  ],
  "groups": [
    {
      "operator": "AND|OR",
      "conditions": [...]
    }
  ]
}
```

### 3.2 支持的操作符

#### 3.2.1 字符串操作符
- `equals`: 精确匹配
- `contains`: 包含匹配
- `startsWith`: 前缀匹配
- `endsWith`: 后缀匹配
- `regex`: 正则表达式匹配
- `in`: 在列表中
- `notIn`: 不在列表中

#### 3.2.2 数值操作符
- `gt`: 大于
- `gte`: 大于等于
- `lt`: 小于
- `lte`: 小于等于
- `between`: 范围匹配

#### 3.2.3 逻辑操作符
- `AND`: 逻辑与
- `OR`: 逻辑或
- `NOT`: 逻辑非

### 3.3 规则示例

#### 3.3.1 简单规则示例
```json
{
  "operator": "AND",
  "conditions": [
    {
      "field": "username",
      "operator": "contains",
      "value": "admin",
      "type": "string"
    },
    {
      "field": "db_type",
      "operator": "equals",
      "value": "mysql",
      "type": "string"
    }
  ]
}
```

#### 3.3.2 复杂规则示例
```json
{
  "operator": "OR",
  "groups": [
    {
      "operator": "AND",
      "conditions": [
        {
          "field": "username",
          "operator": "regex",
          "value": "^(admin|root|sa)$",
          "type": "string"
        },
        {
          "field": "permissions",
          "operator": "contains",
          "value": "SUPER",
          "type": "array"
        }
      ]
    },
    {
      "operator": "AND",
      "conditions": [
        {
          "field": "is_system_account",
          "operator": "equals",
          "value": true,
          "type": "boolean"
        }
      ]
    }
  ]
}
```

## 4. 规则引擎实现

### 4.1 规则解析器
```python
class RuleExpressionParser:
    """规则表达式解析器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.supported_operators = {
            'string': ['equals', 'contains', 'startsWith', 'endsWith', 'regex', 'in', 'notIn'],
            'number': ['equals', 'gt', 'gte', 'lt', 'lte', 'between'],
            'boolean': ['equals'],
            'array': ['contains', 'in', 'notIn', 'isEmpty', 'hasLength']
        }
    
    def parse(self, rule_expression: dict) -> ParsedRule:
        """解析规则表达式"""
        try:
            return self._parse_group(rule_expression)
        except Exception as e:
            self.logger.error(f"规则解析失败: {str(e)}")
            raise RuleParseError(f"规则解析失败: {str(e)}")
    
    def _parse_group(self, group: dict) -> ParsedGroup:
        """解析规则组"""
        operator = group.get('operator', 'AND')
        conditions = []
        nested_groups = []
        
        # 解析条件
        for condition in group.get('conditions', []):
            parsed_condition = self._parse_condition(condition)
            conditions.append(parsed_condition)
        
        # 解析嵌套组
        for nested_group in group.get('groups', []):
            parsed_group = self._parse_group(nested_group)
            nested_groups.append(parsed_group)
        
        return ParsedGroup(
            operator=operator,
            conditions=conditions,
            groups=nested_groups
        )
    
    def _parse_condition(self, condition: dict) -> ParsedCondition:
        """解析单个条件"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        data_type = condition.get('type', 'string')
        
        # 验证操作符
        if operator not in self.supported_operators.get(data_type, []):
            raise RuleParseError(f"不支持的操作符 {operator} 用于类型 {data_type}")
        
        return ParsedCondition(
            field=field,
            operator=operator,
            value=value,
            data_type=data_type
        )
```

### 4.2 条件评估器
```python
class ConditionEvaluator:
    """条件评估器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.evaluators = {
            'equals': self._evaluate_equals,
            'contains': self._evaluate_contains,
            'startsWith': self._evaluate_starts_with,
            'endsWith': self._evaluate_ends_with,
            'regex': self._evaluate_regex,
            'in': self._evaluate_in,
            'notIn': self._evaluate_not_in,
            'gt': self._evaluate_greater_than,
            'gte': self._evaluate_greater_than_equal,
            'lt': self._evaluate_less_than,
            'lte': self._evaluate_less_than_equal,
            'between': self._evaluate_between
        }
    
    def evaluate(self, condition: ParsedCondition, account_data: dict) -> bool:
        """评估单个条件"""
        try:
            field_value = self._get_field_value(account_data, condition.field)
            evaluator = self.evaluators.get(condition.operator)
            
            if not evaluator:
                raise ValueError(f"未知的操作符: {condition.operator}")
            
            return evaluator(field_value, condition.value, condition.data_type)
        except Exception as e:
            self.logger.error(f"条件评估失败: {str(e)}")
            return False
    
    def _get_field_value(self, data: dict, field_path: str) -> any:
        """获取字段值，支持嵌套路径"""
        try:
            keys = field_path.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        except Exception:
            return None
    
    def _evaluate_equals(self, field_value: any, expected_value: any, data_type: str) -> bool:
        """精确匹配"""
        if field_value is None:
            return expected_value is None
        return str(field_value).lower() == str(expected_value).lower()
    
    def _evaluate_contains(self, field_value: any, expected_value: any, data_type: str) -> bool:
        """包含匹配"""
        if field_value is None:
            return False
        if data_type == 'array' and isinstance(field_value, (list, tuple)):
            return expected_value in field_value
        return str(expected_value).lower() in str(field_value).lower()
    
    def _evaluate_regex(self, field_value: any, pattern: str, data_type: str) -> bool:
        """正则表达式匹配"""
        if field_value is None:
            return False
        try:
            import re
            return bool(re.search(pattern, str(field_value), re.IGNORECASE))
        except re.error:
            return False
```

### 4.3 规则引擎核心
```python
class ClassificationRuleEngine:
    """分类规则引擎"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.parser = RuleExpressionParser()
        self.evaluator = ConditionEvaluator()
        self.cache_manager = cache_manager
    
    def evaluate_rules(self, account_data: dict, rules: List[ClassificationRule]) -> Optional[ClassificationRule]:
        """评估规则，返回匹配的最高优先级规则"""
        # 按优先级排序规则
        sorted_rules = sorted(rules, key=lambda r: r.priority or 0, reverse=True)
        
        for rule in sorted_rules:
            if self.evaluate_single_rule(account_data, rule):
                return rule
        
        return None
    
    def evaluate_single_rule(self, account_data: dict, rule: ClassificationRule) -> bool:
        """评估单个规则"""
        try:
            # 检查缓存
            cache_key = self._generate_cache_key(account_data, rule)
            cached_result = self.cache_manager.get_rule_evaluation_cache(
                rule.id, account_data.get('id')
            )
            
            if cached_result is not None:
                return cached_result
            
            # 解析规则表达式
            parsed_rule = self.parser.parse(rule.get_rule_expression())
            
            # 评估规则
            result = self._evaluate_parsed_rule(account_data, parsed_rule)
            
            # 缓存结果
            self.cache_manager.set_rule_evaluation_cache(
                rule.id, account_data.get('id'), result
            )
            
            return result
        except Exception as e:
            self.logger.error(f"规则评估失败: rule_id={rule.id}, error={str(e)}")
            return False
    
    def _evaluate_parsed_rule(self, account_data: dict, parsed_rule: ParsedGroup) -> bool:
        """评估已解析的规则"""
        condition_results = []
        group_results = []
        
        # 评估所有条件
        for condition in parsed_rule.conditions:
            result = self.evaluator.evaluate(condition, account_data)
            condition_results.append(result)
        
        # 评估所有嵌套组
        for group in parsed_rule.groups:
            result = self._evaluate_parsed_rule(account_data, group)
            group_results.append(result)
        
        # 合并所有结果
        all_results = condition_results + group_results
        
        if not all_results:
            return True  # 空规则默认匹配
        
        # 根据操作符计算最终结果
        if parsed_rule.operator == 'AND':
            return all(all_results)
        elif parsed_rule.operator == 'OR':
            return any(all_results)
        elif parsed_rule.operator == 'NOT':
            return not any(all_results)
        else:
            return False
```

### 3.3 关键JavaScript函数

#### 3.3.1 规则管理函数
```javascript
// 加载规则列表
function loadRules() {
    fetch('/account-classification/api/rules')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderRules(data.data);
            } else {
                showAlert('加载规则失败: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('加载规则失败', 'danger');
        });
}

// 创建规则
function createRule() {
    const formData = new FormData(document.getElementById('ruleForm'));
    
    fetch('/account-classification/api/rules', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('规则创建成功', 'success');
            $('#createRuleModal').modal('hide');
            loadRules();
        } else {
            showAlert('创建失败: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('创建失败', 'danger');
    });
}

// 编辑规则
function editRule(id) {
    fetch(`/account-classification/api/rules/${id}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateRuleForm(data.data);
                $('#editRuleModal').modal('show');
            } else {
                showAlert('加载规则失败: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('加载规则失败', 'danger');
        });
}

// 删除规则
function deleteRule(id) {
    if (!confirm('确定要删除这个规则吗？')) {
        return;
    }
    
    fetch(`/account-classification/api/rules/${id}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('规则删除成功', 'success');
            loadRules();
        } else {
            showAlert('删除失败: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('删除失败', 'danger');
    });
}
```

#### 3.3.2 规则测试函数
```javascript
// 测试规则
function testRule(ruleId) {
    showLoading('正在测试规则...');
    
    fetch(`/account-classification/api/rules/${ruleId}/test`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showTestResults(data.data);
        } else {
            showAlert('规则测试失败: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        showAlert('规则测试失败', 'danger');
    });
}

// 显示测试结果
function showTestResults(results) {
    const modal = new bootstrap.Modal(document.getElementById('testResultsModal'));
    const modalBody = document.getElementById('testResultsBody');
    
    modalBody.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>匹配的账户</h6>
                <div class="list-group">
                    ${results.matched_accounts.map(account => `
                        <div class="list-group-item">
                            <strong>${account.username}</strong>
                            <small class="text-muted d-block">${account.instance_name}</small>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="col-md-6">
                <h6>统计信息</h6>
                <ul class="list-unstyled">
                    <li>总账户数: ${results.total_accounts}</li>
                    <li>匹配账户数: ${results.matched_count}</li>
                    <li>匹配率: ${results.match_rate}%</li>
                </ul>
            </div>
        </div>
    `;
    
    modal.show();
}
```

### 3.4 样式设计

#### 3.4.1 规则卡片样式
```css
.rule-card {
    transition: all 0.3s ease;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    background: #fff;
    position: relative;
    overflow: hidden;
    margin-bottom: 0;
}

.rule-card:hover {
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
    border-color: #007bff;
}

.rule-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #007bff, #6f42c1);
    opacity: 0;
    transition: opacity 0.3s ease;
}

.rule-card:hover::before {
    opacity: 1;
}
```

#### 3.4.2 规则操作按钮样式
```css
.rule-actions {
    display: flex;
    gap: 0.15rem;
    flex-wrap: nowrap;
    justify-content: flex-end;
}

.rule-actions .btn {
    width: 28px;
    height: 28px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s ease;
    border: 1px solid #dee2e6;
    font-size: 0.75rem;
}

.rule-actions .btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
```

## 4. 后端实现

### 4.1 路由控制器
**文件**：`app/routes/account_classification.py`

#### 4.1.1 规则管理API
```python
@account_classification_bp.route("/api/rules", methods=["GET"])
@login_required
@view_required
def get_rules() -> Response:
    """获取规则列表"""
    try:
        rules = ClassificationRule.query.filter_by(is_active=True).all()
        return jsonify({
            "success": True,
            "data": [rule.to_dict() for rule in rules]
        })
    except Exception as e:
        log_error(f"获取规则列表失败: {str(e)}", module="account_classification")
        return jsonify({
            "success": False,
            "message": "获取规则列表失败"
        }), 500

@account_classification_bp.route("/api/rules", methods=["POST"])
@login_required
@create_required
def create_rule() -> Response:
    """创建规则"""
    try:
        data = request.get_json()
        
        rule = ClassificationRule(
            classification_id=data.get('classification_id'),
            db_type=data.get('db_type'),
            rule_name=data.get('rule_name'),
            rule_expression=data.get('rule_expression')
        )
        
        db.session.add(rule)
        db.session.commit()
        
        log_info(f"创建规则成功: {rule.rule_name}", module="account_classification")
        
        return jsonify({
            "success": True,
            "data": rule.to_dict(),
            "message": "规则创建成功"
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"创建规则失败: {str(e)}", module="account_classification")
        return jsonify({
            "success": False,
            "message": "创建规则失败"
        }), 500

@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["GET"])
@login_required
@view_required
def get_rule(rule_id: int) -> Response:
    """获取单个规则"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)
        return jsonify({
            "success": True,
            "data": rule.to_dict()
        })
    except Exception as e:
        log_error(f"获取规则失败: {str(e)}", module="account_classification")
        return jsonify({
            "success": False,
            "message": "获取规则失败"
        }), 500

@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["PUT"])
@login_required
@update_required
def update_rule(rule_id: int) -> Response:
    """更新规则"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)
        data = request.get_json()
        
        rule.rule_name = data.get('rule_name', rule.rule_name)
        rule.rule_expression = data.get('rule_expression', rule.rule_expression)
        rule.updated_at = now()
        
        db.session.commit()
        
        log_info(f"更新规则成功: {rule.rule_name}", module="account_classification")
        
        return jsonify({
            "success": True,
            "data": rule.to_dict(),
            "message": "规则更新成功"
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"更新规则失败: {str(e)}", module="account_classification")
        return jsonify({
            "success": False,
            "message": "更新规则失败"
        }), 500

@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["DELETE"])
@login_required
@delete_required
def delete_rule(rule_id: int) -> Response:
    """删除规则"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)
        
        db.session.delete(rule)
        db.session.commit()
        
        log_info(f"删除规则成功: {rule.rule_name}", module="account_classification")
        
        return jsonify({
            "success": True,
            "message": "规则删除成功"
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"删除规则失败: {str(e)}", module="account_classification")
        return jsonify({
            "success": False,
            "message": "删除规则失败"
        }), 500
```

## 5. 数据模型设计

### 5.1 规则模型
```python
class ClassificationRule(db.Model):
    """分类规则模型"""
    
    __tablename__ = "classification_rules"
    
    id = db.Column(db.Integer, primary_key=True)
    classification_id = db.Column(db.Integer, db.ForeignKey("account_classifications.id"), nullable=False)
    db_type = db.Column(db.String(20), nullable=False)  # mysql, postgresql, sqlserver, oracle
    rule_name = db.Column(db.String(100), nullable=False)  # 规则名称
    description = db.Column(db.Text)  # 规则描述
    rule_expression = db.Column(db.Text, nullable=False)  # 规则表达式（JSON格式）
    priority = db.Column(db.Integer, default=0)  # 优先级，数值越大优先级越高
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # 统计字段
    match_count = db.Column(db.Integer, default=0)  # 匹配次数
    last_matched_at = db.Column(db.DateTime(timezone=True))  # 最后匹配时间
    evaluation_count = db.Column(db.Integer, default=0)  # 评估次数
    
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    
    # 关联关系
    classification = db.relationship("AccountClassification", backref="rules")
    
    def __repr__(self) -> str:
        return f"<ClassificationRule {self.rule_name} for {self.db_type}>"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "classification_id": self.classification_id,
            "db_type": self.db_type,
            "rule_name": self.rule_name,
            "description": self.description,
            "rule_expression": self.rule_expression,
            "priority": self.priority,
            "is_active": self.is_active,
            "match_count": self.match_count,
            "evaluation_count": self.evaluation_count,
            "last_matched_at": self.last_matched_at.isoformat() if self.last_matched_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def get_rule_expression(self) -> dict:
        """获取规则表达式（解析JSON）"""
        try:
            return json.loads(self.rule_expression)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_rule_expression(self, expression: dict) -> None:
        """设置规则表达式（保存为JSON）"""
        self.rule_expression = json.dumps(expression, ensure_ascii=False)
    
    def increment_match_count(self) -> None:
        """增加匹配次数"""
        self.match_count = (self.match_count or 0) + 1
        self.last_matched_at = now()
    
    def increment_evaluation_count(self) -> None:
        """增加评估次数"""
        self.evaluation_count = (self.evaluation_count or 0) + 1
```

### 4.3 服务层

#### 4.3.1 规则服务
```python
class RuleService:
    """规则服务"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.cache_manager = cache_manager
    
    def get_all_rules(self) -> List[ClassificationRule]:
        """获取所有规则"""
        return ClassificationRule.query.filter_by(is_active=True).all()
    
    def create_rule(self, classification_id: int, db_type: str, 
                   rule_name: str, rule_expression: dict) -> ClassificationRule:
        """创建规则"""
        rule = ClassificationRule(
            classification_id=classification_id,
            db_type=db_type,
            rule_name=rule_name,
            rule_expression=rule_expression
        )
        db.session.add(rule)
        db.session.commit()
        return rule
    
    def evaluate_rule(self, rule: ClassificationRule, rule_expression: dict) -> List[dict]:
        """评估规则"""
        try:
            # 获取规则对应的账户数据
            accounts = self._get_accounts_by_db_type(rule.db_type)
            
            matched_accounts = []
            for account in accounts:
                if self._evaluate_account_against_rule(account, rule_expression):
                    matched_accounts.append(account.to_dict())
            
            return matched_accounts
        except Exception as e:
            self.logger.error(f"规则评估失败: {str(e)}")
            return []
    
    def _get_accounts_by_db_type(self, db_type: str) -> List[CurrentAccountSyncData]:
        """根据数据库类型获取账户"""
        # 这里需要根据实际的数据库结构来实现
        # 假设通过实例关联来获取账户
        return CurrentAccountSyncData.query.join(Instance).filter(
            Instance.db_type == db_type
        ).all()
    
    def _evaluate_account_against_rule(self, account: CurrentAccountSyncData, 
                                     rule_expression: dict) -> bool:
        """评估单个账户是否符合规则"""
        try:
            # 实现规则评估逻辑
            # 这里需要根据规则表达式的结构来实现具体的匹配逻辑
            return self._match_rule_conditions(account, rule_expression)
        except Exception as e:
            self.logger.error(f"账户规则评估失败: {str(e)}")
            return False
    
    def _match_rule_conditions(self, account: CurrentAccountSyncData, 
                              conditions: dict) -> bool:
        """匹配规则条件"""
        # 实现具体的条件匹配逻辑
        # 支持多种匹配模式：精确匹配、正则表达式、包含匹配等
        pass
```

#### 4.3.2 缓存管理服务
```python
class CacheManager:
    """缓存管理器"""
    
    def get_rule_evaluation_cache(self, rule_id: int, account_id: int) -> bool | None:
        """获取规则评估缓存"""
        try:
            if not self.cache:
                return None
                
            cache_key = self._generate_cache_key("rule_eval", rule_id, account_id, "")
            cached_data = self.cache.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                return data.get("result")
            
            return None
        except Exception as e:
            logger.warning("获取规则评估缓存失败: rule_id=%s, account_id=%s", rule_id, account_id, error=str(e))
            return None
    
    def set_rule_evaluation_cache(self, rule_id: int, account_id: int, 
                                 result: bool, ttl: int = None) -> bool:
        """设置规则评估缓存"""
        try:
            if not self.cache:
                return False
                
            cache_key = self._generate_cache_key("rule_eval", rule_id, account_id, "")
            cache_data = {
                "result": result,
                "cached_at": datetime.now(tz=timezone.utc).isoformat(),
                "rule_id": rule_id,
                "account_id": account_id,
            }
            
            ttl = ttl or (24 * 3600)  # 规则评估缓存1天
            self.cache.set(cache_key, cache_data, timeout=ttl)
            return True
        except Exception as e:
            logger.warning("设置规则评估缓存失败: rule_id=%s, account_id=%s", rule_id, account_id, error=str(e))
            return False
```

## 5. 数据库设计

### 5.1 表结构

#### 5.1.1 分类规则表 (classification_rules)
```sql
CREATE TABLE classification_rules (
    id SERIAL PRIMARY KEY,
    classification_id INTEGER NOT NULL REFERENCES account_classifications(id),
    db_type VARCHAR(20) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_expression TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 5.1.2 账户分类表 (account_classifications)
```sql
CREATE TABLE account_classifications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    color VARCHAR(20),
    icon_name VARCHAR(50) DEFAULT 'fa-tag',
    priority INTEGER DEFAULT 0,
    is_system BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.2 索引设计
```sql
-- 规则表索引
CREATE INDEX idx_classification_rules_classification_id ON classification_rules(classification_id);
CREATE INDEX idx_classification_rules_db_type ON classification_rules(db_type);
CREATE INDEX idx_classification_rules_active ON classification_rules(is_active);

-- 分类表索引
CREATE INDEX idx_account_classifications_name ON account_classifications(name);
CREATE INDEX idx_account_classifications_active ON account_classifications(is_active);
```

## 6. 规则引擎性能优化

### 6.1 缓存策略
- **规则解析缓存**：缓存已解析的规则表达式，避免重复解析
- **评估结果缓存**：缓存账户规则评估结果，设置合理的TTL
- **分层缓存**：本地缓存 + Redis分布式缓存
- **缓存预热**：系统启动时预加载常用规则

### 6.2 性能监控
```python
class RuleEngineMetrics:
    """规则引擎性能指标"""
    
    def __init__(self):
        self.execution_times = []
        self.cache_hit_rate = 0.0
        self.error_rate = 0.0
    
    def record_execution_time(self, rule_id: int, execution_time: float):
        """记录规则执行时间"""
        pass
    
    def get_performance_stats(self) -> dict:
        """获取性能统计"""
        return {
            "avg_execution_time": sum(self.execution_times) / len(self.execution_times),
            "cache_hit_rate": self.cache_hit_rate,
            "error_rate": self.error_rate
        }
```

### 6.3 规则优化建议
- 将高频匹配的条件放在前面
- 避免复杂的正则表达式
- 合理设置规则优先级
- 定期清理无效规则

## 7. 规则调试和测试

### 7.1 规则调试器
```python
class RuleDebugger:
    """规则调试器"""
    
    def debug_rule(self, rule: ClassificationRule, account_data: dict) -> dict:
        """调试单个规则"""
        debug_info = {
            "rule_info": rule.to_dict(),
            "account_data": account_data,
            "execution_steps": [],
            "final_result": False,
            "execution_time": 0
        }
        
        start_time = time.time()
        try:
            # 逐步执行规则并记录每一步
            parsed_rule = self.parser.parse(rule.get_rule_expression())
            debug_info["execution_steps"].append({
                "step": "rule_parsing",
                "result": "success",
                "data": parsed_rule.to_dict()
            })
            
            # 执行条件评估
            result = self.engine._evaluate_parsed_rule(account_data, parsed_rule)
            debug_info["final_result"] = result
            
        except Exception as e:
            debug_info["execution_steps"].append({
                "step": "execution_error",
                "result": "error",
                "error": str(e)
            })
        
        debug_info["execution_time"] = (time.time() - start_time) * 1000
        return debug_info
```

### 7.2 规则测试框架
```python
class RuleTestFramework:
    """规则测试框架"""
    
    def create_test_case(self, rule: ClassificationRule, account_data: dict, 
                        expected_result: bool) -> dict:
        """创建测试用例"""
        return {
            "rule_id": rule.id,
            "rule_name": rule.rule_name,
            "account_data": account_data,
            "expected_result": expected_result,
            "created_at": datetime.now()
        }
    
    def run_test_suite(self, test_cases: List[dict]) -> dict:
        """运行测试套件"""
        results = {
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        for test_case in test_cases:
            result = self.run_single_test(test_case)
            results["details"].append(result)
            if result["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1
        
        return results
```

## 8. 错误处理和异常管理

### 8.1 自定义异常类
```python
class RuleEngineError(Exception):
    """规则引擎基础异常"""
    pass

class RuleParseError(RuleEngineError):
    """规则解析异常"""
    pass

class RuleEvaluationError(RuleEngineError):
    """规则评估异常"""
    pass

class RuleCacheError(RuleEngineError):
    """规则缓存异常"""
    pass
```

### 8.2 错误处理策略
- **优雅降级**：规则解析失败时使用默认分类
- **错误隔离**：单个规则错误不影响其他规则执行
- **错误重试**：对于临时性错误实施重试机制
- **错误监控**：实时监控规则执行错误率

## 9. 扩展指南

### 9.1 添加新的匹配操作符
1. 在 `ConditionEvaluator` 中添加新的评估方法
2. 在 `RuleExpressionParser` 中注册新操作符
3. 更新前端规则编辑器支持新操作符
4. 添加相应的测试用例

### 9.2 支持新的数据库类型
1. 扩展数据库类型枚举
2. 实现对应的数据适配器
3. 更新规则表达式字段映射
4. 添加数据库特定的优化策略

### 9.3 集成机器学习
1. 收集规则执行历史数据
2. 训练规则优化模型
3. 实现智能规则推荐
4. 自动调优规则优先级

## 10. 监控和运维

### 10.1 关键指标监控
- 规则执行成功率
- 平均执行时间
- 缓存命中率
- 规则匹配分布

### 10.2 告警配置
- 规则执行错误率超阈值
- 执行时间异常
- 缓存失效率过高
- 规则冲突频繁

---

**文档版本**：1.0.0  
**最后更新**：2025-01-28  
**维护人员**：开发团队
