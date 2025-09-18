# 代码质量工具使用指南

## 概述

本项目集成了严格的代码质量工具链，包括：
- **Ruff**: 快速 Python 代码检查和格式化
- **Mypy**: 静态类型检查
- **Bandit**: 安全漏洞扫描
- **Black**: 代码格式化
- **pre-commit**: 自动化代码质量检查

## 工具配置

### 1. Ruff 配置 (ruff.toml)

```toml
# 基础配置
target-version = "py313"
line-length = 88
indent-width = 4

# 检查规则
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
    "TCH", # flake8-type-checking
    "Q",   # flake8-quotes
    "RET", # flake8-return
    "SLF", # flake8-self
    "ANN", # flake8-annotations
    "G",   # flake8-logging-format
    "PT",  # flake8-pytest-style
    "INP", # flake8-no-pep420
    "EM",  # flake8-errmsg
]

# 忽略规则
ignore = [
    "E501",  # 行长度限制
    "ANN101", # 缺少类型注解
    "ANN102", # 缺少返回类型注解
    "ANN401", # 动态类型
    "S101",   # 断言使用
    "S104",   # 硬编码绑定
    "B008",   # 默认参数
    "B904",   # 异常处理
    "PLR0913", # 参数过多
    "PLR0912", # 分支过多
    "PLR0915", # 语句过多
    "C901",    # 复杂度
    "RET504",  # 不必要的赋值
    "SIM108",  # 条件表达式
    "EM101",   # 原始字符串
]

# 排除文件
exclude = [
    "migrations/",
    "userdata/",
    "tests/",
    "venv/",
    ".venv/",
    "__pycache__/",
    "*.pyc",
    ".git/",
    "node_modules/",
]
```

### 2. Mypy 配置 (mypy.ini)

```ini
[mypy]
python_version = 3.13
strict = True
warn_return_any = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
show_error_codes = True
pretty = True
color_output = True
error_summary = True

# 排除文件
exclude = migrations/|userdata/|tests/|venv/|\.venv/|__pycache__/|.*\.pyc|\.git/|node_modules/

# 模块特定设置
[mypy-app.*]
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True

# 第三方库设置
[mypy-flask.*]
ignore_missing_imports = True
```

### 3. Black 配置 (pyproject.toml)

```toml
[tool.black]
line-length = 88
target-version = ['py313']
include = '\.pyi?$'
extend-exclude = '''
/(
  migrations
  | userdata
  | tests
  | venv
  | \.venv
  | __pycache__
  | \.git
  | node_modules
)/
'''
```

### 4. Bandit 配置 (pyproject.toml)

```toml
[tool.bandit]
exclude_dirs = ["migrations", "userdata", "tests", "venv", ".venv", "__pycache__", ".git", "node_modules"]
skips = ["B101", "B601"]
```

## 使用方法

### 1. 运行所有检查

```bash
# 使用统一脚本
uv run python scripts/quality_check.py

# 或分别运行
uv run ruff check app/
uv run mypy app/
uv run bandit -r app/
uv run black app/ --check
```

### 2. 自动修复

```bash
# Ruff 自动修复
uv run ruff check app/ --fix

# Black 格式化
uv run black app/

# 组合命令
uv run ruff check app/ --fix && uv run black app/
```

### 3. 检查特定文件

```bash
# 检查单个文件
uv run ruff check app/models/user.py
uv run mypy app/models/user.py
uv run bandit app/models/user.py
uv run black app/models/user.py --check
```

### 4. 生成报告

```bash
# 生成详细报告
uv run ruff check app/ --output-format=json > ruff_report.json
uv run mypy app/ --junit-xml mypy_report.xml
uv run bandit -r app/ -f json -o bandit_report.json
```

## 常见问题解决

### 1. Ruff 问题

**问题**: 行长度超限
```python
# 错误
very_long_variable_name = some_function_call_with_many_parameters(param1, param2, param3, param4, param5)

# 修复
very_long_variable_name = some_function_call_with_many_parameters(
    param1, param2, param3, param4, param5
)
```

**问题**: 缺少类型注解
```python
# 错误
def get_user(user_id):
    return User.query.get(user_id)

# 修复
def get_user(user_id: int) -> Optional[User]:
    return User.query.get(user_id)
```

### 2. Mypy 问题

**问题**: 缺少返回类型注解
```python
# 错误
def process_data(data):
    return data.upper()

# 修复
def process_data(data: str) -> str:
    return data.upper()
```

**问题**: 动态类型
```python
# 错误
def handle_request(request):
    if isinstance(request, dict):
        return request.get('data')

# 修复
from typing import Union, Dict, Any

def handle_request(request: Union[Dict[str, Any], str]) -> Any:
    if isinstance(request, dict):
        return request.get('data')
    return None
```

### 3. Bandit 问题

**问题**: 硬编码密码
```python
# 错误
SECRET_KEY = "hardcoded-secret"

# 修复
import os
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
```

**问题**: 绑定所有接口
```python
# 错误
app.run(host="0.0.0.0", port=8000)

# 修复
app.run(host="127.0.0.1", port=8000)  # 开发环境
# 或使用环境变量
app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)))
```

## 最佳实践

### 1. 开发流程

1. **编写代码** → 遵循编码规范
2. **运行检查** → `uv run python scripts/quality_check.py`
3. **修复问题** → 根据工具提示修复
4. **提交代码** → 确保所有检查通过

### 2. 类型注解

```python
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

def process_users(
    users: List[Dict[str, Any]],
    active_only: bool = True
) -> Dict[str, int]:
    """处理用户数据并返回统计信息"""
    if active_only:
        users = [u for u in users if u.get('active', False)]

    return {
        'total': len(users),
        'processed': len([u for u in users if u.get('processed', False)])
    }
```

### 3. 错误处理

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def safe_get_user(user_id: int) -> Optional[User]:
    """安全获取用户，包含错误处理"""
    try:
        return User.query.get(user_id)
    except Exception as e:
        logger.error(f"获取用户失败: user_id={user_id}, error={e}")
        return None
```

### 4. 安全编码

```python
import os
import secrets
from werkzeug.security import generate_password_hash

# 使用环境变量
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY 环境变量未设置")

# 生成安全密码
def generate_secure_password(length: int = 12) -> str:
    return secrets.token_urlsafe(length)

# 密码哈希
def hash_password(password: str) -> str:
    return generate_password_hash(password)
```

## 持续集成

### GitHub Actions 配置

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'

    - name: Install dependencies
      run: |
        pip install uv
        uv sync --dev

    - name: Run Ruff
      run: uv run ruff check app/

    - name: Run Mypy
      run: uv run mypy app/

    - name: Run Bandit
      run: uv run bandit -r app/

    - name: Run Black
      run: uv run black app/ --check
```

## 工具版本

- **Ruff**: 0.13.0
- **Mypy**: 1.13.0
- **Bandit**: 1.8.6
- **Black**: 24.10.0
- **pre-commit**: 4.0.1

## 总结

这套代码质量工具链确保了：
- **代码一致性**: Black 统一格式化
- **类型安全**: Mypy 静态类型检查
- **代码质量**: Ruff 全面代码检查
- **安全性**: Bandit 安全漏洞扫描
- **自动化**: pre-commit 自动检查

通过遵循这些工具的建议和最佳实践，可以显著提高代码质量、可维护性和安全性。
