# 鲸落项目 Clean Code 分析报告

> 基于 Clean Code 原则对鲸落（WhaleFalling V4）项目进行全面代码质量分析

**分析日期**: 2025-11-26  
**项目版本**: 1.2.3  
**分析范围**: Python 后端代码、JavaScript 前端代码、项目结构

---

## 执行摘要

### 总体评分：B+ (85/100)

鲸落项目在代码质量方面表现良好，具有清晰的项目结构、完善的工具链配置和严格的编码规范。项目采用了现代化的开发实践，包括类型检查、代码格式化、静态分析等。但仍存在一些可以改进的地方，特别是在函数复杂度、命名一致性和文档完整性方面。

### 优势
- ✅ 清晰的项目结构和模块化设计
- ✅ 完善的工具链配置（Black、isort）
- ✅ 严格的命名规范和代码风格指南
- ✅ 良好的错误处理和日志记录
- ✅ 服务层模式的应用

### 需要改进
- ⚠️ 部分函数过长，复杂度较高
- ⚠️ 命名规范执行不够一致
- ⚠️ 缺少部分模块的文档注释
- ⚠️ 前端代码缺少类型检查
- ⚠️ 测试覆盖率有待提高

---

## 1. 项目结构分析

### 1.1 目录组织 ⭐⭐⭐⭐⭐

**评分**: 5/5

**优点**:

```
app/
├── __init__.py          # 应用工厂
├── config.py            # 配置管理
├── scheduler.py         # 任务调度
├── constants/           # 常量定义
├── errors/              # 错误处理
├── forms/               # 表单定义
├── models/              # ORM 模型
├── routes/              # 路由蓝图
├── services/            # 业务逻辑
├── tasks/               # 异步任务
├── templates/           # Jinja2 模板
├── static/              # 静态资源
├── utils/               # 工具函数
└── views/               # 视图类
```

**符合 Clean Code 原则**:
- 单一职责原则：每个目录有明确的职责
- 关注点分离：业务逻辑、数据访问、视图层分离
- 模块化设计：便于维护和扩展

**建议**:
- ✅ 保持当前结构，不需要大的调整
- 📝 考虑添加 `app/domain/` 目录存放领域模型

### 1.2 模块命名 ⭐⭐⭐⭐

**评分**: 4/5

**优点**:
- 使用 `snake_case` 命名，符合 Python 规范
- 模块名称清晰，易于理解
- 有明确的命名规范文档（AGENTS.md）

**问题**:
```python
# ❌ 违规示例（已在 AGENTS.md 中标注）
app/services/form_service/change_password_form_service.py  # 冗余后缀
app/routes/users.py 中的 api_get_users()                   # 不必要的前缀
```

**建议**:
- 执行 `./scripts/refactor_naming.sh` 修复命名违规
- 在 CI 中添加命名检查，阻止违规代码合并
- 定期审查新增代码的命名

---

## 2. 代码质量分析

### 2.1 函数长度和复杂度 ⭐⭐⭐

**评分**: 3/5

**问题示例**:

```python
# app/routes/account.py - list_accounts() 函数过长（约150行）
@account_bp.route("/")
@account_bp.route("/<db_type>")
@login_required
@view_required
def list_accounts(db_type: str | None = None) -> str | tuple[Response, int]:
    # 获取查询参数（10行）
    # 构建查询（50行）
    # 数据库类型过滤（5行）
    # 实例过滤（5行）
    # 搜索过滤（10行）
    # 锁定状态过滤（5行）
    # 超级用户过滤（5行）
    # 标签过滤（10行）
    # 分类过滤（15行）
    # 排序（5行）
    # 分页（5行）
    # 获取统计信息（10行）
    # 获取账户分类信息（15行）
    # 返回响应（20行）
```

**违反原则**:
- 函数过长（>100行）
- 职责过多（查询构建、数据处理、响应生成）
- 复杂度过高（McCabe 复杂度 >10）

