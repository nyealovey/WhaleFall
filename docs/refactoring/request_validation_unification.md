# 请求校验与参数统一方案

本方案旨在统一现有的请求校验机制，规范化查询参数命名和默认值，消除代码重复，提高系统安全性和可维护性。不新增复杂功能，专注于整合和优化现有验证体系。

## 1. 目标与策略

### 核心目标
1. **统一查询参数**：规范化参数命名和默认值（per_page=20，兼容q/search）
2. **补充装饰器**：确保所有接口有适当的验证装饰器
3. **增强安全验证**：提升密码强度（8位+大小写+数字）和IP地址验证（检查私有IP）
4. **统一错误处理**：使用异常抛出替代内联错误返回

### 实施策略
- 保持现有架构不变，避免大规模重构
- 分3个阶段实施：查询参数 → 装饰器 → 安全增强
- 保持向后兼容，渐进式迁移
- 每个阶段独立测试和验证

## 2. 现有基础设施评估

### 已实现的验证层次

#### 装饰器层 (`app/utils/decorators.py`)
- ✅ `@validate_json(required_fields=[...])` - JSON格式和必填字段校验
- ✅ `@login_required` / `@login_required_json` - 登录验证
- ✅ `@admin_required` - 管理员权限验证
- ✅ `@permission_required(permission)` - 通用权限验证
- ✅ `@view_required` / `@create_required` / `@update_required` / `@delete_required` - CRUD权限
- ⚠️ `@rate_limit(requests_per_minute)` - 速率限制（空实现）

#### 数据验证层 (`app/utils/data_validator.py`)
- ✅ `DataValidator.validate_instance_data(data)` - 实例数据验证
- ✅ `DataValidator.validate_batch_data(data_list)` - 批量数据验证
- ✅ `DataValidator.sanitize_input(data)` - 数据清理

#### 输入验证层 (`app/utils/validation.py`)
- ✅ `InputValidator.validate_string()` - 字符串验证
- ✅ `InputValidator.validate_integer()` - 整数验证
- ✅ `InputValidator.validate_boolean()` - 布尔值验证
- ✅ `InputValidator.validate_email()` - 邮箱验证
- ✅ `InputValidator.validate_pagination()` - 分页参数验证
- ✅ `InputValidator.sanitize_html()` - HTML清理
- ✅ `InputValidator.validate_sql_query()` - SQL安全检查

#### 安全验证层 (`app/utils/security.py`)
- ✅ `validate_username()` - 用户名格式验证
- ⚠️ `validate_password()` - 密码验证（强度太弱，只检查长度>=6）
- ✅ `sanitize_input()` - XSS防护
- ✅ `check_sql_injection()` - SQL注入检查

#### 异常处理层 (`app/errors/__init__.py`)
- ✅ `ValidationError` - 验证错误 (400)
- ✅ `AuthenticationError` - 认证错误 (401)
- ✅ `AuthorizationError` - 授权错误 (403)
- ✅ `NotFoundError` - 资源不存在 (404)
- ✅ `ConflictError` - 冲突错误 (409)
- ✅ `DatabaseError` - 数据库错误 (500)
- ✅ `RateLimitError` - 速率限制错误 (429)

### 评分：⭐⭐⭐⭐ (4/5)
**结论**：验证体系已经很完善，主要缺口是安全性相关（密码强度、IP验证）和参数统一性。

## 3. 不一致问题识别

### 查询参数不统一

#### per_page 默认值不一致
| 路由文件 | 当前默认值 | 目标默认值 | 状态 |
|---------|-----------|-----------|------|
| `instances.py` | 10 | 20 | ⚠️ 需修改 |
| `credentials.py` | 10 | 20 | ⚠️ 需修改 |
| `users.py` | 10 | 20 | ⚠️ 需修改 |
| `logs.py` | 50 | 20 | ⚠️ 需修改 |
| `account.py` | 20 | 20 | ✅ 已统一 |
| `tags.py` | 20 | 20 | ✅ 已统一 |
| `sync_sessions.py` | 20 | 20 | ✅ 已统一 |

#### 搜索参数命名不一致
| 路由文件 | 当前使用 | 目标使用 | 状态 |
|---------|---------|---------|------|
| `logs.py` | `q` | `q` | ✅ 已统一 |
| 其他路由 | `search` | `q` | ⚠️ 需兼容 |

