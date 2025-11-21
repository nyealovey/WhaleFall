# 鲸落 (TaifishV4) 项目结构

> 最后更新: 2025-11-21 | 版本: v1.2.2

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
├── oracle_client/          # Oracle客户端库
├── examples/               # 示例代码
├── app.py                  # 应用入口
├── wsgi.py                 # WSGI入口
├── requirements.txt        # Python依赖
├── requirements-prod.txt   # 生产环境依赖
├── pyproject.toml          # 项目配置
├── uv.lock                 # uv依赖锁定文件
├── ruff.toml               # Ruff配置
├── mypy.ini                # Mypy配置
├── pytest.ini              # Pytest配置
├── AGENTS.md               # 编码规范
├── CHANGELOG.md            # 更新日志
├── README.md               # 项目说明
├── LICENSE                 # 许可证
├── Makefile                # Make命令
├── Makefile.flask          # Flask专用Make命令
├── Makefile.prod           # 生产环境Make命令
├── start_uv.sh             # uv启动脚本
├── docker-compose.flask-only.yml  # Flask专用Docker Compose
├── docker-compose.prod.yml        # 生产环境Docker Compose
└── Dockerfile.prod         # 生产环境Dockerfile
```

## 🏗️ 应用架构 (app/)

### 核心模块

```
app/
├── __init__.py             # 应用工厂
├── config.py               # 配置管理
├── scheduler.py            # 任务调度器
├── constants/              # 常量定义模块
│   └── __init__.py
├── errors/                 # 错误处理模块
│   └── __init__.py
├── forms/                  # 表单定义模块
│   └── definitions/
├── models/                 # 数据模型层
├── routes/                 # 路由控制器层
├── services/               # 业务服务层
├── tasks/                  # 异步任务层
├── utils/                  # 工具类
├── views/                  # 视图类（表单视图）
├── static/                 # 静态资源
├── templates/              # 模板文件
└── config/                 # 配置文件
```

### 数据模型层 (models/)

```
models/
├── __init__.py
├── user.py                      # 用户模型
├── instance.py                  # 数据库实例模型
├── instance_account.py          # 实例账户模型
├── instance_database.py         # 实例数据库模型
├── credential.py                # 凭据模型
├── tag.py                       # 标签模型
├── account_classification.py    # 账户分类模型
├── account_permission.py        # 账户权限模型
├── account_change_log.py        # 账户变更日志模型
├── permission_config.py         # 权限配置模型
├── sync_session.py              # 同步会话模型
├── sync_instance_record.py      # 同步实例记录模型
├── base_sync_data.py            # 基础同步数据模型
├── database_size_stat.py        # 数据库大小统计模型
├── database_size_aggregation.py # 数据库大小聚合模型
├── instance_size_stat.py        # 实例大小统计模型
├── instance_size_aggregation.py # 实例大小聚合模型
├── database_type_config.py      # 数据库类型配置模型
└── unified_log.py               # 统一日志模型
```

### 路由控制器层 (routes/)

```
routes/
├── __init__.py
├── main.py                      # 主页面路由
├── common.py                    # 公共路由
├── auth.py                      # 认证路由
├── dashboard.py                 # 仪表板路由
├── instance.py                  # 实例管理路由（列表、创建、编辑）
├── instance_detail.py           # 实例详情路由（详情页面）
├── instance_statistics.py       # 实例统计路由
├── instance_aggr.py             # 实例聚合统计路由
├── database_aggr.py             # 数据库聚合统计路由
├── aggregations.py              # 聚合路由
├── capacity.py                  # 容量路由
├── connections.py               # 连接测试路由
├── credentials.py               # 凭据管理路由
├── tags.py                      # 标签管理路由
├── tags_batch.py                # 标签批量分配路由
├── account_classification.py    # 账户分类路由
├── account.py                   # 账户管理路由
├── account_stat.py              # 账户统计路由
├── account_sync.py              # 账户同步路由
├── sync_sessions.py             # 同步会话路由
├── logs.py                      # 日志管理路由
├── scheduler.py                 # 任务调度路由
├── cache.py                     # 缓存管理路由
├── partition.py                 # 分区管理路由
├── files.py                     # 文件导出路由
├── users.py                     # 用户管理路由
└── health.py                    # 健康检查路由
```

### 业务服务层 (services/)

```
services/
├── __init__.py
├── account_sync/                    # 账户同步服务
│   ├── __init__.py
│   ├── account_sync_service.py      # 账户同步统一入口
│   ├── account_sync_filters.py      # 账户同步过滤器
│   ├── account_query_service.py     # 查询辅助
│   ├── coordinator.py               # 两阶段协调器
│   ├── inventory_manager.py         # 账户清单同步
│   ├── permission_manager.py        # 权限快照同步
│   └── adapters/                    # 数据库适配器
│       ├── base_adapter.py
│       ├── factory.py
│       ├── mysql_adapter.py
│       ├── postgresql_adapter.py
│       ├── sqlserver_adapter.py
│       └── oracle_adapter.py
├── account_classification/          # 账户分类服务
│   ├── __init__.py
│   ├── orchestrator.py              # 分类编排器
│   ├── auto_classify_service.py     # 自动分类服务
│   ├── cache.py                     # 分类缓存
│   ├── repositories.py              # 分类仓储
│   └── classifiers/                 # 分类器
├── aggregation/                     # 聚合服务
│   ├── __init__.py
│   ├── aggregation_service.py       # 聚合服务主类
│   ├── calculator.py                # 聚合计算器
│   ├── query_service.py             # 聚合查询服务
│   ├── results.py                   # 聚合结果
│   ├── database_aggregation_runner.py # 数据库聚合运行器
│   └── instance_aggregation_runner.py # 实例聚合运行器
├── database_sync/                   # 数据库同步服务
│   ├── __init__.py
│   ├── database_sync_service.py     # 数据库同步服务
│   ├── coordinator.py               # 协调器
│   ├── database_filters.py          # 数据库过滤器
│   ├── inventory_manager.py         # 清单管理器
│   ├── persistence.py               # 持久化
│   └── adapters/                    # 数据库适配器
├── form_service/                    # 表单服务
│   ├── __init__.py
│   ├── resource_form_service.py     # 表单服务基类
│   ├── instances_form_service.py    # 实例表单服务
│   ├── credentials_form_service.py  # 凭据表单服务
│   ├── tags_form_service.py         # 标签表单服务
│   ├── users_form_service.py        # 用户表单服务
│   ├── change_password_form_service.py # 修改密码表单服务
│   ├── classification_form_service.py  # 分类表单服务
│   ├── classification_rule_form_service.py # 分类规则表单服务
│   └── scheduler_job_form_service.py   # 调度任务表单服务
├── instances/                       # 实例服务
│   ├── __init__.py
│   └── batch_service.py             # 实例批量创建/删除服务
├── connection_adapters/             # 连接适配器
│   ├── __init__.py
│   ├── connection_factory.py        # 连接工厂
│   ├── connection_test_service.py   # 连接测试服务
│   └── adapters/                    # 数据库连接适配器
├── statistics/                      # 统计服务
│   ├── account_statistics_service.py    # 账户统计服务
│   ├── database_statistics_service.py   # 数据库统计服务
│   ├── instance_statistics_service.py   # 实例统计服务
│   ├── log_statistics_service.py        # 日志统计服务
│   └── partition_statistics_service.py  # 分区统计服务
├── auth/                            # 认证服务
│   └── __init__.py
├── scheduler/                       # 调度器服务
│   └── __init__.py
├── users/                           # 用户服务
│   └── __init__.py
├── partition_management_service.py  # 分区管理服务
├── sync_session_service.py          # 同步会话服务
├── database_type_service.py         # 数据库类型服务
└── cache_service.py                 # 缓存服务
```

### 工具类 (utils/)

```
utils/
├── __init__.py
├── decorators.py                    # 装饰器
├── data_validator.py                # 数据与安全验证工具
├── response_utils.py                # 响应工具
├── structlog_config.py              # 结构化日志配置
├── cache_utils.py                   # 缓存工具
├── time_utils.py                    # 时间工具
├── password_crypto_utils.py         # 密码加密工具
├── query_filter_utils.py            # 查询过滤工具
├── safe_query_builder.py            # 安全查询构建器
├── database_batch_manager.py        # 数据库批量管理器
├── sqlserver_connection_utils.py    # SQL Server连接工具
├── rate_limiter.py                  # 速率限制器
├── version_parser.py                # 版本解析器
└── logging/                         # 日志工具
    └── __init__.py
