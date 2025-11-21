# 鲸落项目编码规范

> 最后更新：2025-11-21  
> 基于项目实际代码库总结

## 1. 代码风格

### 1.1 基本规则

- **缩进**: 统一使用 4 个空格
- **行长度**: 单行不超过 120 个字符
- **编码**: UTF-8
- **换行符**: LF (Unix 风格)

### 1.2 格式化工具

项目使用以下工具保持代码风格一致：

```bash
# 代码格式化
make format

# 实际执行的命令
black .
isort .
```

**配置文件**: `pyproject.toml`

```toml
[tool.black]
line-length = 120
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 120
```

## 2. 命名规范

### 2.1 Python 命名

#### 模块和文件
- **规则**: `snake_case`，使用完整单词，禁止缩写
- **正确**: `database_aggregation.py`, `instance_service.py`
- **错误**: `db_aggr.py`, `inst_svc.py`

#### 类名
- **规则**: `CapWords` (PascalCase)
- **示例**: `DatabaseSizeAggregation`, `InstanceService`, `UserRole`

#### 函数和变量
- **规则**: `snake_case`
- **示例**: `get_user_list()`, `total_count`, `is_active`

#### 路由函数
- **规则**: 动词短语，禁止 `api_` 前缀或 `_api` 后缀
- **正确**: `list_users()`, `get_instance()`, `create_partition()`
- **错误**: `api_list_users()`, `get_instance_api()`, `users_list()`

#### 聚合函数
- **规则**: 使用单数形式，避免复数嵌套
- **正确**: `get_database_aggregations()`, `get_instance_aggregations()`
- **错误**: `get_databases_aggregations()`, `get_instances_aggregations()`

### 2.2 前端命名

#### JavaScript/CSS 文件
- **规则**: `kebab-case`
- **示例**: `database-aggregations.js`, `capacity-stats.css`
- **禁止**: `database_aggregations.js`, `capacityStats.js`

#### JavaScript 函数和变量
- **规则**: `camelCase`
- **示例**: `getUserList()`, `totalCount`, `isActive`

#### JavaScript 类
- **规则**: `PascalCase`
- **示例**: `DatabaseService`, `ChartManager`

## 3. 项目结构

### 3.1 目录组织

```
app/
├── routes/          # 路由蓝图
├── models/          # ORM 模型
├── services/        # 业务逻辑服务
├── utils/           # 通用工具函数
├── tasks/           # 异步任务
├── templates/       # Jinja2 模板
└── static/          # 静态资源
    ├── js/
    │   ├── core/           # 核心工具
    │   ├── common/         # 通用组件
    │   ├── modules/        # 业务模块
    │   └── bootstrap/      # 页面入口
    └── css/
```

### 3.2 导入规范

- 将 `app` 视为一方导入根目录
- 按照标准库、第三方库、本地模块的顺序组织导入
- 使用 `isort` 自动排序

```python
# 标准库
import os
from datetime import datetime

# 第三方库
from flask import Blueprint, request
from sqlalchemy import func

# 本地模块
from app import db
from app.models.user import User
from app.utils.decorators import login_required
```

## 4. 日志规范

### 4.1 使用结构化日志

**禁止使用 `print`**，统一使用 `structlog`：

```python
from app.utils.structlog_config import log_info, log_error, log_warning

# 正确
log_info("用户登录成功", module="auth", user_id=user.id)
log_error("数据库连接失败", module="database", exception=exc)

# 错误
print("用户登录成功")
```

### 4.2 日志级别

- **log_info**: 正常业务流程
- **log_warning**: 警告信息，不影响功能
- **log_error**: 错误信息，需要关注
- **log_debug**: 调试信息（开发环境）

## 5. 错误处理

### 5.1 统一错误响应

使用项目定义的错误类：

```python
from app.errors import ValidationError, SystemError, NotFoundError

# 参数验证错误
if not username:
    raise ValidationError("用户名不能为空")

# 系统错误
try:
    result = some_operation()
except Exception as exc:
    log_error("操作失败", module="service", exception=exc)
    raise SystemError("操作失败") from exc

# 资源不存在
user = User.query.get(user_id)
if not user:
    raise NotFoundError("用户不存在")
```

### 5.2 API 响应格式

使用统一的响应工具：

```python
from app.utils.response_utils import jsonify_unified_success, jsonify_unified_error

# 成功响应
return jsonify_unified_success(
    data={"users": users_data},
    message="获取用户列表成功"
)

# 错误响应（通常由错误处理器自动处理）
return jsonify_unified_error(
    message="操作失败",
    error_code="OPERATION_FAILED"
)
```

