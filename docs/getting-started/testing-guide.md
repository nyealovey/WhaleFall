# 测试指南

> 状态：Active  
> 适用人群：开发者、贡献者  
> 前置条件：已完成本地开发环境搭建

本文档帮助你快速上手 WhaleFall 项目的测试工作。

## 1. 环境准备

### 1.1 安装测试依赖

```bash
# 使用 uv 安装开发依赖（包含 pytest）
uv sync --group dev

# 验证 pytest 安装
uv run pytest --version
```

### 1.2 目录结构

```
tests/
├── conftest.py              # 全局配置（环境变量在这里设置）
├── unit/                    # 单元测试（日常开发主要使用）
│   ├── constants/           # 常量测试
│   ├── routes/              # API 契约测试
│   ├── services/            # 服务层测试
│   └── utils/               # 工具函数测试
└── integration/             # 集成测试（需要数据库）
    ├── api/                 # API 端到端测试
    └── database/            # 数据库集成测试
```

## 2. 运行测试

### 2.1 日常开发（推荐）

```bash
# 运行所有单元测试（无需数据库，约 3 秒）
pytest -m unit

# 运行特定目录的测试
pytest tests/unit/services/

# 运行单个测试文件
pytest tests/unit/services/test_database_ledger_service.py

# 运行单个测试函数
pytest tests/unit/services/test_database_ledger_service.py::test_format_size_handles_megabytes
```

### 2.2 详细输出

```bash
# 显示每个测试的名称和结果
pytest -m unit -v

# 显示 print 输出（调试用）
pytest -m unit -s

# 组合使用
pytest -m unit -vs
```

### 2.3 覆盖率报告

```bash
# 生成 HTML 覆盖率报告
pytest --cov=app --cov-report=html tests/unit/

# 报告位置：htmlcov/index.html
open htmlcov/index.html
```

## 3. 编写测试

### 3.1 创建测试文件

文件命名规则：`test_<模块名>_<功能>.py`

```bash
# 示例：为 user_service.py 创建测试
touch tests/unit/services/test_user_service.py
```

### 3.2 基本测试模板

```python
import pytest

from app.services.xxx_service import XxxService


@pytest.mark.unit
def test_功能_场景_预期结果() -> None:
    """测试描述."""
    # Arrange（准备）
    service = XxxService()
    input_data = {"key": "value"}

    # Act（执行）
    result = service.do_something(input_data)

    # Assert（断言）
    assert result is not None
    assert result["status"] == "success"
```

### 3.3 使用 Mock 隔离依赖

```python
@pytest.mark.unit
def test_service_with_mocked_dependency(monkeypatch) -> None:
    """使用 monkeypatch 隔离外部依赖."""
    # Mock 外部服务
    monkeypatch.setattr(
        "app.services.xxx_service.external_api.call",
        lambda: {"data": "mocked"}
    )

    service = XxxService()
    result = service.process()

    assert result["data"] == "mocked"
```

### 3.4 API 契约测试模板

```python
import pytest

from app import create_app, db
from app.models.user import User


@pytest.mark.unit
def test_xxx_list_contract() -> None:
    """验证 /xxx/api/list 响应结构."""
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        # 创建必要的表
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )

        # 创建测试用户
        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        # 创建已认证的客户端
        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        # 发起请求
        response = client.get("/xxx/api/list")

        # 验证状态码
        assert response.status_code == 200

        # 验证响应结构
        payload = response.get_json()
        assert payload.get("success") is True
        assert payload.get("error") is False
        assert "message" in payload
        assert "timestamp" in payload

        # 验证 data 字段结构
        data = payload.get("data")
        assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())
```

## 4. 测试标记

所有测试必须添加标记：

| 标记 | 用途 | 示例 |
|------|------|------|
| `@pytest.mark.unit` | 单元测试（无外部依赖） | 服务层、工具函数 |
| `@pytest.mark.integration` | 集成测试（需要数据库） | API 端到端 |
| `@pytest.mark.slow` | 执行时间 > 1s | 大数据量测试 |

```python
@pytest.mark.unit
def test_快速测试() -> None:
    ...

@pytest.mark.integration
@pytest.mark.slow
def test_需要数据库的慢测试() -> None:
    ...
```

## 5. 常见问题

### 5.1 测试无法运行

```bash
# 检查是否在项目根目录
pwd  # 应该是 /path/to/WhaleFall

# 检查 pytest 是否安装
uv run pytest --version

# 查看测试发现情况
pytest --collect-only tests/unit/
```

### 5.2 导入错误

```bash
# 确保使用 uv run 运行
uv run pytest -m unit

# 或者激活虚拟环境后运行
source .venv/bin/activate
pytest -m unit
```

### 5.3 数据库相关错误

单元测试使用内存 SQLite，不需要真实数据库。如果遇到数据库错误：

```bash
# 检查环境变量（应该为空或 sqlite:///:memory:）
echo $DATABASE_URL

# 清除环境变量后重试
unset DATABASE_URL
pytest -m unit
```

### 5.4 测试失败但不知道原因

```bash
# 显示完整错误信息
pytest -m unit --tb=long

# 只运行失败的测试
pytest -m unit --lf

# 遇到第一个失败就停止
pytest -m unit -x
```

## 6. 最佳实践

### 6.1 测试命名

```python
# ✅ 好的命名：描述行为和预期
def test_format_size_returns_未采集_when_none():
def test_validate_user_rejects_empty_username():
def test_sync_status_shows_failed_after_timeout():

# ❌ 不好的命名：不清楚测试什么
def test_service():
def test_1():
def test_format():
```

### 6.2 一个测试只验证一件事

```python
# ✅ 好：每个测试验证一个行为
@pytest.mark.unit
def test_format_size_handles_none() -> None:
    assert service._format_size(None) == "未采集"

@pytest.mark.unit
def test_format_size_handles_megabytes() -> None:
    assert service._format_size(512) == "512 MB"

# ❌ 不好：一个测试验证多个行为
@pytest.mark.unit
def test_format_size() -> None:
    assert service._format_size(None) == "未采集"
    assert service._format_size(512) == "512 MB"
    assert service._format_size(2048) == "2.00 GB"
```

### 6.3 不要在测试文件中设置环境变量

```python
# ❌ 错误：在测试文件中设置环境变量
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# ✅ 正确：环境变量只在 tests/conftest.py 中设置
# 测试文件直接导入需要的模块即可
from app.services.xxx import XxxService
```

## 7. 进阶阅读

- 完整测试规范：[docs/standards/testing-standards.md](../standards/testing-standards.md)
- pytest 官方文档：https://docs.pytest.org/
- monkeypatch 使用：https://docs.pytest.org/en/stable/how-to/monkeypatch.html

## 8. 快速参考

```bash
# 日常开发
pytest -m unit              # 运行单元测试
pytest -m unit -v           # 详细输出
pytest -m unit --lf         # 只运行上次失败的

# 调试
pytest -m unit -x           # 遇到失败就停止
pytest -m unit -s           # 显示 print 输出
pytest -m unit --tb=long    # 完整错误信息

# 覆盖率
pytest --cov=app tests/unit/
```
