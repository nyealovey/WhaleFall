# 模块级依赖图

## 概览

本文档描述鲸落（Whalefall）项目的模块级依赖关系，帮助开发者理解系统架构和模块间的交互。

## 依赖层次结构

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用入口层                                 │
│  app.py → app/__init__.py (create_app)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        路由层 (Routes)                           │
│  处理HTTP请求，调用服务层，返回响应                                │
│  • auth, dashboard, instance, account, credentials              │
│  • capacity, aggregations, scheduler, logs, health              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        视图层 (Views)                            │
│  表单视图，处理表单渲染和验证                                      │
│  • instance_forms, credential_forms                     │
│  • user_forms, tag_forms                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        服务层 (Services)                         │
│  业务逻辑核心，协调模型和工具                                      │
│  • accounts_sync, database_sync, aggregation                     │
│  • connection_adapters, form_service, statistics                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        模型层 (Models)                           │
│  数据库实体定义，ORM映射                                          │
│  • User, Instance, Credential, Account                          │
│  • DatabaseSizeAggregation, InstanceSizeAggregation             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        工具层 (Utils)                            │
│  通用工具函数，跨模块复用                                          │
│  • cache_utils, decorators, time_utils                          │
│  • structlog_config, response_utils                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        常量层 (Constants)                        │
│  系统常量定义，配置参数                                            │
│  • database_types, status_types, user_roles                     │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块依赖关系

### 1. 应用初始化模块

**模块**: `app/__init__.py`

**职责**: 
- 创建Flask应用实例
- 初始化扩展（数据库、缓存、认证等）
- 注册蓝图
- 配置日志和错误处理

**依赖**:
```
app/__init__.py
├── app/config.py                    # 配置管理
├── app/routes/*                     # 所有路由蓝图
├── app/models/*                     # 数据模型
├── app/utils/structlog_config       # 日志配置
├── app/utils/cache_utils            # 缓存工具
├── app/utils/rate_limiter           # 速率限制
├── app/utils/time_utils             # 时间工具
└── app/scheduler                    # 定时任务调度器
```

**被依赖**: `app.py` (应用入口)

---

### 2. 路由层模块

#### 2.1 认证路由
**模块**: `app/routes/auth.py`

**依赖**:
```
app/routes/auth.py
├── app/models/user                  # 用户模型
├── app/utils/decorators             # 装饰器（登录验证等）
└── app/utils/response_utils         # 响应工具
```

#### 2.2 实例管理路由
**模块**: `app/routes/instance.py`

**依赖**:
```
app/routes/instance.py
├── app/models/instance              # 实例模型
├── app/models/credential            # 凭证模型
├── app/services/instances/*         # 实例服务
├── app/services/connection_adapters # 连接适配器
├── app/utils/decorators             # 装饰器
└── app/utils/response_utils         # 响应工具
```

#### 2.3 账户管理路由
**模块**: `app/routes/account.py`

**依赖**:
```
app/routes/account.py
├── app/models/instance_account      # 账户模型
├── app/services/accounts_sync/*      # 账户同步服务
├── app/services/account_classification/* # 账户分类服务
└── app/utils/query_filter_utils     # 查询过滤工具
```

#### 2.4 容量统计路由
**模块**: `app/routes/capacity.py`, `app/routes/aggregations.py`

**依赖**:
```
app/routes/capacity.py
├── app/models/database_size_stat    # 数据库容量统计模型
├── app/models/instance_size_stat    # 实例容量统计模型
├── app/services/aggregation/*       # 聚合服务
└── app/tasks/capacity_*_tasks       # 容量相关任务
```

#### 2.5 调度器管理路由
**模块**: `app/routes/scheduler.py`

**依赖**:
```
app/routes/scheduler.py
├── app/scheduler                    # 调度器核心
├── app/services/scheduler/*         # 调度器服务
└── app/tasks/*                      # 所有任务模块
```

---

### 3. 服务层模块

#### 3.1 账户同步服务
**模块**: `app/services/accounts_sync/`

**内部结构**:
```
app/services/accounts_sync/
├── __init__.py
├── coordinator.py                   # 协调器（入口）
├── accounts_sync_service.py          # 同步服务核心
├── account_query_service.py         # 账户查询服务
├── inventory_manager.py             # 库存管理
├── permission_manager.py            # 权限管理
├── accounts_sync_filters.py          # 同步过滤器
└── adapters/                        # 数据库适配器
    ├── mysql_adapter.py
    ├── oracle_adapter.py
    └── sqlserver_adapter.py
```

