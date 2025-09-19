# 鲸落 (TaifishV4) - 项目文件清单

## 项目概述
鲸落是一个基于Flask的DBA数据库管理Web应用，提供多数据库实例管理、账户管理、任务调度、日志监控等功能。使用PostgreSQL作为主数据库，支持MySQL、SQL Server、Oracle等主流数据库实例管理。

## 核心应用文件

### 主入口文件
- `app.py` - Flask应用主入口文件

### 配置文件
- `pyproject.toml` - 项目依赖配置（使用uv包管理器）
- `requirements.txt` - Python依赖文件
- `uv.lock` - uv锁定文件
- `env.example` - 环境变量示例文件
- `app/config/` - 配置文件目录
  - `database_filters.yaml` - 数据库过滤器配置
  - `scheduler_tasks.yaml` - 定时任务配置
- `scripts/` - 脚本目录
  - `database/` - 数据库管理脚本
    - `init_database.sh` - 完整数据库初始化脚本
    - `quick_init.sh` - 快速数据库初始化脚本
    - `reset_admin_password.py` - 重置管理员密码
    - `show_admin_password.py` - 显示管理员密码

## 应用核心目录 (app/)

### 应用初始化
- `app/__init__.py` - Flask应用初始化，蓝图注册，中间件配置
- `app/config.py` - 应用配置管理
- `app/constants.py` - 常量定义
- `app/scheduler.py` - APScheduler定时任务调度器
- `app/tasks.py` - 任务定义

### 数据模型 (app/models/)
- `app/models/__init__.py` - 模型初始化
- `app/models/user.py` - 用户模型
- `app/models/instance.py` - 数据库实例模型
- `app/models/credential.py` - 数据库凭据模型
- `app/models/account.py` - 数据库账户模型
- `app/models/account_classification.py` - 账户分类模型
- `app/models/account_change.py` - 账户变更记录模型
- `app/models/sync_data.py` - 同步数据模型
- `app/models/task.py` - 任务模型
- `app/models/log.py` - 日志模型
- `app/models/permission_config.py` - 权限配置模型
- `app/models/global_param.py` - 全局参数模型

### 路由控制器 (app/routes/)
#### 核心路由
- `app/routes/__init__.py` - 路由初始化
- `app/routes/main.py` - 主页面路由
- `app/routes/auth.py` - 用户认证路由
- `app/routes/dashboard.py` - 仪表盘路由
- `app/routes/health.py` - 健康检查路由

#### 数据库管理路由
- `app/routes/instances.py` - 数据库实例管理路由
- `app/routes/credentials.py` - 凭据管理路由
- `app/routes/accounts.py` - 账户管理路由（原始文件，已拆分）
- `app/routes/account_list.py` - 账户列表路由（从accounts.py拆分）
- `app/routes/account_sync.py` - 账户同步路由（从accounts.py拆分）
- `app/routes/account_static.py` - 账户统计路由（从accounts.py拆分）

#### 功能路由
- `app/routes/account_classification.py` - 账户分类管理路由
- `app/routes/tasks.py` - 任务管理路由
- `app/routes/logs.py` - 日志管理路由
- `app/routes/admin.py` - 系统管理路由
- `app/routes/api.py` - API接口路由


### 业务服务层 (app/services/)
- `app/services/database_service.py` - 数据库连接和操作服务
- `app/services/account_sync_service.py` - 账户同步服务
- `app/services/account_classification_service.py` - 账户分类服务
- `app/services/database_size_service.py` - 数据库大小统计服务
- `app/services/database_drivers.py` - 数据库驱动管理服务
- `app/services/task_executor.py` - 任务执行服务

### 工具类 (app/utils/)
#### 核心工具
- `app/utils/api_response.py` - API响应标准化
- `app/utils/timezone.py` - 时区处理工具
- `app/utils/enhanced_logger.py` - 增强日志工具（合并了基础日志功能）
- `app/utils/error_handler.py` - 错误处理工具
- `app/utils/structlog_config.py` - 增强的错误处理和日志工具

#### 安全和验证
- `app/utils/security.py` - 安全工具
- `app/utils/password_manager.py` - 密码管理工具
- `app/utils/validation.py` - 数据验证工具
- `app/utils/security_headers.py` - 安全头设置

#### 性能和缓存
- `app/utils/cache_manager.py` - 缓存管理
- `app/utils/connection_pool.py` - 连接池管理
- `app/utils/rate_limiter.py` - 速率限制
- `app/utils/retry_manager.py` - 重试管理
- `app/utils/query_optimizer.py` - 查询优化

#### 配置和管理
- `app/utils/config_manager.py` - 配置管理
- `app/utils/env_manager.py` - 环境变量管理
- `app/utils/env_validator.py` - 环境变量验证
- `app/utils/backup_manager.py` - 备份管理

