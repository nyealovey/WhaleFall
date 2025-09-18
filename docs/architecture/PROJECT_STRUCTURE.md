# 鲸落 (TaifishV4) - 项目结构文档

## 项目概述

鲸落是一个基于Flask的DBA数据库管理Web应用，提供多数据库实例管理、账户管理、任务调度、日志监控等功能。支持PostgreSQL、MySQL、SQL Server、Oracle等主流数据库。

## 技术栈

- **后端**: Flask 3.0.3, SQLAlchemy 1.4.54, APScheduler 3.10.4
- **前端**: Bootstrap 5.3.2, jQuery 3.7.1, Chart.js 4.4.0
- **数据库**: PostgreSQL (主数据库), MySQL, SQL Server, Oracle
- **缓存**: Redis 5.0.7
- **任务调度**: APScheduler (替代Celery)
- **Python版本**: 3.13+

## 项目目录结构

```
TaifishV4/
├── app/                           # Flask应用主目录
│   ├── __init__.py               # 应用初始化
│   ├── config.py                 # 应用配置
│   ├── constants.py              # 常量定义
│   ├── scheduler.py              # 定时任务调度器 (APScheduler)
│   ├── tasks.py                  # 任务定义
│   ├── models/                   # 数据模型 (SQLAlchemy)
│   │   ├── __init__.py           # 模型初始化
│   │   ├── user.py              # 用户模型
│   │   ├── instance.py          # 数据库实例模型
│   │   ├── credential.py        # 凭据模型
│   │   ├── account.py           # 账户模型
│   │   ├── account_classification.py # 账户分类模型
│   │   ├── account_change.py    # 账户变更记录模型
│   │   ├── sync_data.py         # 同步数据模型
│   │   ├── log.py               # 日志模型
│   │   ├── task.py              # 任务模型
│   │   ├── database_type_config.py # 数据库类型配置模型
│   │   └── permission_config.py # 权限配置模型
│   ├── routes/                   # 路由控制器 (Flask Blueprint)
│   │   ├── __init__.py           # 路由初始化
│   │   ├── main.py              # 主页面路由
│   │   ├── auth.py              # 认证路由
│   │   ├── admin.py             # 管理后台路由
│   │   ├── api.py               # API路由
│   │   ├── health.py            # 健康检查路由
│   │   ├── instances.py         # 实例管理路由
│   │   ├── credentials.py       # 凭据管理路由
│   │   ├── database_types.py    # 数据库类型管理路由
│   │   ├── account_list.py      # 账户列表路由
│   │   ├── account_sync.py      # 账户同步路由
│   │   ├── account_static.py    # 账户统计路由
│   │   ├── account_classification.py # 账户分类路由
│   │   ├── scheduler.py         # 定时任务路由
│   │   ├── logs.py              # 日志管理路由
│   │   ├── dashboard.py         # 仪表板路由
│   │   └── user_management.py   # 用户管理路由
│   ├── services/                 # 业务服务层
│   │   ├── database_service.py  # 数据库服务
│   │   ├── database_drivers.py  # 数据库驱动检查
│   │   ├── database_type_service.py # 数据库类型服务
│   │   ├── database_filter_manager.py # 数据库过滤器管理
│   │   ├── database_size_service.py # 数据库大小服务
│   │   ├── account_sync_service.py # 账户同步服务
│   │   ├── account_classification_service.py # 账户分类服务
│   │   ├── connection_factory.py # 连接工厂
│   │   ├── permission_query_factory.py # 权限查询工厂
│   │   └── task_executor.py     # 任务执行器
│   ├── utils/                    # 工具类
│   │   ├── api_response.py      # API响应工具
│   │   ├── cache_manager.py     # 缓存管理
│   │   ├── connection_pool.py   # 连接池
│   │   ├── database_type_utils.py # 数据库类型工具
│   │   ├── db_context.py        # 数据库上下文
│   │   ├── decorators.py        # 装饰器
│   │   ├── enhanced_logger.py   # 增强日志记录器
│   │   ├── env_manager.py       # 环境管理
│   │   ├── env_validator.py     # 环境验证
│   │   ├── error_handler.py     # 错误处理
│   │   ├── monitoring.py        # 监控工具
│   │   ├── password_manager.py  # 密码管理
│   │   ├── query_optimizer.py   # 查询优化器
│   │   ├── rate_limiter.py      # 速率限制器
│   │   ├── retry_manager.py     # 重试管理
│   │   ├── security.py          # 安全工具
│   │   ├── security_headers.py  # 安全头
│   │   ├── test_runner.py       # 测试运行器
│   │   ├── timezone.py          # 时区工具
│   │   ├── validation.py        # 验证工具
│   │   ├── structlog_config.py       # 增强的错误处理和日志工具
│   │   ├── advanced_test_framework.py # 高级测试框架
│   │   ├── api_version.py       # API版本管理
│   │   ├── backup_manager.py    # 备份管理
│   │   └── code_quality_analyzer.py # 代码质量分析器
│   ├── middleware/               # 中间件
│   │   └── error_logging_middleware.py # 错误日志中间件
│   ├── blueprints/               # Flask蓝图模块
│   │   └── __init__.py          # 蓝图初始化
│   ├── static/                   # 静态文件
│   │   ├── css/                 # CSS样式文件
│   │   ├── js/                  # JavaScript文件
│   │   └── images/              # 图片文件
│   └── templates/                # Jinja2模板文件
│       ├── base.html            # 基础模板
│       ├── index.html           # 首页模板
│       ├── auth/                # 认证相关模板
│       ├── instances/           # 实例管理模板
│       ├── credentials/         # 凭据管理模板
│       ├── accounts/            # 账户管理模板
│       ├── classification/      # 账户分类模板
│       ├── scheduler/           # 定时任务模板
│       ├── logs/                # 日志管理模板
│       └── admin/               # 管理后台模板
├── docs/                         # 项目文档 (重新组织)
│   ├── README.md                # 文档中心索引
│   ├── architecture/            # 架构文档
│   │   ├── PROJECT_STRUCTURE.md # 项目结构说明
│   │   ├── spec.md              # 技术规格文档
│   │   ├── FUNCTION_INTEGRATION_REPORT.md # 功能集成报告
│   │   └── SECOND_AUDIT_REPORT.md # 第二轮审计报告
│   ├── database/                # 数据库文档
│   │   ├── DATABASE_DRIVERS.md  # 数据库驱动指南
│   │   ├── DATABASE_PERMISSIONS_OVERVIEW.md # 数据库权限总览
│   │   ├── MYSQL_PERMISSIONS.md # MySQL权限管理
│   │   ├── POSTGRESQL_PERMISSIONS.md # PostgreSQL权限管理
│   │   ├── SQL_SERVER_PERMISSIONS.md # SQL Server权限管理
│   │   ├── ORACLE_PERMISSIONS.md # Oracle权限管理
│   │   ├── ORACLE_DRIVER_GUIDE.md # Oracle驱动指南
│   │   ├── ORACLE_PERMISSION_REQUIREMENTS.md # Oracle权限要求
│   │   └── database_initialization.md # 数据库初始化
│   ├── features/                # 功能特性文档
│   │   ├── LOG_MANAGEMENT_FEATURES.md # 日志管理功能
│   │   ├── POSTGRESQL_INTEGRATION_REPORT.md # PostgreSQL集成报告
│   │   └── PERFORMANCE_MONITOR_REMOVAL_REPORT.md # 性能监控移除报告
│   ├── guides/                  # 使用指南
│   │   ├── QUICK_REFERENCE.md   # 快速参考
│   │   ├── README_DEPLOYMENT.md # 部署指南
│   │   ├── UV_USAGE_GUIDE.md    # UV使用指南
│   │   └── ORACLE_SETUP.md      # Oracle环境配置
│   ├── project/                 # 项目文档
│   │   ├── taifish.md           # 项目说明
│   │   ├── todolist.md          # 任务清单
│   │   └── 需求.md              # 需求文档
│   ├── reports/                 # 报告文档
│   │   └── report.md            # 开发报告
│   ├── deployment/              # 部署文档
│   │   ├── DOCKER_ARCHITECTURE.md # Docker架构
│   │   ├── ENVIRONMENT_SETUP.md # 环境配置
│   │   └── PRODUCTION_DEPLOYMENT.md # 生产部署
│   ├── development/             # 开发文档
│   │   ├── ENVIRONMENT_SETUP.md # 开发环境搭建
│   │   ├── DEVELOPMENT_GUIDE.md # 开发指南
│   │   ├── DATABASE_MIGRATION.md # 数据库迁移
│   │   ├── TROUBLESHOOTING.md   # 故障排除
│   │   └── data_requirements.md # 数据要求
│   ├── adr/                     # 架构决策记录
│   │   └── 0001-x86_64-architecture.md # x86_64架构决策
│   └── api/                     # API文档
│       └── README.md            # API接口文档
├── sql/                         # SQL脚本目录 (统一管理)
│   ├── README.md                # SQL目录说明
│   ├── init_postgresql.sql      # PostgreSQL完整初始化脚本
│   ├── postgres_init.sql        # PostgreSQL Docker初始化脚本
│   ├── postgres_docker_init.sql # PostgreSQL Docker配置脚本
│   ├── setup_mysql_monitor_user.sql # MySQL监控用户设置
│   ├── setup_postgresql_monitor_user.sql # PostgreSQL监控用户设置
│   ├── setup_sqlserver_monitor_user.sql # SQL Server监控用户设置
│   └── setup_oracle_monitor_user.sql # Oracle监控用户设置
├── docker/                      # Docker配置
│   ├── compose/                 # Docker Compose配置
│   ├── configs/                 # 配置文件
│   ├── nginx/                   # Nginx配置
│   ├── postgres/                # PostgreSQL配置
│   └── redis/                   # Redis配置
├── scripts/                     # 脚本文件
│   ├── init_database.py         # 数据库初始化
│   ├── init_data.py             # 数据初始化
│   ├── init_database_types.py   # 数据库类型初始化
│   ├── init_permission_config.py # 权限配置初始化
│   ├── create_admin_user.py     # 创建管理员用户
│   ├── create_test_credential.py # 创建测试凭据
│   ├── migrate_db.py            # 数据库迁移
│   ├── optimize_database.py     # 数据库优化
│   └── manage_encryption_key.py # 加密密钥管理
├── tests/                       # 测试文件
│   ├── __init__.py              # 测试初始化
│   ├── conftest.py              # 测试配置
│   ├── test_api.py              # API测试
│   ├── test_models.py           # 模型测试
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── ui/                      # UI测试
├── userdata/                    # 用户数据目录
│   ├── logs/                    # 日志文件
│   │   ├── app.log              # 应用日志
│   │   ├── api.log              # API日志
│   │   ├── auth.log             # 认证日志
│   │   ├── database.log         # 数据库日志
│   │   ├── sync.log             # 同步日志
│   │   ├── security.log         # 安全日志
│   │   ├── cache.log            # 缓存日志
│   │   └── scheduler.log        # 定时任务日志
│   ├── exports/                 # 导出文件
│   ├── backups/                 # 备份文件
│   ├── uploads/                 # 上传文件
│   └── redis/                   # Redis数据
├── migrations/                  # 数据库迁移
│   ├── alembic.ini              # Alembic配置
│   ├── env.py                   # 迁移环境
│   ├── script.py.mako           # 迁移脚本模板
│   └── versions/                # 迁移版本
├── config/                      # 配置文件
│   ├── database_filters.yaml    # 数据库过滤器配置
│   └── scheduler_tasks.yaml     # 定时任务配置
├── app.py                       # 应用入口
├── requirements.txt             # Python依赖
├── pyproject.toml               # 项目配置
├── uv.lock                      # UV锁定文件
├── docker-compose.yml           # Docker Compose配置
├── Dockerfile                   # Docker镜像配置
├── Makefile                     # Make配置
├── README.md                    # 项目说明
└── .cursorrules                 # Cursor AI编程规则
```