```

### 静态资源 (static/)

```
static/
├── css/                    # 样式文件
│   ├── pages/              # 页面样式
│   │   ├── accounts/       # 账户管理页面样式
│   │   ├── auth/           # 认证页面样式
│   │   ├── credentials/    # 凭据管理页面样式
│   │   ├── dashboard/      # 仪表板页面样式
│   │   ├── history/        # 历史记录页面样式
│   │   ├── instances/      # 实例管理页面样式
│   │   └── tags/           # 标签管理页面样式
│   ├── components/         # 组件样式
│   │   ├── filters.css     # 筛选器样式
│   │   ├── tag-selector.css # 标签选择器样式
│   │   └── modal.css       # 模态框样式
│   ├── vendor/             # 第三方样式
│   └── main.css            # 主样式文件
├── js/                     # JavaScript文件
│   ├── common/             # 公共脚本
│   │   ├── grid-wrapper.js # Grid.js封装
│   │   ├── http.js         # HTTP工具
│   │   └── utils.js        # 工具函数
│   ├── modules/            # 模块脚本
│   │   ├── services/       # 服务层
│   │   ├── stores/         # 状态管理
│   │   ├── ui/             # UI组件
│   │   └── views/          # 视图层
│   │       ├── accounts/   # 账户管理视图
│   │       ├── auth/       # 认证视图
│   │       ├── credentials/ # 凭据管理视图
│   │       ├── history/    # 历史记录视图
│   │       ├── instances/  # 实例管理视图
│   │       ├── tags/       # 标签管理视图
│   │       └── components/ # 组件视图
│   ├── bootstrap/          # 页面引导脚本
│   │   ├── accounts/
│   │   ├── auth/
│   │   ├── credentials/
│   │   ├── history/
│   │   ├── instances/
│   │   └── tags/
│   └── vendor/             # 第三方脚本
│       ├── gridjs/         # Grid.js库
│       └── tom-select/     # Tom Select库
├── img/                    # 图片资源
│   ├── icons/              # 图标
│   └── logos/              # Logo
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
| users | 用户表 | id, username, password_hash, role, is_active |
| instances | 数据库实例表 | id, name, host, port, db_type, credential_id |
| instance_accounts | 实例账户关系表 | id, instance_id, username, is_active |
| instance_databases | 实例数据库关系表 | id, instance_id, database_name, is_active |
| credentials | 凭据表 | id, name, username, password, db_type |
| tags | 标签表 | id, name, display_name, category, color |
| account_classifications | 账户分类表 | id, name, description, db_type, color |
| classification_rules | 分类规则表 | id, classification_id, rule_type, pattern |
| account_classification_assignments | 账户分类分配表 | id, account_id, classification_id, is_active |
| permission_configs | 权限配置表 | id, db_type, permission_type, config_data |
| sync_sessions | 同步会话表 | id, session_type, status, start_time, end_time |
| sync_instance_records | 同步实例记录表 | id, session_id, instance_id, status |
| account_change_log | 账户变更日志表 | id, instance_account_id, change_type, change_data |
| account_permission | 账户权限快照表 | id, instance_account_id, username, permissions |
| database_size_stats | 数据库大小统计表 | id, instance_id, database_name, size_bytes |
| database_size_aggregations | 数据库大小聚合表 | id, period_type, period_start, total_size |
| instance_size_stats | 实例大小统计表 | id, instance_id, total_size, stat_time |
| instance_size_aggregations | 实例大小聚合表 | id, instance_id, period_type, avg_size |
| database_type_configs | 数据库类型配置表 | id, name, display_name, default_port |
| unified_logs | 统一日志表 | id, level, module, message, timestamp, context |

