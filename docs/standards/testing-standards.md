# WhaleFall 测试规范

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：`tests/` 目录下所有测试代码

## 1. 目的

- 统一测试代码的组织结构与编写风格。
- 明确各类测试的职责边界与依赖要求。
- 确保测试可维护、可复现、可信赖。

## 2. 适用范围

- 所有新增测试代码 MUST 遵循本规范。
- 存量测试在重构时 SHOULD 逐步对齐。

## 3. 快速开始

```bash
# 安装测试依赖
uv sync --group dev

# 运行单元测试（无需数据库，快速，推荐日常开发）
pytest -m unit

# 运行集成测试（需要数据库）
pytest -m integration

# 运行全部测试
pytest

# 带覆盖率
pytest --cov=app --cov-report=html tests/

# 仅运行快速测试（排除慢测试）
pytest -m "unit and not slow"

# 详细输出模式
pytest -v -m unit
```

## 4. 测试状态概览

### 4.1 单元测试（当前可运行）✅

| 测试文件 | 测试数 | 说明 | 依赖 |
|----------|--------|------|------|
| `unit/constants/test_constants_immutability.py` | - | 常量不可变性 | 无 |
| `unit/routes/test_*_contract.py` | 7 文件 | API 契约测试 | 内存 SQLite |
| `unit/services/test_*.py` | 7 文件 | 服务层测试 | Mock |
| `unit/utils/test_*.py` | 4 文件 | 工具函数测试 | 无 |

### 4.2 集成测试（需要数据库）⚠️

| 测试文件 | 测试数 | 说明 | 依赖 |
|----------|--------|------|------|
| `integration/database/` | - | 数据库集成 | PostgreSQL |
| `integration/api/` | - | API 端到端 | PostgreSQL + Redis |

> 注：集成测试目录待建设，当前仅有单元测试。

## 5. 目录结构

```
tests/
├── conftest.py              # 全局 fixtures 与环境配置（唯一设置环境变量的地方）
├── unit/                    # 单元测试（隔离、快速、无外部依赖）
│   ├── conftest.py          # 单元测试专用 fixtures
│   ├── constants/           # 常量/枚举测试
│   ├── models/              # 模型层测试
│   ├── routes/              # API 契约测试（内存数据库）
│   │   └── conftest.py      # 契约测试专用 fixtures（test_client 等）
│   ├── services/            # 服务层测试（Mock）
│   └── utils/               # 工具函数测试
├── integration/             # 集成测试（需要真实数据库）
│   ├── conftest.py          # 集成测试专用 fixtures
│   ├── database/            # 数据库集成测试
│   └── api/                 # API 端到端测试
└── fixtures/                # 共享测试数据（可选）
    ├── json/                # JSON 测试数据
    └── sql/                 # SQL 测试数据
```

### 5.1 目录职责与依赖

| 目录 | 职责 | 依赖 | 执行速度 |
|------|------|------|----------|
| `unit/constants/` | 常量不可变性验证 | 无 | < 10ms |
| `unit/utils/` | 工具函数行为验证 | 无/Mock | < 50ms |
| `unit/services/` | 服务层业务逻辑 | Mock | < 100ms |
| `unit/routes/` | API 契约结构验证 | 内存 SQLite | < 500ms |
| `integration/` | 模块间协作、真实依赖 | PostgreSQL/Redis | < 5s |

### 5.2 环境变量设置规则

- MUST：环境变量只在 `tests/conftest.py` 顶部设置一次
- MUST NOT：在测试文件中重复设置 `os.environ`
- 原因：避免导入顺序问题和重复代码

```python
# ✅ 正确：只在 tests/conftest.py 设置
# tests/conftest.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CACHE_REDIS_URL", "redis://localhost:6379/0")

# ❌ 错误：在测试文件中重复设置
# tests/unit/services/test_xxx.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")  # 不要这样做
```

## 6. 命名规范

### 6.1 文件命名

- MUST：`test_<module>_<feature>.py`（全小写、下划线分隔）
- 契约测试 SHOULD：`test_<endpoint>_contract.py`

```
✅ test_database_ledger_service.py
✅ test_instances_list_contract.py
✅ test_request_payload.py
❌ TestDatabaseService.py
❌ database_test.py
```

### 6.2 函数命名

- MUST：`test_<action>_<scenario>[_<expected>]()`

```python
✅ test_format_size_handles_megabytes()
✅ test_parse_payload_sets_missing_boolean_fields_to_false_for_multidict()
✅ test_resolve_sync_status_returns_failed_when_timeout()
❌ test_service()
❌ test1()
```

## 7. 测试分类与标记