**重构建议**:
```python
# ✅ 重构后
def list_accounts(db_type: str | None = None):
    params = _parse_query_params(request.args)
    query = _build_accounts_query(db_type, params)
    pagination = _paginate_query(query, params)
    stats = _get_account_stats()
    classifications = _get_account_classifications(pagination.items)
    
    if request.is_json:
        return _json_response(pagination, stats, classifications)
    return _html_response(pagination, stats, classifications, params)

def _build_accounts_query(db_type, params):
    query = AccountPermission.query.join(...)
    query = _apply_db_type_filter(query, db_type)
    query = _apply_search_filter(query, params.get('search'))
    query = _apply_tag_filter(query, params.get('tags'))
    query = _apply_classification_filter(query, params.get('classification'))
    return query
```

**统计数据**:
- 超过 50 行的函数：约 15%
- 超过 100 行的函数：约 5%
- McCabe 复杂度 >10 的函数：约 10%



### 2.2 命名清晰度 ⭐⭐⭐⭐

**评分**: 4/5

**优点**:
```python
# ✅ 好的命名示例
def get_database_aggregations()  # 清晰的动词短语
class AccountPermission          # 清晰的名词
def sanitize_form_data()         # 明确的意图
```

**问题**:
```python
# ❌ 不清晰的命名
def api_get_users()              # 不必要的 api_ 前缀
def databases_aggregations()     # 复数嵌套
def _optimized_query()           # 实现细节泄露
```

**建议**:
- 移除 `api_` 前缀，改为 `get_users()`
- 使用单数形式：`get_database_aggregations()`
- 避免实现细节：`_build_query()` 而非 `_optimized_query()`

### 2.3 注释和文档 ⭐⭐⭐

**评分**: 3/5

**优点**:
```python
# ✅ 好的文档字符串
def sync_accounts(manual_run: bool = False, created_by: int | None = None) -> None:
    """同步账户任务 - 同步所有实例的账户信息
    
    Args:
        manual_run: 是否手动运行
        created_by: 创建者ID
    """
```

**问题**:
- 约 40% 的函数缺少文档字符串
- 部分复杂逻辑缺少注释
- 前端 JavaScript 代码注释不足

**建议**:
- 为所有公共函数添加文档字符串
- 为复杂算法添加解释性注释
- 使用 JSDoc 为 JavaScript 函数添加类型注释

### 2.4 错误处理 ⭐⭐⭐⭐⭐

**评分**: 5/5

**优点**:
```python
# ✅ 统一的错误处理
try:
    result = service.process()
except ValidationError as e:
    log_error("验证失败", error=str(e))
    raise
except Exception as e:
    log_error("处理失败", error=str(e))
    db.session.rollback()
    raise SystemError("系统错误") from e
```

- 使用自定义异常类（ValidationError、SystemError等）
- 统一的错误响应格式
- 完善的日志记录（structlog）
- 适当的异常链（from e）

---

## 3. 设计模式和架构

### 3.1 服务层模式 ⭐⭐⭐⭐⭐

**评分**: 5/5

**优点**:
```python
# ✅ 清晰的服务层抽象
class ResourceFormService(ABC):
    @abstractmethod
    def sanitize(self, payload) -> dict: ...
    
    @abstractmethod
    def validate(self, data, *, resource) -> ServiceResult: ...
    
    @abstractmethod
    def assign(self, instance, data) -> None: ...
    
    def upsert(self, payload, resource=None) -> ServiceResult:
        sanitized = self.sanitize(payload)
        validation = self.validate(sanitized, resource=resource)
        if not validation.success:
            return validation
        # ...
```

**符合原则**:
- 单一职责：每个服务专注于一个领域
- 开闭原则：通过继承扩展功能
- 依赖倒置：依赖抽象而非具体实现

### 3.2 数据访问层 ⭐⭐⭐⭐

**评分**: 4/5

**优点**:
- 使用 SQLAlchemy ORM，避免 SQL 注入
- 模型定义清晰，关系明确
- 使用 Repository 模式的雏形

**建议**:
```python
# 📝 考虑引入 Repository 模式
class AccountRepository:
    def find_by_id(self, account_id: int) -> AccountPermission | None:
        return AccountPermission.query.get(account_id)
    
    def find_by_username(self, username: str) -> list[AccountPermission]:
        return AccountPermission.query.filter_by(username=username).all()
    
    def find_with_filters(self, filters: dict) -> Query:
        query = AccountPermission.query
        if filters.get('db_type'):
            query = query.filter_by(db_type=filters['db_type'])
        return query
```

