# 请求校验与参数统一方案

## 目标
- 统一使用 `app/utils/data_validator.py` 进行严格的领域数据校验
- 使用 `app/utils/decorators.py` 中的 `validate_json(required_fields=[...])` 作为 JSON 接口的必填字段检查
- 统一查询参数命名模式：`q`、`sort_by`、`order`、`page`、`per_page`
- 统一错误处理机制，通过异常抛出交由全局错误处理器处理

## 当前实现状态（2025-10-17）

### 装饰器实现
- ✅ `validate_json(required_fields=[...])` 已完整实现
  - 检查请求是否为JSON格式
  - 验证JSON数据是否为空
  - 检查必填字段是否存在
  - 失败时抛出 `ValidationError` 异常，由全局错误处理器统一处理
- ✅ `login_required_json` 已实现，抛出 `AuthenticationError` 异常
- ✅ 权限相关装饰器已完善，支持JSON和表单两种响应模式

### 数据校验器实现
- ✅ `DataValidator` 已完整实现，提供严格的领域数据校验
  - 支持实例数据验证：`validate_instance_data()`
  - 支持批量数据验证：`validate_batch_data()`
  - 提供数据清理功能：`sanitize_input()`
  - 已在 `instances.py` 路由中广泛使用
- ❌ `InputValidator` 通用校验器未实现（文档中提到但代码中不存在）

### 错误处理机制
- ✅ 全局错误处理器已实现，统一返回格式：`{"error": message, "status_code": code, "timestamp": ...}`
- ✅ 自定义异常类已实现：`ValidationError`、`AuthenticationError`、`AuthorizationError`
- ✅ 路由中已开始使用异常抛出机制替代内联JSON返回

### 查询参数统一状态
- ✅ 分页参数已基本统一：`page`、`per_page`
- ✅ 搜索参数部分统一：`logs.py` 使用 `q`，其他路由多使用 `search`
- ⚠️ 默认值存在差异：
  - `per_page` 默认值：10（instances, credentials, users）、20（account, tags, sync_sessions）、50（logs）
  - 需要统一为20，最大值100
- ✅ 路径参数命名已规范：`<int:instance_id>`、`<int:credential_id>` 等

## 统一参数命名规范

### 查询参数
- **搜索关键字**：`q`（推荐）或 `search`（兼容现有）
- **排序参数**：`sort_by`、`order`（asc/desc）
- **分页参数**：`page`（默认1）、`per_page`（默认20，最大100）
- **筛选参数**：`status`、`type`、`category` 等

### 路径参数
- **实例相关**：`<int:instance_id>`
- **凭据相关**：`<int:credential_id>`
- **账户相关**：`<int:account_id>`
- **用户相关**：`<int:user_id>`

## 统一校验与返回机制

### JSON接口校验
- ✅ 使用 `@validate_json(required_fields=[...])` 装饰器
  - 自动检查 `Content-Type` 为 `application/json`
  - 验证JSON数据存在且不为空
  - 检查必填字段完整性
  - 失败时抛出 `ValidationError` 异常

### 数据校验层次
1. **基础校验**：`@validate_json` 装饰器（必填字段、JSON格式）
2. **领域校验**：`DataValidator.validate_instance_data()` 等（业务规则）
3. **数据清理**：`DataValidator.sanitize_input()` （去除空格、类型转换）

### 错误处理流程
```python
# 1. 装饰器校验失败 → ValidationError → 全局错误处理器
# 2. 业务校验失败 → ValidationError → 全局错误处理器  
# 3. 统一返回格式：{"error": message, "status_code": 400, "timestamp": "..."}
```

## 代码示例

### 标准JSON接口实现（当前最佳实践）
```python
from flask import request
from app.utils.decorators import validate_json, view_required
from app.utils.data_validator import DataValidator
from app.errors import ValidationError
from app.utils.response_utils import jsonify_unified_success

@validate_json(required_fields=["name", "db_type", "host", "port"])
@view_required
def create_instance_api():
    """创建实例API - 标准实现"""
    # 装饰器已确保JSON格式和必填字段存在
    data = request.get_json()
    
    # 数据清理
    data = DataValidator.sanitize_input(data)
    
    # 严格领域校验
    is_valid, error_msg = DataValidator.validate_instance_data(data)
    if not is_valid:
        raise ValidationError(error_msg)  # 抛出异常，由全局错误处理器处理
    
    # 执行业务逻辑
    # ... 创建实例逻辑 ...
    
    return jsonify_unified_success(message="实例创建成功")
```