### 7.1 pytest markers 配置

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: 单元测试（隔离、快速、无外部依赖）",
    "integration: 集成测试（需要数据库/Redis）",
    "slow: 执行时间 > 1s 的测试",
    "contract: API 契约测试",
]
```

### 7.2 标记使用规则

- MUST：所有测试函数必须标记 `@pytest.mark.unit` 或 `@pytest.mark.integration`
- SHOULD：执行时间 > 1s 额外标记 `@pytest.mark.slow`

```python
@pytest.mark.unit
def test_format_size_handles_megabytes() -> None:
    ...

@pytest.mark.integration
@pytest.mark.slow
def test_sync_instance_with_real_database() -> None:
    ...
```

### 7.3 运行命令

```bash
# 按标记运行
pytest -m unit                    # 仅单元测试
pytest -m integration             # 仅集成测试
pytest -m "not slow"              # 排除慢测试
pytest -m "unit and not slow"     # 快速单元测试

# 按目录运行
pytest tests/unit/services/       # 服务层测试
pytest tests/unit/routes/         # 契约测试

# 带详细输出
pytest -v -m unit
```

## 8. Fixtures 规范

### 8.1 conftest.py 层级

```
tests/
├── conftest.py              # 全局：环境变量、app 工厂、通用 fixtures
├── unit/
│   ├── conftest.py          # 单元测试：mock fixtures、通用 monkeypatch
│   └── routes/
│       └── conftest.py      # 契约测试：test_client、auth_session
└── integration/
    └── conftest.py          # 集成测试：真实数据库连接、事务回滚
```

### 8.2 环境变量配置

- MUST：在根 `conftest.py` 顶部设置测试环境变量（在任何 import 之前）
- MUST NOT：在测试文件中重复设置
- MUST NOT：在 fixture 函数内部设置环境变量

```python
# tests/conftest.py（文件最顶部，在所有 import 之前）
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CACHE_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-key")

# 然后才是其他 import
import pytest
from app import create_app, db
```

### 8.3 常用 Fixtures 示例

```python
import pytest
from app import create_app, db

@pytest.fixture(scope="session")
def app():
    """应用实例，整个测试会话复用"""
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    return app

@pytest.fixture(scope="function")
def client(app):
    """测试客户端，每个测试函数独立"""
    return app.test_client()

@pytest.fixture(scope="function")
def db_session(app):
    """数据库会话，测试后自动回滚"""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()

@pytest.fixture(scope="function")
def auth_session(client, db_session):
    """已认证的会话，用于需要登录的测试"""
    from app.models.user import User
    user = User(username="test_admin", password="TestPass1", role="admin")
    db_session.add(user)
    db_session.commit()

    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)

    yield client

    # teardown: 清理测试用户
    db_session.delete(user)
    db_session.commit()
```

### 8.4 Fixture 作用域选择

| 作用域 | 使用场景 | 示例 |
|--------|----------|------|
| `function` | 每个测试需要独立状态 | `db_session`, `client` |
| `class` | 同一测试类共享状态 | 较少使用 |
| `module` | 同一文件共享状态 | 较少使用 |
| `session` | 整个测试会话共享 | `app` 实例 |

## 9. 测试类型详解

### 9.1 单元测试（unit/）

**职责**：验证单个函数/方法的行为，隔离外部依赖。

**规则**：
- MUST：使用 mock/monkeypatch 隔离外部依赖
- MUST：每个测试函数只验证一个行为
- MUST NOT：访问真实数据库、网络、文件系统
- SHOULD：执行时间 < 100ms

**示例**：

```python
@pytest.mark.unit
def test_resolve_sync_status_recent(monkeypatch) -> None:
    service = DatabaseLedgerService()
    now = datetime.datetime(2025, 11, 27, 12, 0, tzinfo=datetime.UTC)
    monkeypatch.setattr(
        "app.services.ledgers.database_ledger_service.time_utils.now",
        lambda: now
    )
    status = service._resolve_sync_status(now - datetime.timedelta(hours=2))
    assert status["value"] == SyncStatus.COMPLETED
```

### 9.2 API 契约测试（unit/routes/）

**职责**：验证 API 响应结构符合契约，不验证业务逻辑。

**规则**：
- MUST：验证响应状态码
- MUST：验证响应 envelope 结构（`success`, `error`, `message`, `timestamp`, `data`）
- MUST：验证 `data` 字段的 key 集合
- SHOULD：使用内存数据库（SQLite）
- MUST NOT：验证具体业务数据值

**示例**：

```python
@pytest.mark.unit
def test_instances_list_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        # 创建最小测试数据
        db.metadata.create_all(bind=db.engine, tables=[...])
        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/instances/api/instances")

        # 验证状态码
        assert response.status_code == 200

        # 验证 envelope 结构
        payload = response.get_json()
        assert payload.get("success") is True
        assert payload.get("error") is False
        assert "message" in payload
        assert "timestamp" in payload

        # 验证 data 字段结构
        data = payload.get("data")
        assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())
```

### 9.3 集成测试（integration/）

**职责**：验证模块间协作、真实外部依赖。

**前提条件**：
```bash
# 启动数据库
docker compose up -d postgres redis