## 🔧 配置文件

### 应用配置 (config/)

```
config/
├── account_filters.yaml    # 账户过滤规则配置
├── database_filters.yaml   # 数据库过滤规则配置
└── scheduler_tasks.yaml    # 调度器任务配置
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
Dockerfile.prod                   # 生产环境Dockerfile
docker-compose.flask-only.yml     # Flask专用Docker Compose
docker-compose.prod.yml           # 生产环境Docker Compose
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
├── conftest.py                    # 测试配置和fixtures
└── unit/                          # 单元测试
    ├── test_period_calculator.py  # 周期计算器测试
    └── services/                  # 服务层测试
```

**注意**: 集成测试目录尚未创建，测试覆盖率有待提高。

## 📜 脚本工具 (scripts/)

```
scripts/
├── code/                   # 代码相关脚本
├── deployment/             # 部署脚本
├── docker/                 # Docker脚本
├── nginx/                  # Nginx脚本
├── oracle/                 # Oracle脚本
├── password/               # 密码相关脚本
├── refactor_naming.sh      # 命名规范检查脚本
└── validate_env.sh         # 环境验证脚本
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
│   ├── PROJECT_STRUCTURE.md # 项目结构文档
│   └── spec.md             # 架构规范
├── api/                    # API文档
│   └── API_ROUTES_DOCUMENTATION.md
├── database/               # 数据库文档
│   ├── ACCOUNT_SYNC_DESIGN.md
│   └── schema/             # 数据库模式
├── deployment/             # 部署文档
│   └── deployment-guide.md
├── development/            # 开发文档
│   └── setup-guide.md
├── project/                # 项目文档
│   └── taifish.md
├── refactor/               # 重构文档
│   └── gridjs-migration-standard.md # Grid.js迁移标准
├── refactoring/            # 重构记录
├── reports/                # 报告文档
│   ├── clean-code-analysis.md # Clean Code分析报告
│   └── 代码分析文档.md
├── grid-refactor-logs.md   # 日志中心Grid.js重构方案
├── grid-refactor-accounts.md # 账户管理Grid.js重构方案
└── CHANGELOG.md            # 更新日志
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

## 🔄 任务层 (tasks/)

```
tasks/
├── __init__.py
├── account_sync_tasks.py           # 账户同步任务
├── capacity_collection_tasks.py    # 容量采集任务
├── capacity_aggregation_tasks.py   # 容量聚合任务
├── partition_management_tasks.py   # 分区管理任务
└── log_cleanup_tasks.py            # 日志清理任务
```

## 🎨 视图层 (views/)

```
views/
├── __init__.py
├── mixins/                         # 视图混入
│   └── resource_form_view.py       # 资源表单视图基类
├── instance_form_view.py           # 实例表单视图
├── credential_form_view.py         # 凭据表单视图
├── tag_form_view.py                # 标签表单视图
├── user_form_view.py               # 用户表单视图
├── change_password_form_view.py    # 修改密码表单视图
├── account_classification_form_view.py # 账户分类表单视图
└── scheduler_job_form_view.py      # 调度任务表单视图
```

## 📋 表单定义 (forms/)

```
forms/
├── __init__.py
└── definitions/                                # 表单定义
    ├── __init__.py
    ├── base.py                                 # 表单基类
    ├── instance.py                             # 实例表单定义
    ├── credential.py                           # 凭据表单定义
    ├── tag.py                                  # 标签表单定义
    ├── user.py                                 # 用户表单定义
    ├── change_password.py                      # 修改密码表单定义
    ├── account_classification.py               # 账户分类表单定义
    ├── account_classification_rule.py          # 账户分类规则表单定义
    ├── account_classification_constants.py     # 账户分类常量
    ├── account_classification_rule_constants.py # 账户分类规则常量
    └── scheduler_job.py                        # 调度任务表单定义