## 6. 数据库规范

### 6.1 模型定义

```python
from app import db
from app.utils.time_utils import time_utils

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=time_utils.now)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.strftime('%Y-%m-%d') if self.created_at else None
        }
```

### 6.2 查询规范

```python
# 使用 ORM 查询
users = User.query.filter(User.is_active == True).all()

# 分页查询
pagination = User.query.paginate(page=page, per_page=limit, error_out=False)

# 使用 with_entities 优化查询
counts = db.session.query(
    User.role,
    func.count(User.id).label('count')
).group_by(User.role).all()
```

## 7. 前端规范

### 7.1 模块化组织

```javascript
// 使用 IIFE 避免全局污染
(function(window) {
    'use strict';
    
    function MyModule() {
        // 模块实现
    }
    
    window.MyModule = MyModule;
})(window);
```

### 7.2 DOM 操作

使用项目封装的 `DOMHelpers`：

```javascript
const { selectOne, ready } = window.DOMHelpers;

ready(() => {
    selectOne('#myButton').on('click', handleClick);
});
```

### 7.3 HTTP 请求

使用项目封装的 `httpU`：

```javascript
const httpU = window.httpU;

httpU.get('/api/users')
    .then(response => {
        // 处理响应
    })
    .catch(error => {
        // 处理错误
    });
```

## 8. 提交规范

### 8.1 提交信息格式

```
<type>: <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: 修复 bug
- `refactor`: 重构代码
- `docs`: 文档更新
- `style`: 代码格式调整
- `chore`: 构建/工具变更

**示例**:
```
feat: 添加用户管理页面

- 实现用户列表展示
- 添加用户创建/编辑功能
- 集成权限控制

Closes #123
```

### 8.2 提交前检查

```bash
# 1. 格式化代码
make format

# 2. 检查命名规范
./scripts/refactor_naming.sh --dry-run

# 3. 确保没有敏感信息
git diff --cached
```

## 9. 安全规范

### 9.1 环境变量

- 敏感信息存放在 `.env` 文件
- `.env` 文件不提交到版本控制
- 使用 `env.production` 作为生产环境模板

### 9.2 SQL 注入防护

```python
# 正确：使用参数化查询
users = User.query.filter(User.username == username).all()

# 错误：字符串拼接
query = f"SELECT * FROM users WHERE username = '{username}'"  # 危险！
```

### 9.3 CSRF 保护

```python
from app.utils.decorators import require_csrf

@app.route('/api/users', methods=['POST'])
@login_required
@require_csrf
def create_user():
    # 处理请求
    pass
```

## 10. 性能优化

### 10.1 数据库查询优化

```python
# 使用 with_entities 减少数据传输
users = User.query.with_entities(User.id, User.username).all()

# 使用 joinedload 避免 N+1 查询
from sqlalchemy.orm import joinedload
users = User.query.options(joinedload(User.role)).all()

# 批量操作
db.session.bulk_insert_mappings(User, user_dicts)
```

### 10.2 缓存使用

```python
from app.utils.cache_utils import cache_manager

# 缓存查询结果
@cache_manager.cached(timeout=300, key_prefix='user_list')
def get_user_list():
    return User.query.all()
```

## 11. 文档规范

### 11.1 函数文档

```python
def get_user_by_id(user_id: int) -> User | None:
    """根据 ID 获取用户
    
    Args:
        user_id: 用户 ID
        
    Returns:
        User 对象，如果不存在返回 None
        
    Raises:
        ValidationError: 当 user_id 无效时
    """
    if not user_id:
        raise ValidationError("用户 ID 不能为空")
    return User.query.get(user_id)
```

### 11.2 API 文档

在 `docs/api/` 目录维护 API 文档，包括：
- 路由路径
- 请求方法
- 请求参数
- 响应格式
- 错误码

## 12. 违规处理

### 12.1 命名违规

运行命名检查脚本：

```bash
./scripts/refactor_naming.sh --dry-run
```

如果发现违规，必须先修复再提交。

### 12.2 代码审查

PR 审查必须包含以下检查项：
- ✅ 命名规范
- ✅ 代码格式
- ✅ 错误处理
- ✅ 日志记录
- ✅ 安全性
- ✅ 性能考虑

---

**参考文档**:
- [AGENTS.md](../../AGENTS.md) - 仓库使用规范
- [PROJECT_STRUCTURE.md](../architecture/PROJECT_STRUCTURE.md) - 项目结构文档