#### 监控和测试
- `app/utils/monitoring.py` - 系统监控
- `app/utils/test_runner.py` - 测试运行器
- `app/utils/advanced_test_framework.py` - 高级测试框架
- `app/utils/code_quality_analyzer.py` - 代码质量分析

#### 其他工具
- `app/utils/api_version.py` - API版本管理
- `app/utils/db_context.py` - 数据库上下文管理

### 中间件 (app/middleware/)
- `app/middleware/error_logging_middleware.py` - 错误日志中间件

### 模板文件 (app/templates/)
#### 基础模板
- `app/templates/base.html` - 基础模板
- `app/templates/errors/error.html` - 错误页面模板

#### 页面模板
- ~~`app/templates/main/index.html` - 主页面~~ **已删除** - 未使用
- `app/templates/dashboard/index.html` - 仪表盘
- `app/templates/auth/login.html` - 登录页面
- ~~`app/templates/auth/register.html` - 注册页面~~ **已删除** - 注册功能已移除
- `app/templates/auth/profile.html` - 用户资料页面
- `app/templates/auth/change_password.html` - 修改密码页面

#### 数据库管理模板
- `app/templates/instances/index.html` - 实例列表
- `app/templates/instances/create.html` - 创建实例
- `app/templates/instances/edit.html` - 编辑实例
- `app/templates/instances/detail.html` - 实例详情
- `app/templates/instances/statistics.html` - 实例统计

#### 账户管理模板
- `app/templates/accounts/index.html` - 账户统计页面
- `app/templates/accounts/list.html` - 账户列表页面
- `app/templates/accounts/sync_records.html` - 同步记录页面
- `app/templates/accounts/sync_details.html` - 同步详情页面

#### 其他功能模板
- `app/templates/credentials/index.html` - 凭据列表
- `app/templates/credentials/create.html` - 创建凭据
- `app/templates/credentials/edit.html` - 编辑凭据
- `app/templates/credentials/detail.html` - 凭据详情
- `app/templates/tasks/index.html` - 任务列表
- `app/templates/tasks/create.html` - 创建任务
- `app/templates/tasks/edit.html` - 编辑任务
- `app/templates/tasks/detail.html` - 任务详情
- `app/templates/tasks/builtin_tasks.py` - 内置任务定义
- ~~`app/templates/tasks/create_old.html` - 旧版创建任务模板~~ **已删除** - 文件不存在
- ~~`app/templates/logs/index.html` - 日志管理页面~~ **已删除** - 旧版模板
- `app/templates/logs/system_logs.html` - 系统日志页面
- `app/templates/logs/detail.html` - 日志详情页面
- `app/templates/logs/statistics.html` - 日志统计页面

#### 账户分类模板
- `app/templates/account_classification/index.html` - 分类管理页面
- `app/templates/account_classification/rules.html` - 分类规则页面

#### 管理后台模板
- ~~`app/templates/admin/layout.html` - 管理后台布局~~ **已删除** - 未使用
- ~~`app/templates/admin/menu.html` - 管理菜单~~ **已删除** - 未使用
- `app/templates/admin/system_config.html` - 系统配置
- `app/templates/admin/constants.html` - 常量管理

## 脚本文件 (scripts/)

### 数据库初始化脚本
- `scripts/init_database.py` - 数据库初始化
- `scripts/init_data.py` - 初始数据创建
- `scripts/create_admin_user.py` - 创建管理员用户
- `scripts/create_test_credential.py` - 创建测试凭据

### 权限配置脚本
- `scripts/init_permission_config.py` - 权限配置初始化
- `sql/setup_mysql_monitor_user.sql` - MySQL监控用户设置
- `sql/setup_postgresql_monitor_user.sql` - PostgreSQL监控用户设置
- `sql/setup_sqlserver_monitor_user.sql` - SQL Server监控用户设置
- `sql/setup_oracle_monitor_user.sql` - Oracle监控用户设置

### 测试脚本
- `scripts/test_mysql_permissions.sql` - MySQL权限测试
- `scripts/test_postgresql_permissions.sql` - PostgreSQL权限测试
- `scripts/test_sqlserver_permissions.sql` - SQL Server权限测试
- `scripts/test_oracle_permissions.sql` - Oracle权限测试

### 数据库管理脚本
- `scripts/migrate_db.py` - 数据库迁移
- `scripts/migration_manager.py` - 迁移管理
- `scripts/add_indexes.py` - 添加索引
- `scripts/add_performance_indexes.py` - 添加性能索引
- `scripts/optimize_database.py` - 数据库优化
- `scripts/link_sync_records_to_tasks.py` - 链接同步记录到任务