**依赖**:
```
accounts_sync/coordinator.py
├── app/models/instance              # 实例模型
├── app/models/instance_account      # 账户模型
├── app/models/sync_session          # 同步会话模型
├── app/services/connection_adapters # 连接适配器
├── app/utils/database_batch_manager # 批量操作管理
└── ./accounts_sync_service           # 内部服务
```

#### 3.2 数据库同步服务
**模块**: `app/services/database_sync/`

**内部结构**:
```
app/services/database_sync/
├── __init__.py
├── coordinator.py                   # 协调器（入口）
├── database_sync_service.py         # 同步服务核心
├── inventory_manager.py             # 库存管理
├── persistence.py                   # 持久化
├── database_filters.py              # 数据库过滤器
└── adapters/                        # 数据库适配器
    ├── mysql_adapter.py
    ├── oracle_adapter.py
    └── sqlserver_adapter.py
```

**依赖**:
```
database_sync/coordinator.py
├── app/models/instance              # 实例模型
├── app/models/instance_database     # 数据库模型
├── app/models/sync_session          # 同步会话模型
├── app/services/connection_adapters # 连接适配器
└── ./database_sync_service          # 内部服务
```

#### 3.3 聚合服务
**模块**: `app/services/aggregation/`

**内部结构**:
```
app/services/aggregation/
├── __init__.py
├── aggregation_service.py           # 聚合服务入口
├── database_aggregation_runner.py   # 数据库聚合执行器
├── instance_aggregation_runner.py   # 实例聚合执行器
├── calculator.py                    # 计算器
├── query_service.py                 # 查询服务
└── results.py                       # 结果封装
```

**依赖**:
```
aggregation/aggregation_service.py
├── app/models/database_size_aggregation  # 数据库聚合模型
├── app/models/instance_size_aggregation  # 实例聚合模型
├── app/models/database_size_stat         # 数据库统计模型
├── app/models/instance_size_stat         # 实例统计模型
└── ./calculator                          # 内部计算器
```

#### 3.4 连接适配器服务
**模块**: `app/services/connection_adapters/`

**内部结构**:
```
app/services/connection_adapters/
├── __init__.py
├── connection_factory.py            # 连接工厂
├── connection_test_service.py       # 连接测试服务
└── adapters/                        # 具体适配器
    ├── base_adapter.py              # 基础适配器
    ├── mysql_adapter.py
    ├── oracle_adapter.py
    └── sqlserver_adapter.py
```

**依赖**:
```
connection_adapters/connection_factory.py
├── app/models/credential            # 凭证模型
├── app/utils/password_crypto_utils  # 密码加密工具
└── ./adapters/*                     # 各数据库适配器
```

#### 3.5 账户分类服务
**模块**: `app/services/account_classification/`

**内部结构**:
```
app/services/account_classification/
├── __init__.py
├── orchestrator.py                  # 编排器（入口）
├── auto_classify_service.py         # 自动分类服务
├── repositories.py                  # 仓储层
├── cache.py                         # 缓存层
└── classifiers/                     # 分类器
    ├── base_classifier.py
    ├── rule_classifier.py
    └── pattern_classifier.py
```

**依赖**:
```
account_classification/orchestrator.py
├── app/models/account_classification # 分类模型
├── app/models/instance_account       # 账户模型
├── app/utils/cache_utils             # 缓存工具
└── ./auto_classify_service           # 内部服务
```

#### 3.6 表单服务
**模块**: `app/services/form_service/`

**内部结构**:
```
app/services/form_service/
├── __init__.py
├── resource_service.py         # 资源表单服务（基类）
├── instance_service.py        # 实例表单
├── credential_service.py      # 凭证表单
├── user_service.py            # 用户表单
├── tag_service.py             # 标签表单
├── classification_service.py   # 分类表单
└── scheduler_job_service.py    # 调度任务表单
```

**依赖**:
```
form_service/instance_service.py
├── app/models/instance              # 实例模型
├── app/models/credential            # 凭证模型
├── app/forms/definitions/*          # 表单定义
└── ./resource_service          # 基类服务
```

#### 3.7 统计服务
**模块**: `app/services/statistics/`

**内部结构**:
```
app/services/statistics/
├── account_statistics_service.py    # 账户统计
├── database_statistics_service.py   # 数据库统计
├── instance_statistics_service.py   # 实例统计
├── log_statistics_service.py        # 日志统计
└── partition_statistics_service.py  # 分区统计
```