### 装饰器使用不完整
- 部分JSON写接口缺少 `@validate_json` 装饰器
- 部分路由仍使用内联 `jsonify({"error": "..."})` 而非异常抛出

### 安全验证不足
- 密码强度验证太弱（只检查长度>=6）
- IP地址验证不检查私有IP、保留IP

## 4. 统一规范定义

### 查询参数标准
| 参数 | 用途 | 默认值 | 限制 | 说明 |
|------|------|--------|------|------|
| `q` | 搜索关键字 | `""` | - | 统一使用 `q`，兼容 `search` |
| `page` | 页码 | `1` | ≥ 1 | 从1开始 |
| `per_page` | 每页数量 | `20` | 1-100 | 统一默认20，最大100 |
| `sort_by` | 排序字段 | `created_at` | - | 根据业务调整 |
| `order` | 排序方向 | `desc` | asc/desc | 降序或升序 |
| `status` | 状态筛选 | `""` | - | 可选筛选 |
| `type` | 类型筛选 | `""` | - | 可选筛选 |

### 路径参数标准（已规范）
- `<int:instance_id>` - 实例ID
- `<int:credential_id>` - 凭据ID
- `<int:account_id>` - 账户ID
- `<int:user_id>` - 用户ID
- `<int:tag_id>` - 标签ID

### 装饰器使用规范
```python
# JSON写接口（POST/PUT/DELETE）
@validate_json(required_fields=["name", "host"])
@create_required
def create_api():
    pass

# 查询接口（GET）
@view_required
def list_api():
    pass
```

### 错误处理规范
```python
# ❌ 不要这样做
if not data:
    return jsonify({"error": "数据不能为空"}), 400

# ✅ 应该这样做
if not data:
    raise ValidationError("数据不能为空")
```


## 5. 安全增强方案

### 密码强度验证增强

**文件**: `app/utils/security.py`  
**修改**: 在 `validate_password()` 函数中添加参数

```python
def validate_password(
    password: str,
    min_length: int = 8,  # 从6提高到8
    require_uppercase: bool = True,  # 新增
    require_lowercase: bool = True,  # 新增
    require_digit: bool = True,  # 新增
    require_special: bool = False  # 新增（可选）
) -> str | None:
    """验证密码强度（增强版）"""
    if not password:
        return "密码不能为空"
    
    if len(password) < min_length:
        return f"密码长度至少{min_length}个字符"
    
    if len(password) > 128:
        return "密码长度不能超过128个字符"
    
    if require_uppercase and not re.search(r'[A-Z]', password):
        return "密码必须包含大写字母"
    
    if require_lowercase and not re.search(r'[a-z]', password):
        return "密码必须包含小写字母"
    
    if require_digit and not re.search(r'\d', password):
        return "密码必须包含数字"
    
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return "密码必须包含特殊字符"
    
    return None
```

### IP地址验证增强

**文件**: `app/utils/data_validator.py`  
**修改**: 在 `_is_valid_host()` 方法中使用 `ipaddress` 模块

```python
@classmethod
def _is_valid_host(
    cls,
    host: str,
    allow_private: bool = True,  # 新增
    allow_localhost: bool = True  # 新增
) -> Tuple[bool, Optional[str]]:
    """检查主机地址是否有效（增强版）"""
    import ipaddress
    
    # ... 基本检查 ...
    
    # 检查IP地址
    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', host):
        try:
            ip = ipaddress.ip_address(host)
            
            # 检查私有IP
            if not allow_private and ip.is_private:
                return False, "不允许使用私有IP地址"
            
            # 检查localhost
            if not allow_localhost and ip.is_loopback:
                return False, "不允许使用localhost地址"
            
            # 检查保留IP
            if ip.is_reserved:
                return False, "不允许使用保留IP地址"
            
            return True, None
        except ValueError:
            return False, "IP地址格式无效"
    
    # ... 域名检查 ...
```

## 6. 迁移步骤

### 阶段1：查询参数统一（优先级最高）

#### 步骤1.1：统一 per_page 默认值
```bash
# 需要修改的文件
- app/routes/instances.py
- app/routes/credentials.py
- app/routes/users.py
- app/routes/logs.py
```

**修改模板**：
```python
# ❌ 修改前
per_page = request.args.get("per_page", 10, type=int)  # 或 50

# ✅ 修改后
per_page = min(request.args.get("per_page", 20, type=int), 100)
```

