# 鲸落 (TaifishV4) 开发环境搭建指南

## 📋 开发环境概览

本指南将帮助您快速搭建鲸落系统的开发环境，包括本地开发环境配置、代码规范、测试框架等。

### 开发环境要求
- **Python**: 3.11+
- **Node.js**: 16+ (可选，用于前端工具)
- **Git**: 2.30+
- **IDE**: VS Code / PyCharm / Cursor
- **数据库**: PostgreSQL 13+
- **缓存**: Redis 6.0+

## 🚀 快速开始

### 1. 克隆项目
```bash
# 克隆仓库
git clone https://github.com/nyealovey/TaifishingV4.git
cd TaifishingV4

# 查看项目结构
ls -la
```

### 2. 创建虚拟环境
```bash
# 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 安装依赖
```bash
# 安装开发依赖
pip install -r requirements.txt

# 安装开发工具
pip install -r requirements-dev.txt
```

### 4. 配置环境变量
```bash
# 复制环境配置文件
cp env.development .env

# 编辑环境配置
nano .env
```

#### 环境变量配置示例
```bash
# 应用配置
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/whalefalling_dev
REDIS_URL=redis://localhost:6379/0

# 调试配置
DEBUG=True
TESTING=False

# 日志配置
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# 邮件配置 (可选)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### 5. 数据库设置
```bash
# 创建PostgreSQL数据库
createdb whalefalling_dev

# 运行数据库迁移
flask db upgrade

# 初始化测试数据
python scripts/init_dev_data.py
```

### 6. 启动开发服务器
```bash
# 启动Flask开发服务器
flask run

# 或者使用Python直接启动
python app.py
```

访问 `http://localhost:5000` 查看应用。

## 🛠️ 开发工具配置

### VS Code 配置

#### 安装推荐扩展
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.flake8",
    "ms-python.black-formatter",
    "ms-python.isort",
    "ms-python.mypy-type-checker",
    "ms-vscode.vscode-json",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode"
  ]
}
```

#### 工作区配置
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm 配置

#### 项目解释器
1. 打开 `File` -> `Settings` -> `Project` -> `Python Interpreter`
2. 选择虚拟环境中的Python解释器
3. 确保路径指向 `venv/bin/python`

#### 代码检查
1. 启用 `File` -> `Settings` -> `Editor` -> `Inspections`
2. 配置Python检查规则
3. 启用Black代码格式化

## 📝 代码规范

### Python 代码规范

#### 代码格式化
```bash
# 使用Black格式化代码
black app/

# 使用isort排序导入
isort app/

# 检查代码质量
ruff check app/
```

#### 类型检查
```bash
# 运行MyPy类型检查
mypy app/

# 生成类型检查报告
mypy app/ --html-report mypy-report
```

#### 代码质量检查
```bash
# 运行Ruff检查
ruff check app/

# 自动修复可修复的问题
ruff check app/ --fix

# 运行安全检查
bandit -r app/
```

### 提交规范

#### Git 提交信息格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

#### 提交类型
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

#### 提交示例
```bash
git commit -m "feat(tags): 添加批量分配标签功能

- 实现标签批量分配接口
- 添加前端批量操作界面
- 支持多实例标签分配

Closes #123"
```

## 🧪 测试框架

### 测试环境配置

#### 测试数据库配置
```bash
# 创建测试数据库
createdb whalefalling_test

# 设置测试环境变量
export TESTING=True
export DATABASE_URL=postgresql://user:password@localhost:5432/whalefalling_test
```

#### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_models.py

# 运行特定测试函数
pytest tests/unit/test_models.py::test_user_creation

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 测试结构

```
tests/
├── __init__.py
├── conftest.py              # 测试配置和fixtures
├── unit/                    # 单元测试
│   ├── test_models.py       # 模型测试
│   ├── test_services.py     # 服务测试
│   ├── test_utils.py        # 工具测试
│   └── test_routes.py       # 路由测试
└── integration/             # 集成测试
    ├── test_api.py          # API测试
    └── test_database.py     # 数据库测试
```

### 测试示例

#### 单元测试示例
```python
import pytest
from app.models.user import User
from app import db