**依赖**:
```
statistics/database_statistics_service.py
├── app/models/database_size_stat    # 数据库统计模型
├── app/models/instance_database     # 数据库模型
└── app/utils/cache_utils            # 缓存工具
```

---

### 4. 任务层模块

**模块**: `app/tasks/`

**内部结构**:
```
app/tasks/
├── __init__.py
├── accounts_sync_tasks.py            # 账户同步任务
├── capacity_collection_tasks.py     # 容量采集任务
├── capacity_aggregation_tasks.py    # 容量聚合任务
├── log_cleanup_tasks.py             # 日志清理任务
└── partition_management_tasks.py    # 分区管理任务
```

**依赖**:
```
tasks/accounts_sync_tasks.py
├── app/services/accounts_sync/*      # 账户同步服务
├── app/models/instance              # 实例模型
└── app/utils/structlog_config       # 日志配置

tasks/capacity_aggregation_tasks.py
├── app/services/aggregation/*       # 聚合服务
└── app/utils/structlog_config       # 日志配置
```

---

### 5. 模型层模块

**模块**: `app/models/`

**核心模型**:
```
app/models/
├── user.py                          # 用户模型
├── instance.py                      # 实例模型
├── credential.py                    # 凭证模型
├── instance_account.py              # 实例账户模型
├── instance_database.py             # 实例数据库模型
├── account_classification.py        # 账户分类模型
├── database_size_stat.py            # 数据库容量统计
├── instance_size_stat.py            # 实例容量统计
├── database_size_aggregation.py     # 数据库容量聚合
├── instance_size_aggregation.py     # 实例容量聚合
├── sync_session.py                  # 同步会话模型
├── sync_instance_record.py          # 同步实例记录
├── tag.py                           # 标签模型
└── unified_log.py                   # 统一日志模型
```

**依赖**:
```
models/instance.py
├── app/__init__.py (db)             # SQLAlchemy实例
└── app/models/base_sync_data        # 基础同步数据模型

models/instance_account.py
├── app/__init__.py (db)
├── app/models/instance              # 实例模型（外键）
└── app/models/account_classification # 分类模型（外键）
```

---

### 6. 工具层模块

**模块**: `app/utils/`

**核心工具**:
```
app/utils/
├── structlog_config.py              # 结构化日志配置
├── cache_utils.py                   # 缓存工具
├── decorators.py                    # 装饰器（登录验证、权限等）
├── response_utils.py                # 响应工具
├── time_utils.py                    # 时间工具
├── password_crypto_utils.py         # 密码加密工具
├── query_filter_utils.py            # 查询过滤工具
├── database_batch_manager.py        # 数据库批量操作管理
├── safe_query_builder.py            # 安全查询构建器
├── rate_limiter.py                  # 速率限制器
└── data_validator.py                # 数据验证器
```

**依赖关系**:
```
utils/decorators.py
├── flask_login                      # Flask登录扩展
└── app/models/user                  # 用户模型

utils/cache_utils.py
├── flask_caching                    # Flask缓存扩展
└── app/__init__.py (cache)          # 缓存实例

utils/time_utils.py
└── pytz                             # 时区库
```

---

### 7. 常量层模块

**模块**: `app/constants/`

**核心常量**:
```
app/constants/
├── database_types.py                # 数据库类型常量
├── status_types.py                  # 状态类型常量
├── user_roles.py                    # 用户角色常量
├── sync_constants.py                # 同步相关常量
├── time_constants.py                # 时间相关常量
├── http_methods.py                  # HTTP方法常量
├── http_headers.py                  # HTTP头常量
├── flash_categories.py              # Flash消息类别
└── scheduler_jobs.py                # 调度任务常量
```

**无依赖**: 常量模块不依赖其他模块

---

## 跨模块依赖关系图

### 数据流向

```
用户请求
    ↓
路由层 (Routes)
    ↓
视图层 (Views) ← 表单定义 (Forms)
    ↓
服务层 (Services)
    ├→ 连接适配器 (Connection Adapters)
    ├→ 缓存服务 (Cache Service)
    └→ 工具层 (Utils)
    ↓
模型层 (Models) ← 数据库 (SQLAlchemy)
    ↓
数据库持久化
```

### 任务调度流向

```
调度器 (Scheduler)
    ↓
任务层 (Tasks)
    ↓
服务层 (Services)
    ↓
模型层 (Models)
    ↓
数据库持久化
```

---

## 关键依赖说明

### 1. 数据库连接依赖

所有需要连接外部数据库的模块都依赖 `connection_adapters`:

```
accounts_sync → connection_adapters
database_sync → connection_adapters
connection_test → connection_adapters
```

### 2. 缓存依赖

所有需要缓存的模块都依赖 `cache_utils`:

```
account_classification → cache_utils
statistics → cache_utils
aggregation → cache_utils
```

### 3. 日志依赖

所有模块都依赖 `structlog_config` 进行日志记录:

```
所有模块 → structlog_config
```

### 4. 认证依赖

所有需要认证的路由都依赖 `decorators`:

```
routes/* → decorators (login_required, role_required)
```

---

## 循环依赖检测

### 已知循环依赖

目前项目中**不存在**循环依赖。所有模块遵循单向依赖原则：

- 路由层 → 服务层 → 模型层 → 工具层 → 常量层
- 任务层 → 服务层 → 模型层

### 避免循环依赖的原则

1. **分层架构**: 严格遵循分层架构，上层依赖下层，下层不依赖上层
2. **依赖注入**: 通过依赖注入解耦模块间的强依赖
3. **接口抽象**: 使用抽象基类定义接口，避免具体实现间的相互依赖
4. **事件驱动**: 使用事件机制解耦模块间的通信

---

## 模块职责边界

### 路由层 (Routes)
- **职责**: 处理HTTP请求，参数验证，调用服务层，返回响应
- **禁止**: 直接操作数据库，包含业务逻辑

### 服务层 (Services)
- **职责**: 实现业务逻辑，协调多个模型，事务管理
- **禁止**: 直接处理HTTP请求，渲染模板

### 模型层 (Models)
- **职责**: 定义数据结构，ORM映射，简单查询方法
- **禁止**: 包含复杂业务逻辑，依赖服务层

### 工具层 (Utils)
- **职责**: 提供通用工具函数，跨模块复用
- **禁止**: 包含业务逻辑，依赖服务层或路由层

### 任务层 (Tasks)
- **职责**: 定义后台任务，调用服务层执行业务逻辑
- **禁止**: 直接操作数据库，包含复杂业务逻辑

---

## 依赖管理建议

### 1. 新增模块时

- 明确模块所属层次
- 检查是否会引入循环依赖
- 遵循单一职责原则
- 更新本文档

### 2. 修改依赖时

- 评估影响范围
- 运行完整测试套件
- 更新相关文档
- 通知相关开发者

### 3. 重构时

- 优先解耦强依赖
- 使用依赖注入
- 提取公共逻辑到工具层
- 保持向后兼容

---

## 依赖可视化工具

### 已生成的依赖图

项目已生成以下依赖图（SVG 格式），可在 `docs/architecture/` 目录查看：

1. **dependency-graph.svg** - 完整的模块依赖图（3层深度，带聚类）
2. **dependency-graph-simple.svg** - 简化版依赖图（2层深度）
3. **dependency-cycles.svg** - 循环依赖检测图
4. **services-dependency.svg** - 服务层模块依赖图
5. **routes-dependency.svg** - 路由层模块依赖图
6. **models-dependency.svg** - 模型层模块依赖图

### 重新生成依赖图

如需重新生成依赖图，使用以下命令：

```bash
# 安装依赖（如未安装）
brew install graphviz  # macOS
uv pip install pydeps

# 生成完整依赖图
uv run pydeps app --max-bacon=3 --cluster -o docs/architecture/dependency-graph.svg

# 生成简化版依赖图
uv run pydeps app --max-bacon=2 --no-show -o docs/architecture/dependency-graph-simple.svg

# 检测循环依赖
uv run pydeps app --show-cycles -o docs/architecture/dependency-cycles.svg

# 生成各层依赖图
uv run pydeps app/services --max-bacon=2 -o docs/architecture/services-dependency.svg
uv run pydeps app/routes --max-bacon=2 -o docs/architecture/routes-dependency.svg
uv run pydeps app/models --max-bacon=2 -o docs/architecture/models-dependency.svg
```

### 其他依赖分析工具

```bash
# 使用 pipdeptree 查看包依赖
uv pip install pipdeptree
uv run pipdeptree
```

---

## 更新记录

| 日期 | 版本 | 修改内容 | 修改人 |
|------|------|----------|--------|
| 2025-11-21 | 1.0.0 | 初始版本 | Kiro |

---

## 参考资料

- [项目结构文档](./PROJECT_STRUCTURE.md)
- [代码质量分析报告](../reports/clean-code-analysis.md)
- [Flask 最佳实践](https://flask.palletsprojects.com/en/latest/patterns/)