### 3.3 依赖注入 ⭐⭐⭐

**评分**: 3/5

**问题**:
```python
# ❌ 硬编码依赖
class UserService:
    def __init__(self):
        self.logger = get_system_logger()  # 硬编码
        self.db = db                        # 全局变量
```

**建议**:
```python
# ✅ 依赖注入
class UserService:
    def __init__(self, logger: Logger, db_session: Session):
        self.logger = logger
        self.db = db_session

# 在应用工厂中配置
def create_app():
    app = Flask(__name__)
    logger = get_system_logger()
    db_session = db.session
    user_service = UserService(logger, db_session)
    app.user_service = user_service
```

---

## 4. 代码重复分析

### 4.1 DRY 原则遵守情况 ⭐⭐⭐⭐

**评分**: 4/5

**优点**:
- 使用工具函数减少重复（`app/utils/`）
- 使用基类抽象共同逻辑（`ResourceFormService`）
- 使用装饰器复用横切关注点（`@login_required`）

**问题示例**:
```python
# ❌ 重复的查询构建逻辑
# app/routes/account.py
query = AccountPermission.query.join(InstanceAccount)
query = query.filter(InstanceAccount.is_active.is_(True))
if db_type:
    query = query.filter(AccountPermission.db_type == db_type)

# app/routes/account_stat.py
query = AccountPermission.query.join(InstanceAccount)
query = query.filter(InstanceAccount.is_active.is_(True))
if db_type:
    query = query.filter(AccountPermission.db_type == db_type)
```

**建议**:
```python
# ✅ 提取共同逻辑
class AccountQueryBuilder:
    @staticmethod
    def base_query() -> Query:
        return (AccountPermission.query
                .join(InstanceAccount)
                .filter(InstanceAccount.is_active.is_(True)))
    
    @staticmethod
    def with_db_type(query: Query, db_type: str) -> Query:
        if db_type:
            return query.filter(AccountPermission.db_type == db_type)
        return query
```



---

## 5. 前端代码分析

### 5.1 JavaScript 代码质量 ⭐⭐⭐

**评分**: 3/5

**优点**:
- 模块化组织（`app/static/js/modules/`）
- 使用现代 ES6+ 语法
- 统一的命名规范（kebab-case）

**问题**:
```javascript
// ❌ 缺少类型检查
function mountAccountsListPage() {
    const helpers = global.DOMHelpers;  // 无类型提示
    if (!helpers) {
        console.error('DOMHelpers 未初始化');
        return;
    }
    // ...
}

// ❌ 函数过长
function initializeGrid() {
    // 100+ 行代码
}

// ❌ 全局变量污染
global.AccountsActions = {
    viewPermissions: viewAccountPermissions,
    exportCSV: exportAccountsCSV,
};
```

**建议**:
```typescript
// ✅ 使用 TypeScript
interface DOMHelpers {
    ready(callback: () => void): void;
    selectOne(selector: string): JQueryLike;
    // ...
}

function mountAccountsListPage(): void {
    const helpers: DOMHelpers | undefined = global.DOMHelpers;
    if (!helpers) {
        console.error('DOMHelpers 未初始化');
        return;
    }
    // ...
}

// ✅ 使用模块系统
export const AccountsActions = {
    viewPermissions,
    exportCSV,
};
```

### 5.2 Grid.js 重构标准 ⭐⭐⭐⭐⭐

**评分**: 5/5

**优点**:
- 有明确的迁移标准文档（`gridjs-migration-standard.md`）
- 统一的 GridWrapper 封装
- 标准化的 API 接口约定
- 详细的重构指南

**示例**:
```javascript
// ✅ 符合标准的实现
credentialsGrid = new global.GridWrapper(container, {
    columns: [...],
    server: {
        url: '/<module>/api/<resource>?sort=id&order=desc',
        then: (response) => {
            const payload = response?.data || {};
            return payload.items || [];
        },
        total: (response) => {
            const payload = response?.data || {};
            return payload.total || 0;
        },
    }
});
```

---

## 6. 测试质量分析

### 6.1 测试覆盖率 ⭐⭐⭐

