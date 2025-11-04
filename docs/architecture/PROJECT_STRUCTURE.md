# 鲸落 (TaifishV4) 项目结构

## 📁 项目根目录

```
TaifishV4/
├── app/                    # 应用主目录
├── docs/                   # 项目文档
├── tests/                  # 测试文件
├── scripts/                # 工具脚本
├── sql/                    # SQL脚本
├── nginx/                  # Nginx配置
├── migrations/             # 数据库迁移
├── userdata/               # 用户数据目录
├── instance/               # 实例配置
├── oracle_client/          # Oracle客户端
├── app.py                  # 应用入口
├── wsgi.py                 # WSGI入口
├── requirements.txt        # Python依赖
├── pyproject.toml          # 项目配置
├── CHANGELOG.md            # 更新日志
├── README.md               # 项目说明
└── LICENSE                 # 许可证
```

## 🏗️ 应用架构 (app/)

### 核心模块

```
app/
├── __init__.py             # 应用工厂
├── config.py               # 配置管理
├── constants.py            # 常量定义
├── scheduler.py            # 任务调度器
├── tasks.py                # 任务定义
├── models/                 # 数据模型层
├── routes/                 # 路由控制器层
├── services/               # 业务服务层
├── utils/                  # 工具类
├── middleware/             # 中间件
├── static/                 # 静态资源
├── templates/              # 模板文件
└── config/                 # 配置文件
```

### 数据模型层 (models/)

```
models/
├── __init__.py
├── user.py                 # 用户模型
├── instance.py             # 数据库实例模型
├── credential.py           # 凭据模型
├── tag.py                  # 标签模型
├── account_classification.py # 账户分类模型
├── classification_batch.py  # 分类批次模型
├── permission_config.py    # 权限配置模型
├── sync_session.py         # 同步会话模型
├── sync_instance_record.py # 同步实例记录模型
├── account_change_log.py   # 账户变更日志模型
├── current_account_sync_data.py # 当前账户同步数据模型
├── base_sync_data.py       # 基础同步数据模型
├── database_type_config.py # 数据库类型配置模型
├── global_param.py         # 全局参数模型
└── unified_log.py          # 统一日志模型
```

### 路由控制器层 (routes/)

```
routes/
├── __init__.py
├── main.py                 # 主页面路由
├── auth.py                 # 认证路由
├── dashboard.py            # 仪表板路由
├── instance.py            # 实例管理路由（基础信息）
├── instance_detail.py   # 实例详情相关路由（账户、容量等）
├── instance_statistics.py   # 实例容量与统计路由
├── instance_stats.py      # 实例聚合统计页面与API
├── credentials.py          # 凭据管理路由
├── tags.py                 # 标签管理路由
├── account_classification.py # 账户分类路由
├── account.py              # 账户管理路由
├── account_stat.py         # 账户统计路由
├── account_sync.py         # 账户同步路由
├── sync_sessions.py        # 同步会话路由
├── logs.py                 # 日志管理路由
├── scheduler.py            # 任务调度路由
├── cache.py               # 缓存管理路由
├── database_types.py       # 数据库类型路由
├── storage.py              # 存储同步路由
├── users.py                # 用户管理路由
└── health.py               # 健康检查路由
```

### 业务服务层 (services/)

```
services/
├── __init__.py
├── account_sync/
│   ├── __init__.py
│   ├── account_sync_service.py      # 账户同步统一入口
│   ├── coordinator.py               # 两阶段协调器
│   ├── inventory_manager.py         # 账户清单同步
│   ├── permission_manager.py        # 权限快照同步
│   ├── account_query_service.py     # 查询辅助
│   └── adapters/
│       ├── base_adapter.py          # 账户同步适配器基类
│       ├── factory.py
│       ├── mysql_adapter.py
│       ├── postgresql_adapter.py
│       ├── sqlserver_adapter.py
│       └── oracle_adapter.py
├── sync_session_service.py # 同步会话服务
├── sync_data_manager.py    # 同步数据管理
├── database_type_service.py # 数据库类型服务
├── cache_service.py        # 缓存管理器
├── account_classification_service.py # 优化账户分类服务
├── classification_batch_service.py # 分类批次服务
├── connection_adapters/    # 连接适配器
│   ├── __init__.py
│   ├── connection_factory.py
│   └── connection_test_service.py


```

