# 鲸落 (WhaleFall) 项目结构

> 最后更新: 2025-12-17 | 版本: v1.3.0

## 📁 项目根目录

```
WhaleFall/
├── app/                          # Flask应用主目录
├── docs/                         # 项目文档
├── tests/                        # 测试文件
├── scripts/                      # 工具脚本
├── sql/                          # SQL脚本
├── nginx/                        # Nginx配置
├── migrations/                   # 数据库迁移
├── userdata/                     # 用户数据目录
├── examples/                     # 示例代码
├── node_modules/                 # Node依赖(本地生成)
├── package.json                  # 前端依赖与脚本
├── package-lock.json             # npm锁文件
├── eslint.config.cjs             # ESLint配置
├── pyrightconfig.json            # Pyright配置
├── app.py                        # 应用入口
├── wsgi.py                       # WSGI入口
├── pyproject.toml                # 项目配置
├── uv.lock                       # uv依赖锁定文件
├── requirements.txt              # Python依赖
├── requirements-prod.txt         # 生产环境依赖
├── env.example                   # 生产环境变量模板
├── docker-compose.flask-only.yml # Flask专用Docker Compose
├── docker-compose.prod.yml       # 生产环境Docker Compose
├── Dockerfile.prod               # 生产环境Dockerfile
├── Makefile                      # Make命令
├── Makefile.flask                # Flask专用Make命令
├── Makefile.prod                 # 生产环境Make命令
├── start_uv.sh                   # uv启动脚本
├── AGENTS.md                     # 编码规范
├── CHANGELOG.md                  # 更新日志
├── README.md                     # 项目说明
└── LICENSE                       # 许可证
```

## 🏗️ 应用架构 (app/)

### 核心模块

```
app/
├── __init__.py             # 应用工厂
├── settings.py             # 统一配置读取与校验
├── config.py               # 配置兼容层（已弃用）
├── config/                 # YAML配置文件
├── scheduler.py            # 任务调度器
├── py.typed                # PEP 561类型标记
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
├── types/                  # 共享类型别名/协议/TypedDict
├── utils/                  # 工具类
├── views/                  # 视图类（表单视图）
├── static/                 # 静态资源
└── templates/              # 模板文件
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
├── users.py                     # 用户管理路由
├── credentials.py               # 凭据管理路由
├── connections.py               # 连接测试路由
├── files.py                     # 文件导入/导出路由
├── cache.py                     # 缓存管理路由
├── partition.py                 # 分区管理路由
├── scheduler.py                 # 任务调度路由
├── health.py                    # 健康检查路由
├── instances/                   # 实例管理路由
│   ├── __init__.py
│   ├── manage.py                # 实例管理路由（列表、创建、编辑）
│   ├── detail.py                # 实例详情路由（详情页面）
│   ├── batch.py                 # 实例批量导入/删除路由
│   └── statistics.py            # 实例统计路由
├── accounts/                    # 账户相关路由
│   ├── __init__.py
│   ├── classifications.py       # 账户分类管理路由
│   ├── ledgers.py               # 账户台账路由
│   ├── statistics.py            # 账户统计路由
│   └── sync.py                  # 账户同步路由
├── tags/                        # 标签管理路由
│   ├── __init__.py
│   ├── manage.py                # 标签管理路由
│   └── bulk.py                  # 标签批量分配路由
├── history/                     # 历史/审计相关路由
│   ├── __init__.py
│   ├── logs.py                  # 日志管理路由
│   └── sessions.py              # 同步会话路由
├── databases/                   # 数据库相关路由
│   ├── __init__.py
│   ├── capacity_sync.py         # 数据库容量同步路由
│   └── ledgers.py               # 数据库台账路由
└── capacity/                    # 容量统计路由
    ├── __init__.py
    ├── aggregations.py          # 容量聚合路由
    ├── databases.py             # 容量统计（数据库维度）
    └── instances.py             # 容量统计（实例维度）
```

### 业务服务层 (services/)