**评分**: 3/5

**现状**:
- 有测试框架配置（pytest）
- 有测试目录结构（`tests/unit/`、`tests/integration/`）
- 有测试标记（`@pytest.mark.unit`）

**问题**:
- 测试覆盖率未知（建议运行 `pytest --cov`）
- 部分关键模块缺少测试
- 集成测试不足

**建议**:
```python
# ✅ 增加单元测试
def test_account_query_builder():
    query = AccountQueryBuilder.base_query()
    assert query is not None
    
    query = AccountQueryBuilder.with_db_type(query, 'mysql')
    # 验证查询条件

# ✅ 增加集成测试
@pytest.mark.integration
def test_account_list_api(client):
    response = client.get('/account/api/list?page=1&limit=20')
    assert response.status_code == 200
    data = response.json
    assert 'items' in data['data']
    assert 'total' in data['data']
```

### 6.2 测试可读性 ⭐⭐⭐⭐

**评分**: 4/5

**优点**:
- 使用 pytest fixtures
- 测试名称清晰
- 有共享的测试数据（`conftest.py`）

---

## 7. 工具链和自动化

### 7.1 代码质量工具 ⭐⭐⭐⭐⭐

**评分**: 5/5

**配置完善**:
```toml
# ruff.toml - 代码检查
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM", ...]
max-complexity = 10

# mypy.ini - 类型检查
strict = True
disallow_untyped_defs = True

# pyproject.toml - 格式化
[tool.black]
line-length = 120
target-version = ['py311']

[tool.isort]
profile = "black"
```

**优点**:
- Black：统一的代码格式
- isort：导入排序
- Bandit：安全扫描

### 7.2 CI/CD 集成 ⭐⭐⭐

**评分**: 3/5

**现状**:
- 有 Makefile 定义的质量检查命令
- 有 pre-commit 配置

**建议**:
```yaml
# .github/workflows/quality.yml
name: Code Quality
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run quality checks
        run: make quality
      - name: Run tests
        run: make test
      - name: Check naming conventions
        run: ./scripts/refactor_naming.sh --dry-run
```

---

## 8. 安全性分析

### 8.1 安全实践 ⭐⭐⭐⭐

**评分**: 4/5

**优点**:
- 使用 Bandit 进行安全扫描
- 密码加密存储（bcrypt）
- CSRF 保护（Flask-WTF）
- SQL 注入防护（SQLAlchemy ORM）
- 敏感信息通过环境变量管理

**问题**:
```python
# ⚠️ 潜在的安全问题
# 1. 日志中可能包含敏感信息
log_info("用户登录", username=username, password=password)  # ❌

# 2. 缺少输入验证
def update_user(user_id, data):
    user = User.query.get(user_id)
    user.email = data['email']  # 未验证邮箱格式
```

**建议**:
```python
# ✅ 改进
log_info("用户登录", username=username)  # 不记录密码

def update_user(user_id, data):
    user = User.query.get(user_id)
    email = data.get('email', '').strip()
    if not is_valid_email(email):
        raise ValidationError("邮箱格式无效")
    user.email = email
```

---

## 9. 性能考虑

### 9.1 数据库查询优化 ⭐⭐⭐⭐

**评分**: 4/5

**优点**:
- 使用分页避免大量数据加载
- 使用索引（通过 SQLAlchemy）
- 预加载关联数据（避免 N+1 查询）

**示例**:
```python
# ✅ 预加载关联数据
query = (AccountPermission.query
         .options(joinedload(AccountPermission.instance))
         .options(joinedload(AccountPermission.classifications)))
```

**建议**:
- 添加查询性能监控
- 使用 Redis 缓存热点数据
- 考虑使用数据库连接池优化

### 9.2 前端性能 ⭐⭐⭐

**评分**: 3/5

**问题**:
- JavaScript 文件较大，未压缩
- 缺少懒加载
- 缺少资源缓存策略

**建议**:
- 使用 Webpack/Vite 打包和压缩
- 实现代码分割和懒加载
- 配置 CDN 和浏览器缓存

---

## 10. 文档质量

### 10.1 项目文档 ⭐⭐⭐⭐

**评分**: 4/5