### 开发工具脚本
- `scripts/run_comprehensive_tests.py` - 运行综合测试
- `scripts/run_second_audit_tests.py` - 运行二次审计测试
- `scripts/replace_hardcoded_values.py` - 替换硬编码值
- `scripts/manage_encryption_key.py` - 管理加密密钥

### 部署脚本
- `scripts/automated_deployment.py` - 自动化部署

### 日志和监控脚本
- `scripts/init_sample_logs.py` - 初始化示例日志

## 测试文件 (tests/)

### 测试配置
- `tests/__init__.py` - 测试包初始化
- `tests/conftest.py` - pytest配置文件

### 单元测试
- `tests/unit/test_timezone.py` - 时区功能测试
- `tests/unit/test_china_time.py` - 中国时间测试
- `tests/unit/test_logging.py` - 日志功能测试
- `tests/unit/test_constants_integration.py` - 常量集成测试

### 集成测试
- `tests/integration/test_database.py` - 数据库集成测试
- `tests/integration/test_db.py` - 数据库测试（重复）
- `tests/integration/test_api_logging.py` - API日志测试
- `tests/integration/test_log_trend.py` - 日志趋势测试
- `tests/integration/test_admin_menu.py` - 管理菜单测试
- `tests/integration/test_advanced_systems.py` - 高级系统测试
- `tests/integration/test_all_admin_pages.py` - 所有管理页面测试

### API测试
- `tests/test_api.py` - API接口测试
- `tests/test_models.py` - 模型测试

### UI测试
- `tests/ui/test_admin_interface.html` - 管理界面UI测试
- `tests/ui/test_menu_display.html` - 菜单显示UI测试

## 文档文件 (doc/)

### 项目文档
- `doc/README.md` - 项目说明文档
- `doc/spec.md` - 技术规格文档
- `doc/todolist.md` - 任务清单
- `doc/report.md` - 项目报告
- `doc/PROJECT_STRUCTURE.md` - 项目结构文档

### 功能文档
- `doc/DATABASE_DRIVERS.md` - 数据库驱动文档
- `doc/DATABASE_PERMISSIONS_OVERVIEW.md` - 数据库权限概览
- `doc/MYSQL_PERMISSIONS.md` - MySQL权限文档
- `doc/POSTGRESQL_PERMISSIONS.md` - PostgreSQL权限文档
- `doc/SQL_SERVER_PERMISSIONS.md` - SQL Server权限文档
- `doc/ORACLE_PERMISSIONS.md` - Oracle权限文档
- `doc/ORACLE_DRIVER_GUIDE.md` - Oracle驱动指南
- `doc/ORACLE_PERMISSION_REQUIREMENTS.md` - Oracle权限要求
- `doc/ORACLE_ARM64_SUPPORT_REPORT.md` - Oracle ARM64支持报告
- `doc/ORACLE_ARM64_ERROR_HANDLING_REPORT.md` - Oracle ARM64错误处理报告

### 集成报告
- `doc/POSTGRESQL_INTEGRATION_REPORT.md` - PostgreSQL集成报告
- `doc/FUNCTION_INTEGRATION_REPORT.md` - 功能集成报告
- `doc/PERFORMANCE_MONITOR_REMOVAL_REPORT.md` - 性能监控移除报告

### 审计报告
- `doc/AUDIT_REPORT.md` - 审计报告
- `doc/SECOND_AUDIT_REPORT.md` - 二次审计报告

### 开发文档
- `doc/UV_USAGE_GUIDE.md` - UV使用指南
- `doc/api/API_DOCUMENTATION.md` - API文档

### 部署文档
- `doc/deployment/` - 部署相关文档

### 其他文档
- `doc/index_temp.css` - 临时CSS文件（可删除）

## 配置文件

### 数据库迁移
- `migrations/` - Alembic数据库迁移文件目录
- `migrations/alembic.ini` - Alembic配置文件
- `migrations/env.py` - Alembic环境配置
- `migrations/script.py.mako` - 迁移脚本模板

### Docker配置
- `docker/` - Docker相关配置文件
- `docker/compose/docker-compose.yml` - Docker Compose配置
- `docker/configs/` - 各种服务配置文件
- `docker/nginx/` - Nginx配置
- `docker/postgres/` - PostgreSQL配置
- `docker/redis/` - Redis配置

### 开发配置
- `Makefile` - Make构建配置

## 启动脚本详细分析

### 核心启动脚本（保留）
- `start_app.sh` - **核心应用启动脚本**
  - 功能：激活虚拟环境，检查依赖，启动Flask应用
  - 状态：✅ 保留（简单可靠）
  - 用途：生产环境和简单开发环境

- `start_uv.sh` - **UV环境启动脚本**
  - 功能：使用uv管理Python环境和依赖，启动应用
  - 状态：✅ 保留（现代化包管理）
  - 用途：推荐的新开发方式