## 核心功能模块

### 1. 用户认证与权限管理
- **文件**: `app/models/user.py`, `app/routes/auth.py`
- **功能**: 基于Flask-Login的会话管理、JWT令牌认证、基于角色的访问控制
- **特性**: 密码加密存储、会话超时自动清理

### 2. 数据库实例管理
- **文件**: `app/models/instance.py`, `app/routes/instances.py`
- **功能**: 支持PostgreSQL、MySQL、SQL Server、Oracle实例管理
- **特性**: 实例创建、编辑、删除、连接测试、状态监控

### 3. 账户分类管理 (核心功能)
- **文件**: `app/models/account_classification.py`, `app/routes/account_classification.py`
- **功能**: 智能账户分类与权限规则管理
- **特性**: 支持多种数据库权限规则、自动分类、多分类分配

### 4. 凭据管理
- **文件**: `app/models/credential.py`, `app/routes/credentials.py`
- **功能**: 安全的数据库连接凭据存储
- **特性**: 凭据与实例关联管理、密码加密存储

### 5. 定时任务管理
- **文件**: `app/scheduler.py`, `app/tasks.py`, `app/routes/scheduler.py`
- **功能**: 基于APScheduler的轻量级任务调度
- **特性**: 任务持久化存储、启用/禁用、立即执行