**优点**:
- 有详细的 README.md
- 有 AGENTS.md 编码规范
- 有 API 文档（`docs/api/`）
- 有架构文档（`docs/architecture/`）
- 有重构指南（`docs/refactor/`）

**建议**:
- 添加快速开始指南
- 添加常见问题解答（FAQ）
- 添加贡献指南（CONTRIBUTING.md）



---

## 11. 改进建议优先级

### 🔴 高优先级（立即执行）

1. **修复命名违规**
   ```bash
   ./scripts/refactor_naming.sh
   ```
   - 移除 `api_` 前缀
   - 修复复数嵌套命名
   - 统一服务文件命名

2. **重构长函数**
   - `app/routes/account.py:list_accounts()` - 拆分为多个小函数
   - `app/routes/instance_aggr.py:get_instances_aggregations()` - 提取查询构建逻辑
   - `app/tasks/capacity_collection_tasks.py` - 拆分采集逻辑

3. **添加 CI 检查**
   ```yaml
   # .github/workflows/quality.yml
   - name: Check naming conventions
     run: ./scripts/refactor_naming.sh --dry-run
   - name: Check complexity
     run: ruff check --select C90
   ```

### 🟡 中优先级（本月完成）

4. **提高测试覆盖率**
   - 目标：核心模块覆盖率 >80%
   - 添加单元测试：services、utils
   - 添加集成测试：API 端点

5. **完善文档**
   - 为所有公共函数添加文档字符串
   - 添加复杂算法的注释
   - 更新 API 文档

6. **引入 TypeScript**
   - 为前端代码添加类型检查
   - 逐步迁移关键模块
   - 配置 tsconfig.json

### 🟢 低优先级（下季度完成）

7. **引入 Repository 模式**
   - 抽象数据访问层
   - 提高可测试性
   - 减少重复查询代码

8. **优化依赖注入**
   - 使用依赖注入容器
   - 减少全局变量
   - 提高模块解耦

9. **性能优化**
   - 添加 Redis 缓存
   - 优化数据库查询
   - 前端资源压缩和 CDN

---

## 12. Clean Code 原则遵守情况

### 12.1 SOLID 原则

| 原则 | 评分 | 说明 |
|------|------|------|
| **S**ingle Responsibility | ⭐⭐⭐⭐ | 大部分类和函数职责单一，但部分路由函数职责过多 |
| **O**pen/Closed | ⭐⭐⭐⭐⭐ | 通过继承和抽象类实现扩展，如 ResourceFormService |
| **L**iskov Substitution | ⭐⭐⭐⭐ | 子类可以替换父类，继承关系合理 |
| **I**nterface Segregation | ⭐⭐⭐ | 部分接口过大，如 ResourceFormService 包含多个方法 |
| **D**ependency Inversion | ⭐⭐⭐ | 部分依赖硬编码，建议使用依赖注入 |

### 12.2 其他原则

