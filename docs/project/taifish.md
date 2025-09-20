# 鲸落 (TaifishV4) - 项目文件清单

> **注意**: 详细的项目概述和功能特性请参考 [主README文档](../../README.md)

## 项目概述
鲸落是一个基于Flask的DBA数据库管理Web应用，提供多数据库实例管理、账户管理、任务调度、日志监控等功能。

## 核心文件结构

### 主入口文件
- `app.py` - Flask应用主入口文件

### 配置文件
- `pyproject.toml` - 项目依赖配置
- `requirements.txt` - Python依赖文件
- `env.development` - 开发环境配置
- `env.production` - 生产环境配置

## 应用核心目录 (app/)

### 核心文件
- `app/__init__.py` - Flask应用初始化
- `app/config.py` - 应用配置管理
- `app/constants.py` - 常量定义
- `app/scheduler.py` - APScheduler定时任务调度器
- `app/tasks.py` - 任务定义

### 数据模型 (app/models/)
- `app/models/user.py` - 用户模型
- `app/models/instance.py` - 数据库实例模型
- `app/models/credential.py` - 数据库凭据模型
- `app/models/account.py` - 数据库账户模型
- `app/models/account_classification.py` - 账户分类模型
- `app/models/task.py` - 任务模型
- `app/models/log.py` - 日志模型

### 路由控制器 (app/routes/)
- `app/routes/auth.py` - 用户认证路由
- `app/routes/dashboard.py` - 仪表盘路由
- `app/routes/instances.py` - 数据库实例管理路由
- `app/routes/credentials.py` - 凭据管理路由
- `app/routes/accounts.py` - 账户管理路由
- `app/routes/account_classification.py` - 账户分类管理路由
- `app/routes/tasks.py` - 任务管理路由
- `app/routes/logs.py` - 日志管理路由
- `app/routes/api.py` - API接口路由

### 业务服务层 (app/services/)
- `app/services/database_service.py` - 数据库连接和操作服务
- `app/services/account_sync_service.py` - 账户同步服务
- `app/services/account_classification_service.py` - 账户分类服务
- `app/services/task_executor.py` - 任务执行服务

### 工具类 (app/utils/)
- `app/utils/api_response.py` - API响应标准化
- `app/utils/timezone.py` - 时区处理工具
- `app/utils/security.py` - 安全工具
- `app/utils/validation.py` - 数据验证工具
- `app/utils/cache_manager.py` - 缓存管理

## 脚本文件 (scripts/)

### 核心脚本
- `scripts/init_database.py` - 数据库初始化
- `scripts/create_admin_user.py` - 创建管理员用户
- `scripts/migrate_db.py` - 数据库迁移
- `scripts/optimize_database.py` - 数据库优化

## 测试文件 (tests/)

### 测试配置
- `tests/conftest.py` - pytest配置文件

### 单元测试
- `tests/unit/test_timezone.py` - 时区功能测试
- `tests/unit/test_logging.py` - 日志功能测试

### 集成测试
- `tests/integration/test_database.py` - 数据库集成测试
- `tests/integration/test_api_logging.py` - API日志测试

## 配置文件

### 数据库迁移
- `migrations/` - Alembic数据库迁移文件目录

### Docker配置
- `docker-compose.dev.yml` - 开发环境Docker配置
- `docker-compose.prod.yml` - 生产环境Docker配置

## 启动脚本

### 核心启动脚本
- `start_app.sh` - 传统方式启动
- `start_uv.sh` - UV方式启动（推荐）

### 任务调度
- `app/scheduler.py` - APScheduler调度器
- `app/tasks.py` - 任务定义

## 项目完成状态

### 核心功能
- **用户管理** ✅
- **实例管理** ✅
- **账户分类** ✅
- **定时任务** ✅
- **日志监控** ✅

### 多数据库支持
- **PostgreSQL** ✅
- **MySQL** ✅
- **SQL Server** ✅
- **Oracle** ✅

### 安全防护
- **密码加密** ✅
- **SQL注入防护** ✅
- **XSS防护** ✅
- **CSRF防护** ✅