### 工具类 (utils/)

```
utils/
├── __init__.py
├── decorators.py           # 装饰器
├── data_validator.py       # 数据与安全验证工具
├── formatters.py           # 格式化工具
├── helpers.py              # 辅助函数
├── exceptions.py           # 自定义异常
├── structlog_config.py     # 结构化日志配置
├── database_utils.py       # 数据库工具
├── cache_utils.py          # 缓存工具
├── file_utils.py           # 文件工具
├── time_utils.py           # 时间工具
├── string_utils.py         # 字符串工具
├── json_utils.py           # JSON工具
├── crypto_utils.py         # 加密工具
├── email_utils.py          # 邮件工具
├── http_utils.py           # HTTP工具
├── config_utils.py         # 配置工具
├── log_utils.py            # 日志工具
├── test_utils.py           # 测试工具
├── migration_utils.py      # 迁移工具
├── sync_utils.py           # 同步工具
├── classification_utils.py # 分类工具
├── permission_utils.py     # 权限工具
├── tag_utils.py            # 标签工具
├── instance_utils.py       # 实例工具
└── scheduler_utils.py      # 调度器工具
```

### 静态资源 (static/)

```
static/
├── css/                    # 样式文件
│   ├── pages/              # 页面样式
│   ├── components/         # 组件样式
│   └── vendor/             # 第三方样式
├── js/                     # JavaScript文件
│   ├── pages/              # 页面脚本
│   ├── components/         # 组件脚本
│   └── vendor/             # 第三方脚本
├── img/                    # 图片资源
└── vendor/                 # 第三方资源
```

### 模板文件 (templates/)

```
templates/
├── base.html               # 基础模板
├── about.html              # 关于页面
├── auth/                   # 认证模板
│   ├── login.html
│   └── change_password.html
├── admin/                  # 管理模板
│   └── management.html
├── dashboard/              # 仪表板模板
│   └── overview.html
├── instances/              # 实例管理模板
│   ├── list.html
│   ├── create.html
│   ├── edit.html
│   ├── detail.html
│   └── statistics.html
├── credentials/            # 凭据管理模板
│   ├── list.html
│   ├── create.html
│   └── edit.html
├── tags/                   # 标签管理模板
│   ├── index.html
│   └── batch_assign.html
├── accounts/               # 账户管理模板
│   ├── list.html
│   ├── sync_records.html
│   └── static.html
├── sync_sessions/          # 同步会话模板
│   └── management.html
├── logs/                   # 日志模板
│   └── dashboard.html
├── users/                  # 用户管理模板
│   └── management.html
├── account_classification/ # 账户分类模板
│   └── account_classification.html
└── components/             # 组件模板
    ├── filters/            # 统一筛选宏
    │   └── macros.html
    └── tag_selector.html
```

## 🗄️ 数据库结构

### 核心表

| 表名 | 描述 | 主要字段 |
|------|------|----------|
| users | 用户表 | id, username, email, role, is_active |
| instances | 数据库实例表 | id, name, host, port, db_type, status |
| credentials | 凭据表 | id, instance_id, username, password, credential_type |
| tags | 标签表 | id, name, display_name, category, color, description |
| account_classifications | 账户分类表 | id, name, description, db_type, is_active |
| classification_batches | 分类批次表 | id, name, description, status, created_at |
| permission_configs | 权限配置表 | id, name, db_type, rules, is_active |
| sync_sessions | 同步会话表 | id, name, status, start_time, end_time |
| sync_instance_records | 同步实例记录表 | id, session_id, instance_id, status, records_count |
| account_change_logs | 账户变更日志表 | id, account_id, change_type, old_value, new_value |
| current_account_sync_data | 当前账户同步数据表 | id, instance_id, account_data, last_sync_time |
| base_sync_data | 基础同步数据表 | id, instance_id, sync_data, sync_time |
| database_type_configs | 数据库类型配置表 | id, name, display_name, driver, port |
| global_params | 全局参数表 | id, key, value, description |
| logs | 日志表 | id, level, module, message, timestamp |

## 🔧 配置文件

### 应用配置 (config/)