```
services/
├── __init__.py
├── accounts_sync/                    # 账户同步服务
│   ├── __init__.py
│   ├── accounts_sync_service.py      # 账户同步统一入口
│   ├── accounts_sync_filters.py      # 账户同步过滤器
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
│   ├── resource_service.py     # 表单服务基类
│   ├── instance_service.py    # 实例表单服务
│   ├── credential_service.py  # 凭据表单服务
│   ├── tag_service.py         # 标签表单服务
│   ├── user_service.py        # 用户表单服务
│   ├── password_service.py # 修改密码表单服务
│   ├── classification_service.py  # 分类表单服务
│   ├── classification_rule_service.py # 分类规则表单服务
│   └── scheduler_job_service.py   # 调度任务表单服务
├── instances/                       # 实例服务
│   ├── __init__.py
│   └── batch_service.py             # 实例批量创建/删除服务
├── connection_adapters/             # 连接适配器
│   ├── __init__.py
│   ├── connection_factory.py        # 连接工厂
│   ├── connection_test_service.py   # 连接测试服务
│   └── adapters/                    # 数据库连接适配器
├── ledgers/                         # 台账服务
│   ├── __init__.py
│   └── database_ledger_service.py   # 数据库台账服务
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
├── route_safety.py                  # 路由安全封装
├── sensitive_data.py                # 敏感信息处理工具
├── structlog_config.py              # 结构化日志配置
├── cache_utils.py                   # 缓存工具
├── time_utils.py                    # 时间工具
├── password_crypto_utils.py         # 密码加密工具
├── query_filter_utils.py            # 筛选器选项格式化工具(纯函数)
├── safe_query_builder.py            # 安全查询构建器
├── database_batch_manager.py        # 数据库批量管理器
├── sqlserver_connection_utils.py    # SQL Server连接工具
├── rate_limiter.py                  # 速率限制器
├── version_parser.py                # 版本解析器
└── logging/                         # 日志工具
    ├── __init__.py
    ├── context_vars.py              # 日志上下文变量
    ├── error_adapter.py             # 错误日志适配器
    ├── handlers.py                  # 日志处理器
    └── queue_worker.py              # 队列日志worker
```

### 类型定义 (types/)

```
types/
├── __init__.py
├── accounts.py                # 账户相关类型
├── classification.py          # 分类相关类型
├── converters.py              # 类型转换工具
├── dbapi.py                   # DBAPI类型定义
├── extensions.py              # 扩展点类型
├── query_protocols.py         # 查询协议/Protocol
├── resources.py               # 资源结构类型
├── routes.py                  # 路由相关类型
├── structures.py              # 共享结构/TypedDict
├── sync.py                    # 同步相关类型
└── stubs/                     # 本地stub
    ├── pytest/
    └── sqlalchemy/
```

### 静态资源 (static/)

```
static/
├── css/                         # 样式文件
│   ├── components/              # 组件样式
│   │   ├── crud-modal.css
│   │   ├── stats-card.css
│   │   ├── table.css
│   │   ├── tag-selector.css
│   │   └── filters/filter-common.css
│   ├── pages/                   # 页面样式
│   │   ├── about.css
│   │   ├── accounts/
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── capacity/
│   │   ├── credentials/
│   │   ├── dashboard/
│   │   ├── databases/
│   │   ├── history/
│   │   ├── instances/
│   │   └── tags/
│   ├── fonts.css
│   ├── global.css
│   ├── theme-orange.css
│   └── variables.css
├── js/                          # JavaScript文件
│   ├── bootstrap/               # 页面入口脚本
│   │   ├── accounts/
│   │   ├── admin/
│   │   ├── auth/
│   │   ├── capacity/
│   │   ├── credentials/
│   │   ├── dashboard/
│   │   ├── databases/
│   │   ├── history/
│   │   ├── instances/
│   │   ├── tags/
│   │   └── users/
│   ├── common/                  # 通用工具
│   │   ├── csrf-utils.js
│   │   ├── event-bus.js
│   │   ├── form-validator.js
│   │   ├── grid-wrapper.js
│   │   ├── lodash-utils.js
│   │   ├── number-format.js
│   │   ├── time-utils.js
│   │   ├── toast.js
│   │   └── validation-rules.js
│   ├── core/                    # 核心库
│   │   ├── dom.helpers.js
│   │   └── http-u.js
│   ├── modules/                 # 模块化代码
│   │   ├── services/
│   │   ├── stores/
│   │   ├── theme/
│   │   ├── ui/
│   │   └── views/
│   └── utils/                   # 预留目录(当前为空)
├── vendor/                      # 第三方前端依赖(手动管理,含 VERSIONS.txt)
├── fonts/                       # 字体资源(Inter等)
└── img/                         # 图片资源(logo/favicon等)
```

### 模板文件 (templates/)

