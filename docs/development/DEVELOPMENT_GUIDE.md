# 鲸落 - 开发指南

## 📋 目录

- [环境搭建](#环境搭建)
- [项目结构](#项目结构)
- [开发规范](#开发规范)
- [代码风格](#代码风格)
- [测试指南](#测试指南)
- [部署流程](#部署流程)
- [常见问题](#常见问题)
- [开发工具](#开发工具)

## 🚀 环境搭建

### 系统要求

- **操作系统**: macOS 10.15+, Ubuntu 18.04+, Windows 10+
- **Python**: 3.11+
- **Node.js**: 16+ (可选，用于前端工具)
- **Git**: 2.20+

### 开发环境安装

#### 1. 克隆项目

```bash
git clone https://github.com/nyealovey/TaifishingV4.git
cd TaifishingV4
```

#### 2. 创建虚拟环境

```bash
# 使用venv
python -m venv venv

# 激活虚拟环境
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 3. 安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 或安装完整依赖（包含所有数据库驱动）
pip install -r requirements-full.txt
```

#### 4. 配置环境变量

```bash
# 复制环境变量模板
cp env.example .env

# 编辑环境变量
vim .env
```

**环境变量配置示例**:
```bash
# 应用配置
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# 数据库配置
DATABASE_URL=postgresql://taifish_user:password@localhost:5432/taifish_dev

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 时区配置
TIMEZONE=Asia/Shanghai

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=userdata/logs
```

#### 5. 初始化数据库

```bash
# 初始化数据库
flask db upgrade

# 创建管理员用户
python scripts/create_admin_user.py

# 初始化示例数据（可选）
python scripts/init_data.py
```

#### 6. 启动Redis

```bash
# macOS (使用Homebrew)
brew services start redis

# Ubuntu/Debian
sudo systemctl start redis

# 或使用Docker
docker run -d -p 6379:6379 redis:7.2.5
```

#### 7. 启动应用

```bash
# 开发模式启动
python app.py

# 或使用脚本启动
./scripts/start_dev.sh
```

访问 http://localhost:5001 查看应用

### Docker开发环境

```bash
# 使用Docker Compose启动完整环境
docker-compose -f docker/compose/docker-compose.yml up -d

# 查看日志
docker-compose -f docker/compose/docker-compose.yml logs -f

# 停止环境
docker-compose -f docker/compose/docker-compose.yml down
```

## 📁 项目结构

```
TaifishV4/
├── app/                          # 应用主目录
│   ├── __init__.py              # 应用初始化
│   ├── config.py                # 配置文件
│   ├── models/                  # 数据模型层
│   │   ├── __init__.py
│   │   ├── user.py             # 用户模型
│   │   ├── instance.py         # 实例模型
│   │   ├── credential.py       # 凭据模型
│   │   ├── account.py          # 账户模型
│   │   ├── task.py             # 任务模型
│   │   ├── log.py              # 日志模型
│   │   ├── global_param.py     # 全局参数模型
│   │   └── sync_data.py        # 同步数据模型
│   ├── routes/                  # 路由控制器层
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证路由
│   │   ├── instances.py        # 实例管理路由
│   │   ├── credentials.py      # 凭据管理路由
│   │   ├── accounts.py         # 账户管理路由
│   │   ├── tasks.py            # 任务管理路由
│   │   ├── dashboard.py        # 仪表板路由
│   │   ├── logs.py             # 日志管理路由
│   │   ├── params.py           # 参数管理路由
│   │   ├── api.py              # API路由
│   │   └── main.py             # 主路由
│   ├── services/                # 业务服务层
│   │   ├── database_service.py # 数据库服务
│   │   ├── database_drivers.py # 数据库驱动
│   │   └── task_executor.py    # 任务执行器
│   ├── utils/                   # 工具类
│   │   ├── logger.py           # 日志工具
│   │   ├── security.py         # 安全工具
│   │   ├── timezone.py         # 时区工具
│   │   ├── cache_manager.py    # 缓存管理
│   │   ├── rate_limiter.py     # 速率限制
│   │   ├── error_handler.py    # 错误处理
│   │   └── env_manager.py      # 环境管理
│   └── templates/               # 模板文件
│       ├── base.html           # 基础模板
│       ├── auth/               # 认证模板
│       ├── instances/          # 实例管理模板
│       ├── credentials/        # 凭据管理模板
│       ├── accounts/           # 账户管理模板
│       ├── tasks/              # 任务管理模板
│       ├── dashboard/          # 仪表板模板
│       ├── logs/               # 日志管理模板
│       ├── params/             # 参数管理模板
│       └── errors/             # 错误页面模板
├── doc/                         # 项目文档
│   ├── spec.md                 # 技术规格文档
│   ├── todolist.md             # 任务清单
│   ├── development/            # 开发文档
│   └── api/                    # API文档
├── docker/                      # Docker配置
│   ├── Dockerfile              # Docker镜像
│   ├── docker-compose.yml      # Docker Compose配置
│   └── scripts/                # Docker脚本
├── scripts/                     # 脚本文件
│   ├── create_admin_user.py    # 创建管理员用户
│   ├── init_data.py            # 初始化数据
│   └── start_dev.sh            # 开发环境启动脚本
├── tests/                       # 测试文件
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   └── e2e/                    # 端到端测试
├── userdata/                    # 用户数据目录
│   ├── logs/                   # 日志文件
│   ├── backups/                # 备份文件
│   └── uploads/                # 上传文件
├── migrations/                  # 数据库迁移
├── requirements.txt             # Python依赖
├── app.py                      # 应用入口
└── README.md                   # 项目说明
```

## 📝 开发规范

### 代码组织原则

1. **分层架构**: 严格按照MVC模式组织代码
2. **模块化**: 每个功能模块独立，低耦合高内聚
3. **可扩展性**: 预留扩展接口，支持功能扩展
4. **可维护性**: 代码清晰，注释完整，易于理解

### 文件命名规范

#### Python文件
- 使用小写字母和下划线
- 模型文件使用单数形式: `user.py`, `instance.py`
- 路由文件使用复数形式: `users.py`, `instances.py`
- 工具类文件使用功能名: `logger.py`, `security.py`

#### HTML模板文件
- 使用小写字母和下划线
- 按功能模块分目录: `auth/login.html`, `instances/list.html`
- 基础模板: `base.html`

#### JavaScript文件
- 使用小写字母和连字符: `user-management.js`
- 或使用下划线: `user_management.js`

### 类命名规范

```python
# 模型类 - 使用大驼峰命名法
class User(db.Model):
    pass

class DatabaseInstance(db.Model):
    pass

# 服务类 - 以Service结尾
class DatabaseService:
    pass

class TaskExecutor:
    pass

# 工具类 - 使用功能名
class Logger:
    pass

class SecurityUtils:
    pass
```

### 函数命名规范

```python
# 公共函数 - 使用小写字母和下划线
def get_user_by_id(user_id):
    pass

def create_database_instance(instance_data):
    pass

# 私有函数 - 以下划线开头
def _validate_user_data(data):
    pass

def _encrypt_password(password):
    pass

# 类方法 - 使用动词开头
def validate_credentials(self, username, password):
    pass

def execute_task(self, task_id):
    pass
```

### 变量命名规范

```python
# 普通变量 - 使用小写字母和下划线
user_name = "admin"
database_url = "postgresql://taifish_user:password@localhost:5432/taifish_dev"
is_active = True

# 常量 - 使用大写字母和下划线
MAX_RETRY_COUNT = 3
DEFAULT_PAGE_SIZE = 10
DATABASE_TYPES = ['postgresql', 'mysql', 'sqlserver']

# 布尔变量 - 使用is_、has_、can_前缀
is_authenticated = True
has_permission = False
can_edit = True

# 列表和字典 - 使用复数形式
users = []
user_credentials = {}
```

## 🎨 代码风格

### Python代码风格

遵循PEP 8规范：

```python
# 导入顺序
import os
import sys
from datetime import datetime

from flask import Flask, request, jsonify
from sqlalchemy import Column, Integer, String

from app.models import User
from app.utils import logger

# 类定义
class UserService:
    """用户服务类"""
    
    def __init__(self):
        self.logger = logger.get_logger(__name__)
    
    def create_user(self, user_data):
        """
        创建用户
        
        Args:
            user_data (dict): 用户数据
            
        Returns:
            User: 创建的用户对象
            
        Raises:
            ValueError: 当用户数据无效时
        """
        if not user_data.get('username'):
            raise ValueError("用户名不能为空")
        
        user = User(
            username=user_data['username'],
            email=user_data.get('email'),
            is_active=True
        )
        
        return user
```

### HTML模板风格

```html
<!-- 使用语义化标签 -->
<div class="container-fluid">
    <div class="row">
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title">
                        <i class="fas fa-users me-2"></i>用户管理
                    </h5>
                </div>
                <div class="card-body">
                    <!-- 内容 -->
                </div>
            </div>
        </div>
    </div>
</div>
```

### JavaScript代码风格

```javascript
// 使用ES6+语法
const UserManager = {
    // 初始化
    init() {
        this.bindEvents();
        this.loadUsers();
    },
    
    // 绑定事件
    bindEvents() {
        $('#create-user-btn').on('click', this.createUser.bind(this));
        $('#edit-user-btn').on('click', this.editUser.bind(this));
    },
    
    // 创建用户
    async createUser(event) {
        event.preventDefault();
        
        try {
            const userData = this.getFormData();
            const response = await this.apiCall('/api/users', 'POST', userData);
            
            if (response.success) {
                this.showAlert('success', '用户创建成功');
                this.loadUsers();
            } else {
                this.showAlert('error', response.message);
            }
        } catch (error) {
            this.showAlert('error', '创建用户失败');
            console.error('Error creating user:', error);
        }
    }
};
```

## 🧪 测试指南

### 测试结构

```
tests/
├── __init__.py
├── conftest.py              # 测试配置
├── unit/                    # 单元测试
│   ├── test_models.py      # 模型测试
│   ├── test_services.py    # 服务测试
│   └── test_utils.py       # 工具测试
├── integration/             # 集成测试
│   ├── test_api.py         # API测试
│   └── test_auth.py        # 认证测试
└── e2e/                     # 端到端测试
    ├── test_user_flow.py   # 用户流程测试
    └── test_admin_flow.py  # 管理员流程测试
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_models.py

# 运行特定测试类
pytest tests/unit/test_models.py::TestUserModel

# 运行特定测试方法
pytest tests/unit/test_models.py::TestUserModel::test_create_user

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html

# 运行测试并显示详细输出
pytest -v

# 运行测试并停止在第一个失败
pytest -x
```

### 测试示例

```python
# tests/unit/test_models.py
import pytest
from app.models import User
from app import db

class TestUserModel:
    """用户模型测试"""
    
    def test_create_user(self, app):
        """测试创建用户"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.is_active is True
    
    def test_user_password_hash(self, app):
        """测试密码哈希"""
        with app.app_context():
            user = User(username='testuser')
            user.set_password('password123')
            
            assert user.check_password('password123') is True
            assert user.check_password('wrongpassword') is False
            assert user.password_hash is not None
```

## 🚀 部署流程

### 开发环境部署

1. **本地开发**
```bash
# 启动Redis
redis-server

# 启动应用
python app.py
```

2. **Docker开发环境**
```bash
docker-compose -f docker/compose/docker-compose.yml up -d
```

### 生产环境部署

1. **使用Docker Compose**
```bash
# 配置生产环境变量
cp env.example .env.prod

# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d
```

2. **手动部署**
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@localhost/taifish

# 初始化数据库
flask db upgrade

# 启动应用
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

### 部署检查清单

- [ ] 环境变量配置正确
- [ ] 数据库连接正常
- [ ] Redis服务运行正常
- [ ] 静态文件路径正确
- [ ] 日志目录权限正确
- [ ] 防火墙端口开放
- [ ] SSL证书配置（生产环境）
- [ ] 备份策略配置

## ❓ 常见问题

### 1. 数据库连接问题

**问题**: 无法连接到数据库
**解决方案**:
```bash
# 检查数据库服务状态
sudo systemctl status postgresql

# 检查连接配置
python -c "from app import db; print(db.engine.url)"

# 测试数据库连接
python scripts/test_database.py
```

### 2. Redis连接问题

**问题**: Redis连接失败
**解决方案**:
```bash
# 检查Redis服务状态
redis-cli ping

# 检查Redis配置
redis-cli config get bind

# 重启Redis服务
sudo systemctl restart redis
```

### 3. 依赖安装问题

**问题**: 某些依赖安装失败
**解决方案**:
```bash
# 更新pip
pip install --upgrade pip

# 安装系统依赖
sudo apt-get install python3-dev libpq-dev

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 4. 数据库迁移问题

**问题**: 数据库迁移失败
**解决方案**:
```bash
# 检查迁移状态
flask db current

# 查看迁移历史
flask db history

# 回滚迁移
flask db downgrade

# 重新生成迁移
flask db migrate -m "描述信息"
```

### 5. 权限问题

**问题**: 文件权限错误
**解决方案**:
```bash
# 修复用户数据目录权限
chmod -R 755 userdata/

# 修复日志目录权限
chmod -R 755 userdata/logs/

# 修复上传目录权限
chmod -R 755 userdata/uploads/
```

## 🛠️ 开发工具

### 推荐IDE

1. **PyCharm Professional** - 功能最全面的Python IDE
2. **Visual Studio Code** - 轻量级，插件丰富
3. **Sublime Text** - 快速，适合轻量开发

### 推荐插件

#### VS Code插件
- Python
- Python Docstring Generator
- GitLens
- Thunder Client
- PostgreSQL管理工具
- Docker

#### PyCharm插件
- Database Navigator
- Redis Plugin
- Docker Integration
- Git Integration

### 调试工具

1. **Flask调试器**
```python
# 在代码中添加断点
import pdb; pdb.set_trace()
```

2. **日志调试**
```python
import logging
logger = logging.getLogger(__name__)
logger.debug("调试信息")
logger.info("信息")
logger.warning("警告")
logger.error("错误")
```

3. **数据库调试**
```python
# 查看SQL查询
from sqlalchemy import event
from sqlalchemy.engine import Engine
import logging

logging.basicConfig()
logger = logging.getLogger("sqlalchemy.engine")
logger.setLevel(logging.INFO)
```

### 性能分析工具

1. **Flask-Profiler**
```python
from flask_profiler import Profiler

app.config["flask_profiler"] = {
    "enabled": True,
    "storage": {
        "engine": "postgresql",
        "db_file": "profiler.db"
    }
}

profiler = Profiler()
profiler.init_app(app)
```

2. **Memory Profiler**
```bash
pip install memory-profiler
python -m memory_profiler app.py
```

## 📚 学习资源

### 官方文档
- [Flask官方文档](https://flask.palletsprojects.com/)
- [SQLAlchemy官方文档](https://docs.sqlalchemy.org/)
- [APScheduler官方文档](https://apscheduler.readthedocs.io/)
- [Redis官方文档](https://redis.io/documentation)

### 教程资源
- [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)
- [SQLAlchemy Tutorial](https://docs.sqlalchemy.org/en/14/tutorial/)
- [APScheduler Tutorial](https://apscheduler.readthedocs.io/en/stable/userguide.html#getting-started)

### 最佳实践
- [Flask Best Practices](https://exploreflask.com/)
- [SQLAlchemy Best Practices](https://docs.sqlalchemy.org/en/14/orm/session_basics.html)
- [Python Best Practices](https://docs.python-guide.org/)

---

**最后更新**: 2025-09-08  
**维护者**: 鲸落开发团队