```

## 🚨 错误处理 (errors/)

```
errors/
├── __init__.py                     # 错误类定义
└── handlers.py                     # 错误处理器
```

## 📊 示例代码 (examples/)

```
examples/
├── logging/                        # 日志示例
├── time/                           # 时间处理示例
└── validation/                     # 验证示例
```

---

## 🎯 核心设计原则

### 1. 分层架构
- **模型层 (Models)**: 数据模型和业务实体
- **服务层 (Services)**: 业务逻辑和数据处理
- **控制器层 (Routes)**: 请求处理和响应
- **视图层 (Views/Templates)**: 用户界面展示
- **任务层 (Tasks)**: 异步任务和定时任务

### 2. 模块化设计
- **功能模块**: 按业务功能划分模块（账户、实例、凭据等）
- **工具模块**: 通用工具和辅助函数
- **配置模块**: 配置管理和环境变量
- **服务模块**: 业务逻辑封装

### 3. 可扩展性
- **插件化**: 支持数据库类型扩展
- **适配器模式**: 不同数据库的适配器
- **工厂模式**: 对象创建和实例化
- **策略模式**: 算法和策略的可替换性
- **服务层模式**: 业务逻辑与控制器分离

### 4. 可维护性
- **代码规范**: 统一的代码风格和规范（AGENTS.md）
- **文档完整**: 详细的文档和注释
- **测试覆盖**: 单元测试和集成测试
- **错误处理**: 完善的异常处理和日志记录
- **工具链**: Ruff、Mypy、Black、isort等

### 5. 前端架构
- **模块化**: JavaScript模块化组织
- **组件化**: 可复用的UI组件
- **标准化**: Grid.js迁移标准
- **状态管理**: Store模式管理状态
- **服务层**: 前端服务层封装API调用

---

## 📝 命名规范

### Python代码
- **模块/文件**: `snake_case`，使用完整单词，禁止缩写
- **类名**: `CapWords`（大驼峰）
- **函数/变量**: `snake_case`
- **常量**: `UPPER_SNAKE_CASE`
- **私有成员**: `_leading_underscore`

### JavaScript代码
- **文件/目录**: `kebab-case`
- **类名**: `PascalCase`
- **函数/变量**: `camelCase`
- **常量**: `UPPER_SNAKE_CASE`

### 路由命名
- 使用动词短语：`list_instances`、`get_user`
- 禁止 `api_` 前缀：❌ `api_get_users` → ✅ `get_users`
- 禁止复数嵌套：❌ `databases_aggregations` → ✅ `get_database_aggregations`

---

## 🔧 开发工具

### 代码质量工具
```bash
make format      # 代码格式化（Black + isort）
make quality     # 代码检查（Ruff + Mypy）
make test        # 运行测试
```

### 命名检查
```bash
./scripts/refactor_naming.sh --dry-run  # 检查命名违规
./scripts/refactor_naming.sh            # 修复命名违规
```

### 开发环境
```bash
make install     # 安装依赖（uv sync）
make dev start   # 启动开发环境（PostgreSQL + Redis）
make dev start-flask  # 启动Flask应用
make dev stop    # 停止开发环境
```

---

**最后更新**: 2025-11-21  
**文档版本**: v1.2.2  
**维护团队**: TaifishingV4 Team
