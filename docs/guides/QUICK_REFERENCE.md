# 鲸落 - 快速参考

## 🚀 快速启动

### 开发环境
```bash
# 1. 克隆项目
git clone https://github.com/nyealovey/TaifishingV4.git
cd TaifishingV4

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 3. 安装依赖 (使用uv)
uv sync

# 4. 配置环境
cp env.example .env
# 编辑 .env 文件

# 5. 初始化数据库
flask db upgrade
python scripts/create_admin_user.py

# 6. 启动Redis
redis-server  # 或使用Docker: docker run -d -p 6379:6379 redis:7.2.5

# 7. 启动应用
uv run python app.py
```

### Docker环境
```bash
# 启动完整环境
docker-compose -f docker/compose/docker-compose.yml up -d

# 查看日志
docker-compose -f docker/compose/docker-compose.yml logs -f
```

## 📁 项目结构速览

```
TaifishV4/
├── app/                    # 应用主目录
│   ├── models/            # 数据模型
│   ├── routes/            # 路由控制器
│   ├── services/          # 业务服务
│   ├── utils/             # 工具类
│   └── templates/         # 模板文件
├── doc/                   # 项目文档
├── scripts/               # 脚本文件
├── tests/                 # 测试文件
├── userdata/              # 用户数据
└── migrations/            # 数据库迁移
```

## 🔧 常用命令

### 数据库操作
```bash
# 创建迁移
flask db migrate -m "描述信息"

# 应用迁移
flask db upgrade

# 回滚迁移
flask db downgrade

# 查看迁移历史
flask db history

# 查看当前版本
flask db current
```

### 开发工具
```bash
# 创建管理员用户
python scripts/create_admin_user.py

# 初始化示例数据
python scripts/init_data.py

# 测试数据库连接
python scripts/test_database.py

# 运行测试
pytest

# 运行特定测试
pytest tests/unit/test_models.py
```

### Docker操作
```bash
# 构建镜像
docker build -t taifish .

# 运行容器
docker run -p 5001:5001 taifish

# 查看容器日志
docker logs <container_id>

# 进入容器
docker exec -it <container_id> /bin/bash
```

## 🌐 访问地址

- **应用首页**: http://localhost:5001
- **登录页面**: http://localhost:5001/auth/login
- **API文档**: http://localhost:5001/api/health
- **管理后台**: http://localhost:5001/admin

## 👤 默认账户

- **用户名**: admin
- **密码**: Admin123
- **邮箱**: admin@taifish.com

## 📊 核心功能

### 1. 用户管理
- 用户注册、登录、登出
- 密码修改和用户资料
- 基于角色的权限控制

### 2. 实例管理
- 支持PostgreSQL、MySQL、SQL Server、Oracle
- 实例创建、编辑、删除
- 连接测试和状态监控

### 3. 凭据管理
- 安全的数据库连接凭据存储
- 凭据与实例关联管理
- 密码加密存储

### 4. 账户管理
- 数据库用户账户同步
- 按数据库类型筛选
- 账户状态和权限管理

### 5. 任务管理
- 高度可定制化的任务管理
- 内置同步任务模板
- 支持自定义Python代码执行

### 6. 系统监控
- 实时监控仪表板
- 系统健康检查
- 操作日志记录

## 🔑 环境变量

### 必需配置
```bash
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DATABASE_URL=postgresql://taifish_user:password@localhost:5432/taifish_dev
REDIS_URL=redis://localhost:6379/0
```

### 可选配置
```bash
FLASK_ENV=development
TIMEZONE=Asia/Shanghai
LOG_LEVEL=INFO
```

## 🗄️ 数据库配置

### PostgreSQL (主数据库)
```bash
DATABASE_URL=postgresql://taifish_user:password@localhost:5432/taifish_dev
```

### PostgreSQL (生产环境)
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/taifish
```

### MySQL
```bash
DATABASE_URL=mysql://user:password@localhost:3306/taifish
```

## 🔌 API接口

### 认证接口
- `POST /auth/login` - 用户登录
- `POST /auth/logout` - 用户登出
- `POST /auth/register` - 用户注册

### 实例管理
- `GET /instances/` - 获取实例列表
- `POST /instances/create` - 创建实例
- `GET /instances/<id>` - 获取实例详情
- `PUT /instances/<id>/edit` - 更新实例
- `DELETE /instances/<id>/delete` - 删除实例

### 任务管理
- `GET /tasks/` - 获取任务列表
- `POST /tasks/create` - 创建任务
- `POST /tasks/create-builtin` - 创建内置任务
- `POST /tasks/execute-all` - 批量执行任务

### 健康检查
- `GET /api/health` - 系统健康检查

## 🐛 常见问题

### 1. 端口被占用
```bash
# 查看端口占用
lsof -i :5001

# 杀死进程
kill -9 <PID>
```

### 2. 数据库连接失败
```bash
# 检查数据库服务
sudo systemctl status postgresql

# 测试连接
python scripts/test_database.py
```

### 3. Redis连接失败
```bash
# 检查Redis服务
redis-cli ping

# 重启Redis
sudo systemctl restart redis
```

### 4. 依赖安装失败
```bash
# 更新pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## 📝 开发规范

### 代码风格
- Python: 遵循PEP 8规范
- HTML: 使用语义化标签
- JavaScript: 使用ES6+语法

### 命名规范
- 文件: 小写字母和下划线
- 类: 大驼峰命名法
- 函数: 小写字母和下划线
- 变量: 小写字母和下划线

### 提交规范
```bash
# 功能开发
git commit -m "feat: 添加用户管理功能"

# 问题修复
git commit -m "fix: 修复登录验证问题"

# 文档更新
git commit -m "docs: 更新API文档"

# 代码重构
git commit -m "refactor: 重构数据库服务层"
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 测试数据
```bash
# 创建测试用户
python scripts/create_test_user.py

# 创建测试实例
python scripts/create_test_instance.py

# 创建测试任务
python scripts/create_test_task.py
```

## 📚 文档链接

- [技术规格文档](doc/spec.md)
- [任务清单](doc/todolist.md)
- [开发指南](doc/development/DEVELOPMENT_GUIDE.md)
- [API文档](doc/api/README.md)
- [部署文档](doc/deployment/)

## 🆘 获取帮助

1. **查看日志**: `userdata/logs/`
2. **检查配置**: `.env` 文件
3. **运行测试**: `pytest`
4. **查看文档**: `doc/` 目录
5. **提交问题**: [GitHub Issues](https://github.com/nyealovey/TaifishingV4/issues)

---

**鲸落** - 让数据库管理更简单！ 🐟