### 查询参数处理示例
```python
from flask import request

@view_required
def list_instances_api():
    """实例列表API - 统一参数处理"""
    # 分页参数（统一默认值）
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)  # 统一默认20，最大100
    
    # 搜索参数（兼容两种命名）
    search = request.args.get("q", request.args.get("search", "")).strip()
    
    # 排序参数
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")
    
    # 筛选参数
    db_type = request.args.get("db_type", "")
    status = request.args.get("status", "")
    
    # 参数验证
    if page < 1:
        raise ValidationError("页码必须大于0")
    if order not in ["asc", "desc"]:
        raise ValidationError("排序方向只能是asc或desc")
    
    # ... 执行查询逻辑 ...
```

## 校验装饰器详解

### 已实现的装饰器
- ✅ `@validate_json(required_fields=[...])` - JSON数据和必填字段校验
- ✅ `@login_required_json` - JSON API登录校验  
- ✅ `@view_required`、`@create_required`、`@update_required`、`@delete_required` - 权限校验
- ✅ `@admin_required` - 管理员权限校验

### 规划中的装饰器（未实现）
- ❌ `@validate_json_types(types={...})` - 字段类型校验
- ❌ `@validate_query(spec={...})` - 查询参数契约式校验

## 数据校验器使用指南

### DataValidator（已实现）
- **用途**：严格的领域数据校验
- **方法**：
  - `validate_instance_data(data)` - 实例数据校验
  - `validate_batch_data(data_list)` - 批量数据校验  
  - `sanitize_input(data)` - 数据清理
- **使用场景**：实例创建/编辑、批量导入等

### 表单数据处理
- 使用 `app/utils/security.py` 中的工具：
  - `sanitize_form_data()` - 表单数据清理
  - `validate_required_fields()` - 必填字段检查

## 错误处理统一机制

### 当前实现
- ✅ 全局错误处理器统一返回格式
- ✅ 自定义异常类支持结构化错误信息
- ✅ 路由中使用异常抛出替代内联JSON返回

### 统一错误格式
```json
{
  "error": "错误描述信息",
  "status_code": 400,
  "timestamp": "2025-10-17T14:30:00+08:00"
}
```

## 迁移计划

### 已完成的工作 ✅
1. **核心基础设施**
   - `@validate_json` 装饰器完整实现
   - `DataValidator` 领域校验器完整实现
   - 全局错误处理器和自定义异常类
   - `instances.py` 路由已完全迁移到新的校验机制

2. **部分完成的工作** ⚠️
   - 查询参数基本统一（`page`、`per_page`）
   - 部分路由使用异常抛出机制

### 待完成的工作 ❌
1. **查询参数统一**
   - 统一 `per_page` 默认值为20（当前10/20/50混用）
   - 统一搜索参数为 `q`（当前 `search` 和 `q` 混用）
   - 添加 `per_page` 最大值100的限制

2. **装饰器应用**
   - 为所有JSON写接口添加 `@validate_json` 装饰器
   - 检查并补充遗漏的权限装饰器

3. **错误处理迁移**
   - 将剩余的内联 `jsonify({"error": "..."})` 替换为异常抛出
   - 统一所有API的错误返回格式

## 验收标准

### 功能验收
- [ ] 所有JSON写接口都有 `@validate_json` 装饰器保护
- [ ] 所有列表接口使用统一的查询参数命名和默认值
- [ ] 所有API错误都通过全局错误处理器返回统一格式
- [ ] `DataValidator` 在所有需要领域校验的地方被正确使用

### 性能验收
- [ ] 校验逻辑不影响API响应时间
- [ ] 错误处理不产生额外的性能开销

### 兼容性验收
- [ ] 前端现有调用不受影响
- [ ] 错误信息对用户友好且便于调试

## 风险控制

### 主要风险
1. **前端兼容性**：参数名称变更可能影响前端调用
2. **错误格式变更**：可能影响前端错误处理逻辑
3. **默认值变更**：可能影响分页显示效果

### 缓解措施
1. **渐进式迁移**：保持向后兼容，逐步迁移
2. **双参数支持**：同时支持新旧参数名称
3. **充分测试**：确保每个变更都经过测试验证

## 涉及文件清单

### 核心文件
- `app/utils/decorators.py` - 校验装饰器
- `app/utils/data_validator.py` - 数据校验器
- `app/utils/error_handler.py` - 全局错误处理
- `app/errors.py` - 自定义异常类

### 路由文件（需要检查和统一）
- `app/routes/instances.py` ✅ 已完成
- `app/routes/credentials.py` ⚠️ 需要检查
- `app/routes/account.py` ⚠️ 需要检查  
- `app/routes/logs.py` ⚠️ 需要检查
- `app/routes/users.py` ⚠️ 需要检查
- 其他路由文件...