### 6. 日志监控
- **文件**: `app/models/log.py`, `app/routes/logs.py`
- **功能**: 结构化日志记录、操作审计日志
- **特性**: 日志聚合和过滤、定时任务日志追踪

### 7. 数据同步管理
- **文件**: `app/models/sync_data.py`, `app/routes/account_sync.py`
- **功能**: 账户数据同步、权限数据同步
- **特性**: 同步记录管理、数据变更追踪

## 数据库设计

### 核心表结构
- **users**: 用户表
- **instances**: 数据库实例表
- **credentials**: 凭据表
- **accounts**: 账户表
- **account_classifications**: 账户分类表
- **classification_rules**: 分类规则表
- **permission_configs**: 权限配置表
- **tasks**: 任务表
- **sync_data**: 同步数据表
- **logs**: 日志表
- **account_changes**: 账户变更记录表

### 数据库支持
- **主数据库**: PostgreSQL (包含APScheduler任务调度)
- **缓存**: Redis

## 部署架构

### 开发环境
- Flask开发服务器
- PostgreSQL数据库
- Redis缓存
- 本地文件存储

### 生产环境
- Gunicorn WSGI服务器
- PostgreSQL数据库
- Redis缓存
- Docker容器化部署

## 开发规范

### 代码组织
- 使用Flask Blueprint组织路由
- 业务逻辑封装在services层
- 数据模型统一在models层
- 工具函数放在utils层

### 文档管理
- 所有文档统一存放在docs/目录
- 按功能模块分类组织
- SQL脚本统一存放在sql/目录
- 保持文档链接的准确性

### 版本控制
- 使用清晰的提交信息
- 定期提交和推送代码
- 保持分支整洁
- 及时更新文档

---

**最后更新**: 2025年9月12日  
**维护者**: 鲸落开发团队