class TestUserModel:
    def test_user_creation(self, app):
        """测试用户创建"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                password_hash='hashed_password'
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
```

#### API测试示例
```python
import pytest
from app import create_app

class TestAuthAPI:
    def test_login_success(self, client):
        """测试登录成功"""
        response = client.post('/auth/login', json={
            'username': 'admin',
            'password': 'admin123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'token' in data['data']
```

## 🔧 开发工具

### 数据库管理

#### 数据库迁移
```bash
# 创建迁移文件
flask db migrate -m "Add user table"

# 应用迁移
flask db upgrade

# 回滚迁移
flask db downgrade
```

#### 数据库管理工具
```bash
# 使用psql连接数据库
psql -h localhost -U user -d whalefalling_dev

# 使用pgAdmin (图形界面)
# 下载并安装pgAdmin
# 连接本地PostgreSQL数据库
```

### 缓存管理

#### Redis操作
```bash
# 连接Redis
redis-cli

# 查看所有键
KEYS *

# 清空缓存
FLUSHALL

# 查看内存使用
INFO memory
```

### 日志管理

#### 查看日志
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看访问日志
tail -f logs/access.log
```

## 🚀 开发工作流

### 1. 功能开发流程

#### 创建功能分支
```bash
# 从main分支创建功能分支
git checkout -b feature/new-feature

# 推送分支到远程
git push -u origin feature/new-feature
```

#### 开发过程
```bash
# 1. 编写代码
# 2. 运行测试
pytest

# 3. 代码格式化
black app/
isort app/

# 4. 代码检查
ruff check app/
mypy app/

# 5. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 6. 推送代码
git push
```

#### 创建Pull Request
1. 在GitHub上创建Pull Request
2. 填写详细的描述和变更说明
3. 等待代码审查
4. 合并到main分支

### 2. Bug修复流程

#### 创建修复分支
```bash
# 从main分支创建修复分支
git checkout -b fix/bug-description

# 修复bug
# 编写测试用例
# 提交修复
git commit -m "fix: 修复bug描述"
```

### 3. 发布流程

#### 版本发布
```bash
# 1. 更新版本号
# 编辑 pyproject.toml
version = "1.1.1"

# 2. 更新CHANGELOG.md
# 添加新版本说明

# 3. 创建发布标签
git tag -a v1.1.1 -m "Release version 1.1.1"
git push origin v1.1.1

# 4. 创建GitHub Release
# 在GitHub上创建Release
```

## 🔍 调试技巧

### 应用调试

#### Flask调试模式
```python
# 在app.py中启用调试模式
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

#### 使用调试器
```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或者使用ipdb (更友好的调试器)
import ipdb; ipdb.set_trace()
```

### 数据库调试

#### SQL查询调试
```python
# 启用SQL查询日志
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

#### 数据库查询分析
```sql
-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM users WHERE username = 'admin';

-- 查看表统计信息
SELECT * FROM pg_stat_user_tables;
```

### 前端调试

#### 浏览器开发者工具
1. 打开浏览器开发者工具 (F12)
2. 查看Console面板的错误信息
3. 使用Network面板分析请求
4. 使用Elements面板检查DOM结构

#### JavaScript调试
```javascript
// 在JavaScript中添加调试信息
console.log('Debug info:', data);

// 使用断点调试
debugger;
```

## 📚 学习资源

### 官方文档
- [Flask官方文档](https://flask.palletsprojects.com/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- [Bootstrap文档](https://getbootstrap.com/docs/)
- [jQuery文档](https://api.jquery.com/)

### 开发工具文档
- [pytest文档](https://docs.pytest.org/)
- [Black文档](https://black.readthedocs.io/)
- [MyPy文档](https://mypy.readthedocs.io/)
- [Ruff文档](https://docs.astral.sh/ruff/)

### 项目相关
- [项目README](../README.md)
- [API文档](../api/README.md)
- [部署指南](../deployment/PRODUCTION_DEPLOYMENT.md)

## 🤝 贡献指南

### 贡献流程
1. Fork项目仓库
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request
5. 参与代码审查

### 代码审查标准
- 代码符合项目规范
- 测试覆盖率达标
- 文档更新完整
- 性能影响评估
- 安全性检查通过

## 📞 获取帮助

### 问题反馈
- 在GitHub Issues中提交问题
- 提供详细的错误信息和复现步骤
- 包含相关的日志和配置信息

### 讨论交流
- 在GitHub Discussions中参与讨论
- 分享开发经验和技巧
- 提出改进建议

---

**最后更新**: 2025-09-25  
**文档版本**: v1.1.1  
**维护团队**: TaifishingV4 Team