### APScheduler相关脚本（已集成）
- `app/scheduler.py` - **APScheduler调度器**
  - 功能：定时任务调度管理
  - 状态：✅ 已实现并集成
  - 用途：替代Celery的轻量级任务调度

- `app/tasks.py` - **任务定义**
  - 功能：定义各种定时任务
  - 状态：✅ 已实现
  - 用途：账户同步、日志清理等任务

- `app/routes/scheduler.py` - **任务管理API**
  - 功能：任务管理Web界面和API
  - 状态：✅ 已实现
  - 用途：任务创建、编辑、执行管理

- `app/routes/scheduler.py` - **任务管理界面**
  - 功能：任务管理Web界面
  - 状态：✅ 已实现
  - 用途：任务创建、编辑、监控


### 监控和检查脚本
- `app/scheduler.py` - **任务监控**
  - 功能：监控任务执行状态
  - 状态：✅ 已实现
  - 用途：任务执行监控

- `app/routes/scheduler.py` - **任务健康检查**
  - 功能：检查任务调度器状态
  - 状态：✅ 已实现
  - 用途：任务调度器健康检查

## 启动脚本清理建议

### 已清理的脚本
所有功能重复和过时的启动脚本已删除，保留核心功能脚本。

### 保留的核心脚本
1. `start_app.sh` - 核心应用启动
2. `start_uv.sh` - UV环境启动（推荐）
3. `app/scheduler.py` - APScheduler调度器
4. `app/tasks.py` - 任务定义
5. `app/routes/scheduler.py` - 任务管理API
6. `app/scheduler.py` - 任务监控
7. `app/scheduler.py` - APScheduler调度器
8. `app/tasks.py` - 任务定义
9. `app/routes/scheduler.py` - 任务管理API

### 当前启动脚本结构
```
启动脚本/
├── 应用启动/
│   ├── start_app.sh          # 传统方式启动
│   └── start_uv.sh           # UV方式启动（推荐）
├── APScheduler服务/
│   ├── app/scheduler.py      # APScheduler调度器
│   ├── app/tasks.py          # 任务定义
│   └── app/routes/scheduler.py # 任务管理API
└── 监控检查/
    ├── app/scheduler.py      # 任务监控
    └── app/routes/scheduler.py # 健康检查
```

## 测试和调试文件

### 测试脚本
- `run_tests.py` - 测试运行脚本
- `run_auto_classify.py` - 自动分类测试
- `run_pgsql_classification.py` - PostgreSQL分类测试
- `minimal_test.py` - 最小化测试
- `simple_test.py` - 简单测试

### 调试脚本
- `debug_timezone.py` - 时区调试
- `fix_logging.py` - 日志修复
- `fix_timezone.py` - 时区修复
- `test_oracle_rule.py` - Oracle规则测试
- `test_pgsql_rule.py` - PostgreSQL规则测试

### 环境设置
- `setup_dev_environment.sh` - 开发环境设置
- `setup_oracle_env.sh` - Oracle环境设置
- `dev_uv.sh` - UV开发环境
- `dev_workflow.sh` - 开发工作流
- `manage_deps_uv.sh` - UV依赖管理

## 数据文件

### 用户数据
- `userdata/` - 用户数据目录（包含数据库文件）

### 实例数据
- `instances_template.csv` - 实例模板CSV文件

### 缓存和临时文件
- `appendonlydir/` - Redis AOF文件目录
- `dump.rdb` - Redis RDB文件
- `apscheduler_jobs` - APScheduler任务表（PostgreSQL）
- `scheduler.db` - APScheduler任务数据库（已迁移到PostgreSQL）
- `cookies.txt` - Cookie文件（可删除）

### 其他数据文件
- `instance/` - 实例数据目录

## 项目完成状态

### 项目交付成果
- **核心功能**：用户管理、实例管理、账户分类、定时任务、日志监控 ✅
- **多数据库支持**：PostgreSQL、MySQL、SQL Server、Oracle ✅
- **安全防护**：密码加密、SQL注入防护、XSS防护、CSRF防护 ✅
- **性能优化**：数据库优化、缓存系统、连接池、异步任务 ✅
- **生产就绪**：错误处理、监控告警、日志记录、健康检查 ✅

### 文件结构统计
- **总文件数**：约150+个文件
- **核心应用文件**：约50个
- **模板文件**：约35个
- **测试文件**：约20个
- **文档文件**：约25个（已清理）
- **配置文件**：约20个

### 文档清理完成
- **已删除临时文档**：20个开发过程文档 ✅
- **保留核心文档**：25个重要文档 ✅
- **文档结构**：更加清晰，便于维护 ✅