# 或使用测试数据库
export DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/test_db
```

**规则**：
- MUST：使用真实数据库（测试库）
- MUST：测试后清理数据
- SHOULD：标记 `@pytest.mark.slow`

## 10. 测试数据管理

### 10.1 测试数据清理

- MUST：集成测试后自动清理创建的数据
- SHOULD：使用 fixture 的 teardown 机制

```python
@pytest.fixture
def test_user(db_session):
    user = User(username="test_user", password="TestPass1")
    db_session.add(user)
    db_session.commit()
    yield user
    # teardown: 自动回滚或删除
    db_session.delete(user)
    db_session.commit()
```

### 10.2 测试数据文件

```
tests/fixtures/
├── json/
│   ├── valid_instance.json
│   └── invalid_instance.json
└── sql/
    └── seed_test_data.sql
```

## 11. 覆盖率要求

### 11.1 目标

| 层级 | 最低覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| `utils/` | 80% | 90% |
| `services/` | 70% | 85% |
| `routes/` | 60%（契约） | 80% |
| `models/` | 50% | 70% |

### 11.2 运行覆盖率

```bash
# 生成 HTML 报告
pytest --cov=app --cov-report=html tests/unit/

# 检查覆盖率门槛
pytest --cov=app --cov-fail-under=70 tests/unit/

# CI 模式
pytest --cov=app --cov-report=xml tests/
```

## 12. 门禁与检查

### 12.1 CI 门禁

- MUST：所有单元测试通过
- MUST：无新增测试文件缺少 marker
- SHOULD：覆盖率不低于基线

### 12.2 本地检查命令

```bash
# 运行单元测试
pytest -m unit

# 检查测试文件命名
find tests -name "*.py" ! -name "test_*.py" ! -name "conftest.py" ! -name "__init__.py"

# 检查缺少 marker 的测试（简易）
grep -rL "@pytest.mark" tests/unit/ --include="test_*.py"
```

## 13. 正反例

### 13.1 正例

```python
# ✅ 清晰的测试命名 + marker
@pytest.mark.unit
def test_format_size_returns_未采集_when_none() -> None:
    assert DatabaseLedgerService()._format_size(None) == "未采集"

# ✅ 隔离的单元测试
@pytest.mark.unit
def test_parse_payload_trims_strings_and_defaults_checkbox() -> None:
    payload: MultiDict[str, str] = MultiDict([("username", "  alice  ")])
    sanitized = parse_payload(payload, boolean_fields_default_false=["is_active"])
    assert sanitized["username"] == "alice"
    assert sanitized["is_active"] is False

# ✅ 契约测试只验证结构
@pytest.mark.unit
def test_users_list_contract(client, auth_session) -> None:
    response = client.get("/users/api/users")
    assert response.status_code == 200
    assert {"items", "total"}.issubset(response.json["data"].keys())
```

### 13.2 反例

```python
# ❌ 命名不清晰
def test_service():
    ...

# ❌ 缺少 marker
def test_format_size():
    ...

# ❌ 单元测试访问真实数据库
@pytest.mark.unit
def test_user_service():
    user = User.query.first()  # 不应访问真实数据库
    ...

# ❌ 多个断言验证不同行为
def test_everything():
    assert service.create() is not None
    assert service.update() is True
    assert service.delete() is True
```

## 14. 测试数据自动清理

### 14.1 清理策略

- MUST：集成测试后自动清理创建的数据
- SHOULD：使用 fixture 的 teardown 机制（yield 后的代码）
- SHOULD：测试用户名包含 `test_` 前缀，便于识别和清理

### 14.2 手动清理命令

```bash
# 清理测试数据库中的测试用户（名称包含 test_）
# 仅在集成测试环境使用
flask shell -c "from app.models.user import User; User.query.filter(User.username.like('test_%')).delete()"
```

## 15. 常见问题排查

### 15.1 测试无法运行

```bash
# 检查 pytest 是否安装
uv run pytest --version

# 检查测试发现
pytest --collect-only tests/unit/

# 检查 marker 配置
pytest --markers | grep -E "unit|integration"
```

### 15.2 导入错误

```bash
# 确保在项目根目录运行
cd /path/to/WhaleFall
pytest -m unit

# 检查 PYTHONPATH
echo $PYTHONPATH
```

### 15.3 数据库连接错误

```bash
# 单元测试应使用内存数据库，检查环境变量
echo $DATABASE_URL  # 应为空或 sqlite:///:memory:

# 集成测试需要真实数据库
docker compose up -d postgres redis
```

## 16. 变更历史

| 日期 | 变更内容 | 负责人 |
|------|----------|--------|
| 2025-12-25 | 初始版本，参考 claude-code-hub 测试结构 | WhaleFall Team |
| 2025-12-25 | 补充环境变量设置规则、Fixture 作用域、常见问题排查 | WhaleFall Team |