#### 步骤1.2：统一搜索参数（兼容性处理）
```python
# ✅ 兼容新旧参数
q = request.args.get("q", request.args.get("search", "")).strip()
```

**注意**：保持向后兼容，同时支持 `q` 和 `search` 参数。

### 阶段2：安全验证增强（优先级高）

#### 步骤2.1：增强密码验证
1. 修改 `app/utils/security.py` 中的 `validate_password()` 函数
2. 更新所有调用该函数的地方，传入新参数
3. 测试用户注册、修改密码功能

#### 步骤2.2：增强IP验证
1. 修改 `app/utils/data_validator.py` 中的 `_is_valid_host()` 方法
2. 更新 `validate_instance_data()` 方法调用
3. 测试实例创建、编辑功能

### 阶段3：装饰器补充（优先级中）

#### 步骤3.1：补充 @validate_json 装饰器
```bash
# 扫描所有 POST/PUT/DELETE 接口
rg -n "@app.route.*methods=.*POST" app/routes/
rg -n "@app.route.*methods=.*PUT" app/routes/
rg -n "@app.route.*methods=.*DELETE" app/routes/
```

**检查清单**：
- [ ] 是否有 `@validate_json` 装饰器
- [ ] `required_fields` 列表是否完整
- [ ] 是否有权限装饰器

#### 步骤3.2：替换内联错误返回
```bash
# 搜索内联错误返回
rg -n 'jsonify\(\{"error"' app/routes/
rg -n 'return.*\{"error"' app/routes/
```

**替换模板**：
```python
# ❌ 修改前
if not data:
    return jsonify({"error": "数据不能为空"}), 400

# ✅ 修改后
if not data:
    raise ValidationError("数据不能为空")
```

### 阶段4：测试与验证

#### 单元测试
- `tests/unit/utils/test_security.py` - 测试密码强度验证
- `tests/unit/utils/test_data_validator.py` - 测试IP地址验证

#### 集成测试
- 测试用户注册（密码强度）
- 测试实例创建（IP验证）
- 测试分页功能（per_page统一）
- 测试搜索功能（q参数兼容）

## 7. 覆盖范围与检查清单

### 必查路径
- ✅ `app/routes/**` - 所有路由文件
- ✅ `app/utils/security.py` - 密码验证
- ✅ `app/utils/data_validator.py` - IP验证
- ✅ `app/utils/decorators.py` - 装饰器（无需修改）
- ✅ `app/utils/validation.py` - 输入验证（无需修改）

### 验收清单

#### 查询参数统一
- [ ] 所有列表接口的 `per_page` 默认值为20
- [ ] 所有列表接口的 `per_page` 最大值为100
- [ ] 所有搜索接口兼容 `q` 和 `search` 参数

#### 装饰器完整性
- [ ] 所有JSON写接口有 `@validate_json` 装饰器
- [ ] 所有接口有适当的权限装饰器
- [ ] 无内联 `jsonify({"error": ...})` 返回

#### 兼容性
- [ ] 前端现有调用不受影响
- [ ] 错误信息清晰友好
- [ ] 分页显示正常

## 8. 自动化辅助脚本

### 搜索需要修改的代码
```bash
# 搜索 per_page 默认值不是20的
rg -n 'per_page.*=.*request\.args\.get.*[^2]0' app/routes/

# 搜索只使用 search 参数的
rg -n 'request\.args\.get\("search"' app/routes/

# 搜索缺少 @validate_json 的 POST 接口
rg -n '@.*route.*POST' app/routes/ | while read line; do
    file=$(echo $line | cut -d: -f1)
    lineno=$(echo $line | cut -d: -f2)
    # 检查前5行是否有 @validate_json
    sed -n "$((lineno-5)),$((lineno))p" "$file" | grep -q "@validate_json" || echo "$line"
done

# 搜索内联错误返回
rg -n 'jsonify\(\{"error"' app/routes/
rg -n 'return.*\{"error"' app/routes/
```

### 批量修改脚本（需人工确认）
```bash
#!/usr/bin/env bash
# 统一 per_page 默认值为20

files=$(rg -l 'per_page.*=.*request\.args\.get.*10' app/routes/)
for f in $files; do
    echo "Processing $f"
    # 备份
    cp "$f" "$f.bak"
    # 替换
    sed -i 's/per_page.*=.*request\.args\.get("per_page", 10/per_page = min(request.args.get("per_page", 20/g' "$f"
done
```