```
templates/
├── base.html               # 基础模板
├── about.html              # 关于页面
├── auth/                   # 认证模板
│   ├── login.html
│   ├── list.html
│   ├── change_password.html
│   └── modals/user-modals.html
├── admin/                  # 管理中心模板
│   ├── scheduler/
│   │   ├── index.html
│   │   └── modals/scheduler-modals.html
│   └── partitions/
│       ├── index.html
│       ├── charts/partitions-charts.html
│       └── modals/partitions-modals.html
├── dashboard/              # 仪表板模板
│   └── overview.html
├── capacity/               # 容量统计模板
│   ├── instances.html
│   └── databases.html
├── databases/              # 数据库台账模板
│   └── ledgers.html
├── history/                # 历史记录模板
│   ├── logs/
│   │   ├── logs.html
│   │   ├── detail.html
│   │   └── modals/log-detail-modal.html
│   └── sessions/
│       ├── sync-sessions.html
│       ├── detail.html
│       └── modals/session-detail-modal.html
├── instances/              # 实例管理模板
│   ├── list.html
│   ├── detail.html
│   ├── statistics.html
│   └── modals/
│       ├── instance-modals.html
│       └── batch-create-modal.html
├── credentials/            # 凭据管理模板
│   ├── list.html
│   └── modals/credential-modals.html
├── tags/                   # 标签管理模板
│   ├── index.html
│   ├── bulk/assign.html
│   └── modals/tag-modals.html
├── accounts/               # 账户管理模板
│   ├── ledgers.html
│   ├── statistics.html
│   └── account-classification/
│       ├── index.html
│       ├── permissions/policy-center-view.html
│       └── modals/
│           ├── classification-modals.html
│           └── rule-modals.html
├── users/                  # 用户管理模板（当前为空）
├── errors/                 # 错误模板
│   └── error.html
└── components/             # 组件模板
    ├── filters/macros.html
    ├── forms/macros.html
    ├── ui/
    │   ├── filter_card.html
    │   ├── macros.html
    │   ├── modal.html
    │   ├── page_header.html
    │   └── stats_card.html
    ├── permission_modal.html
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
env.example                 # 生产环境配置
```

### 项目配置

```
pyproject.toml              # 项目元数据
requirements.txt            # 生产环境依赖
requirements-prod.txt       # 生产环境依赖
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
├── conftest.py                    # 测试配置和fixtures
└── unit/                          # 单元测试
    ├── constants/
    │   └── test_constants_immutability.py
    ├── services/
    │   ├── test_aggregation_service_periods.py
    │   ├── test_classification_form_service.py
    │   ├── test_classification_rule_form_service.py
    │   ├── test_database_ledger_service.py
    │   ├── test_sqlserver_adapter_permissions.py
    │   └── test_user_form_service.py
    └── utils/
        ├── test_data_validator.py
        └── test_sensitive_data.py
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
├── getting-started/        # 快速开始
├── architecture/           # 架构设计与 ADR
│   ├── PROJECT_STRUCTURE.md
│   ├── spec.md
│   └── adr/
├── reference/              # 参考手册（契约/字段/参数）
│   ├── api/
│   ├── database/
│   └── config/
├── operations/             # 运维 Runbook（部署/热更新/回滚）
│   ├── deployment/
│   └── hot-update/
├── standards/              # 规范标准（MUST/SHOULD）
│   ├── documentation-standards.md
│   ├── coding-standards.md
│   ├── naming-standards.md
│   ├── version-update-guide.md
│   ├── backend/
│   └── ui/
├── changes/                # 变更记录（feature/bugfix/refactor）
│   ├── feature/
│   ├── bugfix/
│   ├── refactor/
│   ├── perf/
│   └── security/
├── reports/                # 评审与报告
│   └── artifacts/
├── prompts/                # Prompts 与协作模板
└── _archive/               # 归档区（只读）
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
├── accounts_sync_tasks.py           # 账户同步任务
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
│   └── resource_forms.py       # 资源表单视图基类
├── instance_forms.py           # 实例表单视图
├── credential_forms.py         # 凭据表单视图
├── tag_forms.py                # 标签表单视图
├── user_forms.py               # 用户表单视图
├── password_forms.py    # 修改密码表单视图
├── classification_forms.py # 账户分类表单视图
└── scheduler_forms.py      # 调度任务表单视图
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
└── __init__.py                     # 错误类定义
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
- **错误处理**: 完善的异常处理和日志记录
- **工具链**: Black、isort等

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

**最后更新**: 2025-12-17  
**文档版本**: v1.3.0  
**维护团队**: WhaleFall Team