```
config/
├── account_filters.yaml    # 账户过滤规则配置
├── scheduler_tasks.yaml    # 调度器任务配置
└── sqlserver_sync_performance.yaml # SQL Server同步性能配置
```

### 环境配置

```
env.development             # 开发环境配置
env.production              # 生产环境配置
```

### 项目配置

```
pyproject.toml              # 项目元数据
requirements.txt            # 生产环境依赖
requirements-prod.txt       # 生产环境依赖
ruff.toml                   # 代码检查配置
mypy.ini                    # 类型检查配置
pytest.ini                  # 测试配置
```

## 🐳 容器化配置

### Docker配置

```
Dockerfile.dev              # 开发环境Dockerfile
Dockerfile.prod             # 生产环境Dockerfile
docker-compose.dev.yml      # 开发环境Docker Compose
docker-compose.flask-only.yml # Flask专用Docker Compose
docker-compose.prod.yml     # 生产环境Docker Compose
```

### Nginx配置

```
nginx/
├── conf.d/                 # Nginx配置目录
├── error_pages/            # 错误页面
├── gunicorn/               # Gunicorn配置
├── local/                  # 本地SSL证书
├── sites-available/        # 可用站点配置
├── ssl/                    # SSL证书
└── supervisor/             # Supervisor配置
```

## 🧪 测试结构

```
tests/
├── __init__.py
├── conftest.py             # 测试配置
├── unit/                   # 单元测试
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_utils.py
│   └── test_routes.py
└── integration/            # 集成测试
    ├── test_api.py
    └── test_database.py
```

## 📜 脚本工具 (scripts/)

```
scripts/
├── database/               # 数据库脚本
├── deployment/             # 部署脚本
├── dev/                    # 开发脚本
├── docker/                 # Docker脚本
├── nginx/                  # Nginx脚本
├── oracle/                 # Oracle脚本
├── quality/                # 质量检查脚本
├── security/               # 安全脚本
└── README.md               # 脚本说明
```

## 📊 数据目录 (userdata/)

```
userdata/
├── backups/                # 备份数据
├── dynamic_tasks/          # 动态任务
├── exports/                # 导出数据
├── log/                    # 日志文件
├── postgres/               # PostgreSQL数据
└── scheduler.db            # 调度器数据库
```

## 🔄 数据迁移 (migrations/)

```
migrations/
├── alembic.ini             # Alembic配置
├── env.py                  # 迁移环境
├── script.py.mako          # 迁移脚本模板
└── versions/               # 迁移版本
    ├── 001_initial_migration.py
    ├── 002_add_tags_table.py
    └── ...
```

## 📚 文档结构 (docs/)

```
docs/
├── README.md               # 文档首页
├── architecture/           # 架构文档
├── features/               # 功能文档
├── development/            # 开发文档
├── database/               # 数据库文档
├── api/                    # API文档
├── deployment/             # 部署文档
├── security/               # 安全文档
├── project/                # 项目文档
├── reports/                # 报告文档
├── guides/                 # 用户指南
├── constants/              # 常量文档
├── analysis/               # 分析文档
├── fixes/                  # 修复文档
└── releases/               # 发布文档
```

## 🎯 核心设计原则

### 1. 分层架构
- **模型层 (Models)**: 数据模型和业务实体
- **服务层 (Services)**: 业务逻辑和数据处理
- **控制器层 (Routes)**: 请求处理和响应
- **视图层 (Templates)**: 用户界面展示

### 2. 模块化设计
- **功能模块**: 按业务功能划分模块
- **工具模块**: 通用工具和辅助函数
- **配置模块**: 配置管理和环境变量
- **中间件模块**: 横切关注点处理

### 3. 可扩展性
- **插件化**: 支持数据库类型扩展
- **适配器模式**: 不同数据库的适配器
- **工厂模式**: 对象创建和实例化
- **策略模式**: 算法和策略的可替换性

### 4. 可维护性
- **代码规范**: 统一的代码风格和规范
- **文档完整**: 详细的文档和注释
- **测试覆盖**: 全面的单元测试和集成测试
- **错误处理**: 完善的异常处理和日志记录

---

**最后更新**: 2025-10-31  
**文档版本**: v1.2.0  
**维护团队**: TaifishingV4 Team