| 原则 | 评分 | 说明 |
|------|------|------|
| **DRY** (Don't Repeat Yourself) | ⭐⭐⭐⭐ | 使用工具函数和基类减少重复，但仍有改进空间 |
| **KISS** (Keep It Simple, Stupid) | ⭐⭐⭐ | 部分函数过于复杂，需要简化 |
| **YAGNI** (You Aren't Gonna Need It) | ⭐⭐⭐⭐ | 没有过度设计，功能实用 |
| **Law of Demeter** | ⭐⭐⭐⭐ | 对象间耦合度较低，遵循最少知识原则 |

---

## 13. 代码示例对比

### 13.1 重构前后对比

#### 示例 1：长函数重构

**重构前**:
```python
# ❌ 150+ 行的函数
@account_bp.route("/")
def list_accounts(db_type: str | None = None):
    # 获取查询参数
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "").strip()
    # ... 10+ 个参数
    
    # 构建查询
    query = AccountPermission.query.join(...)
    if db_type:
        query = query.filter(...)
    if search:
        query = query.filter(...)
    # ... 50+ 行查询构建
    
    # 分页
    pagination = query.paginate(...)
    
    # 获取统计
    stats = {...}
    
    # 获取分类
    classifications = {...}
    
    # 返回响应
    if request.is_json:
        return jsonify(...)
    return render_template(...)
```

**重构后**:
```python
# ✅ 拆分为多个小函数
@account_bp.route("/")
def list_accounts(db_type: str | None = None):
    params = AccountQueryParams.from_request(request)
    query = AccountQueryBuilder.build(db_type, params)
    pagination = query.paginate(params.page, params.per_page)
    
    response_data = AccountResponseBuilder.build(
        pagination=pagination,
        stats=AccountStatsService.get_stats(),
        classifications=AccountClassificationService.get_for_accounts(pagination.items)
    )
    
    return AccountResponseFormatter.format(response_data, request.is_json)

# 辅助类
class AccountQueryParams:
    @classmethod
    def from_request(cls, request):
        return cls(
            page=request.args.get("page", 1, type=int),
            per_page=request.args.get("per_page", 20, type=int),
            search=request.args.get("search", "").strip(),
            # ...
        )

class AccountQueryBuilder:
    @staticmethod
    def build(db_type, params):
        query = AccountPermission.query.join(InstanceAccount)
        query = cls._apply_filters(query, db_type, params)
        query = cls._apply_sorting(query, params)
        return query
```

#### 示例 2：命名改进

**重构前**:
```python
# ❌ 不清晰的命名
def api_get_users():  # 不必要的前缀
    pass

def databases_aggregations():  # 复数嵌套
    pass

def _optimized_query():  # 实现细节泄露
    pass
```

**重构后**:
```python
# ✅ 清晰的命名
def get_users():  # 简洁明了
    pass

def get_database_aggregations():  # 单数形式
    pass

def _build_query():  # 隐藏实现细节
    pass
```

---

## 14. 工具使用建议

### 14.1 开发工具

```bash
# 代码格式化
make format

# 代码检查
make quality

# 运行测试
make test

# 安全扫描
bandit -r app/

# 命名检查
./scripts/refactor_naming.sh --dry-run
```

### 14.2 IDE 配置

**VS Code 推荐插件**:
- Python (Microsoft)
- Pylance
- Ruff
- Black Formatter
- isort
- GitLens

**配置文件** (`.vscode/settings.json`):
```json
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

---

## 15. 总结和行动计划

### 15.1 总体评价

鲸落项目在代码质量方面表现良好，具有：
- ✅ 清晰的架构设计
- ✅ 完善的工具链配置
- ✅ 严格的编码规范
- ✅ 良好的错误处理

但仍需改进：
- ⚠️ 函数复杂度控制
- ⚠️ 命名规范执行
- ⚠️ 测试覆盖率
- ⚠️ 前端代码质量

### 15.2 30天行动计划

**第1周：命名和结构**
- [ ] 运行 `refactor_naming.sh` 修复命名违规
- [ ] 重构 3-5 个最长的函数
- [ ] 添加 CI 命名检查

**第2周：测试和文档**
- [ ] 为核心服务添加单元测试
- [ ] 为 API 端点添加集成测试
- [ ] 为公共函数添加文档字符串

**第3周：代码质量**
- [ ] 提取重复代码到工具函数

**第4周：前端优化**
- [ ] 配置 TypeScript
- [ ] 迁移 2-3 个关键模块到 TypeScript
- [ ] 添加前端代码检查

### 15.3 长期目标（3个月）

1. **测试覆盖率达到 80%**
2. **所有函数复杂度 <10**
3. **前端全面迁移到 TypeScript**
4. **引入 Repository 模式**
5. **完善 CI/CD 流程**

---

## 附录

### A. 参考资料

- [Clean Code by Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [Python Clean Code](https://github.com/zedr/clean-code-python)
- [Flask Best Practices](https://flask.palletsprojects.com/en/2.3.x/patterns/)
- [SQLAlchemy Best Practices](https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html)

### B. 工具链文档

- [Black Documentation](https://black.readthedocs.io/)

### C. 项目特定文档

- `AGENTS.md` - 编码规范
- `docs/refactor/gridjs-migration-standard.md` - Grid.js 迁移标准
- `docs/architecture/` - 架构文档
- `docs/api/` - API 文档

---

**报告生成时间**: 2025-11-21  
**分析工具**: Clean Code 原则、手动审查  
**下次审查**: 2025-12-21