**注意**：执行前务必备份或在单独分支操作。


## 9. 标准实现模板

### JSON写接口模板
```python
@validate_json(required_fields=["name", "host", "port"])
@create_required
def create_api():
    data = request.get_json()
    data = DataValidator.sanitize_input(data)
    
    is_valid, error_msg = DataValidator.validate_instance_data(data)
    if not is_valid:
        raise ValidationError(error_msg)
    
    # 业务逻辑...
    return jsonify_unified_success(data=result)
```

### 查询接口模板
```python
@view_required
def list_api():
    # 统一参数处理
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    q = request.args.get("q", request.args.get("search", "")).strip()
    
    # 参数验证
    if page < 1:
        raise ValidationError("页码必须大于0")
    
    # 查询逻辑...
    return jsonify_unified_success(data={"items": items, "pagination": {...}})
```

## 10. 测试与验证

### 测试重点
- 分页默认值统一（per_page=20）
- 搜索参数兼容（q 和 search）
- 装饰器完整性
- 错误处理统一

### 简单测试示例
```python
# 测试分页默认值
def test_pagination_defaults(client):
    response = client.get("/api/instances")
    assert response.json["pagination"]["per_page"] == 20

# 测试搜索兼容性
def test_search_compatibility(client):
    r1 = client.get("/api/instances?q=test")
    r2 = client.get("/api/instances?search=test")
    assert r1.json == r2.json
```

## 11. 验收指标

### 功能验收
- [ ] 所有列表接口的 `per_page` 默认值为20，最大值100
- [ ] 所有搜索接口兼容 `q` 和 `search` 参数
- [ ] 所有JSON写接口有 `@validate_json` 装饰器
- [ ] 所有错误通过异常抛出，无内联 `jsonify({"error": ...})`

### 性能验收
- [ ] 校验逻辑不影响API响应时间（增加<10ms）
- [ ] 错误处理不产生额外的性能开销

### 兼容性验收
- [ ] 前端现有调用不受影响
- [ ] 错误信息清晰友好
- [ ] 分页显示正常
- [ ] 搜索功能正常



## 12. 风险与回滚

### 主要风险

#### 风险1：参数变更影响前端
**影响**：前端可能依赖旧的默认值  
**概率**：中  
**缓解措施**：
- 保持向后兼容（同时支持 `q` 和 `search`）
- 提前通知前端团队
- 在测试环境充分验证

#### 风险2：密码强度提升影响现有用户
**影响**：现有弱密码用户无法修改密码  
**概率**：低  
**缓解措施**：
- 只对新密码应用新规则
- 现有密码不强制更新
- 提供密码强度提示

#### 风险3：IP验证过严影响正常使用
**影响**：合法的私有IP被拦截  
**概率**：中  
**缓解措施**：
- 默认允许私有IP和localhost
- 提供配置选项
- 记录详细的错误信息

### 回滚策略

#### 快速回滚
```bash
# 回滚到上一个版本
git revert <commit-hash>
git push origin main
```

#### 分阶段回滚
- 阶段1（查询参数）：独立提交，可单独回滚
- 阶段2（安全验证）：独立提交，可单独回滚
- 阶段3（装饰器）：独立提交，可单独回滚

#### 紧急修复
- 保留旧版本的 tag
- 准备热修复分支
- 监控错误日志和用户反馈

## 13. 实施计划

### 阶段1：查询参数统一（1-2天）
- [ ] 统一 per_page 默认值为20
- [ ] 兼容 q 和 search 参数
- [ ] 测试验证

### 阶段2：装饰器补充（1-2天）
- [ ] 补充缺失的 @validate_json
- [ ] 替换内联错误返回
- [ ] 测试验证

### 阶段3：安全增强（1-2天）
- [ ] 增强密码验证
- [ ] 增强IP验证
- [ ] 测试验证

## 附录：常见问题

### Q1：为什么不重构整合验证文件？
**A**：当前结构清晰，重构风险大收益小。

### Q2：为什么要兼容 search 参数？
**A**：保持向后兼容，避免影响前端。

### Q3：安全增强会影响现有功能吗？
**A**：不会。只对新密码和新实例应用新规则。

---

**文档版本**: 1.0  
**最后更新**: 2025-10-17  
**负责人**: 开发团队  
**审阅人**: 技术负责人
