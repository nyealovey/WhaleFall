# 鲸落 (TaifishV4) - 技术规格文档

## 📋 文档信息

- **项目名称**: 鲸落 (TaifishV4 / Whalefall)
- **文档版本**: v2.0.0
- **创建日期**: 2024-12-19
- **最后更新**: 2025-11-21
- **文档类型**: 技术规格文档
- **维护者**: 鲸落开发团队

## 🎯 项目概述

鲸落是一个基于Flask的DBA数据库管理Web应用，提供多数据库实例管理、账户权限同步、容量统计聚合、任务调度、日志监控等功能。支持PostgreSQL、MySQL、SQL Server、Oracle等主流数据库。

### 核心价值
- **统一管理**: 多数据库类型统一管理平台
- **权限同步**: 实时同步数据库账户权限信息
- **智能分类**: 基于权限规则的智能账户分类
- **容量统计**: 数据库和实例级别的容量统计与聚合
- **标签管理**: 灵活的标签分类管理系统
- **实时监控**: 账户权限实时同步和变更追踪
- **安全审计**: 完整的操作审计和日志记录
- **生产就绪**: 企业级安全性和可靠性

### 项目特点
- **模块化架构**: 清晰的分层架构，易于维护和扩展
- **统一数据模型**: 优化的账户权限存储模型，减少80%存储空间
- **高性能**: Redis缓存、数据库连接池、查询优化
- **安全性**: 密码加密、CSRF保护、SQL注入防护
- **可观测性**: 结构化日志、性能监控、错误追踪


## 🏗️ 系统架构

### 整体架构图

```mermaid
graph TB
    subgraph "前端层"
        UI[Web UI<br/>Bootstrap + jQuery]
        API_CLIENT[API Client<br/>AJAX + JSON]
    end
    
    subgraph "应用层"
        FLASK[Flask Application<br/>v3.1.2]
        BLUEPRINTS[Blueprints<br/>模块化路由]
        MIDDLEWARE[Middleware<br/>认证/日志/缓存]
    end
    
    subgraph "业务层"
        SERVICES[Services<br/>业务逻辑层]
        MODELS[Models<br/>数据模型层]
        UTILS[Utils<br/>工具类层]
    end
    
    subgraph "数据层"
        POSTGRES[(PostgreSQL<br/>主数据库)]
        REDIS[(Redis<br/>缓存)]
        SQLITE[(SQLite<br/>任务调度)]
    end
    
    subgraph "外部数据库"
        MYSQL[(MySQL)]
        SQLSERVER[(SQL Server)]
        ORACLE[(Oracle)]
    end
    
    subgraph "任务调度"
        SCHEDULER[APScheduler<br/>定时任务]
        TASKS[Tasks<br/>任务定义]
    end
    
    UI --> API_CLIENT
    API_CLIENT --> FLASK
    FLASK --> BLUEPRINTS
    BLUEPRINTS --> MIDDLEWARE
    MIDDLEWARE --> SERVICES
    SERVICES --> MODELS
    SERVICES --> UTILS
    MODELS --> POSTGRES
    SERVICES --> REDIS
    SCHEDULER --> SQLITE
    SCHEDULER --> TASKS
    TASKS --> SERVICES
    SERVICES --> MYSQL
    SERVICES --> SQLSERVER
    SERVICES --> ORACLE
```


### 分层架构

```mermaid
graph TD
    subgraph "表现层 (Presentation Layer)"
        A1[Web UI Templates]
        A2[API Endpoints]
        A3[Static Assets]
    end
    
    subgraph "路由层 (Route Layer)"
        B1[Flask Blueprints]
        B2[Route Handlers]
        B3[Authentication]
        B4[Authorization]
    end
    
    subgraph "服务层 (Service Layer)"
        C1[Account Sync Service]
        C2[Database Sync Service]
        C3[Aggregation Service]
        C4[Classification Service]
        C5[Form Service]
        C6[Connection Adapters]
    end
    
    subgraph "数据访问层 (Data Access Layer)"
        D1[SQLAlchemy ORM]
        D2[Database Models]
        D3[Query Builders]
    end
    
    subgraph "数据层 (Data Layer)"
        E1[PostgreSQL]
        E2[Redis Cache]
        E3[SQLite Scheduler]
        E4[External Databases]
    end
    
    A1 --> B1
    A2 --> B2
    B1 --> C1
    B2 --> C2
    B3 --> C3
    B4 --> C4
    C1 --> D1
    C2 --> D2
    C3 --> D3
    D1 --> E1
    D2 --> E2
    D3 --> E3
    C6 --> E4
```


## 🔧 技术栈规格

### 后端技术栈

| 组件 | 版本 | 用途 | 说明 |
|------|------|------|------|
| Python | 3.11+ | 运行时环境 | 主要编程语言 |
| Flask | 3.1.2 | Web框架 | 轻量级Web应用框架 |
| SQLAlchemy | 2.0.43 | ORM | 数据库对象关系映射 |
| APScheduler | 3.11.0 | 任务调度 | 定时任务管理 |
| Redis | 6.4.0 | 缓存 | 数据缓存和会话存储 |
| PostgreSQL | 15+ | 主数据库 | 数据持久化存储 |
| Alembic | 1.16.5 | 数据库迁移 | 版本控制 |
| Structlog | 25.4.0 | 日志系统 | 结构化日志记录 |
| Flask-Login | 0.6.3 | 认证 | 用户会话管理 |
| Flask-JWT-Extended | 4.7.1 | JWT | Token认证 |
| Flask-Bcrypt | 1.0.1 | 密码加密 | bcrypt哈希 |
| Flask-Caching | 2.3.1 | 缓存 | 缓存管理 |
| Flask-CORS | 6.0.1 | 跨域 | CORS支持 |

### 前端技术栈

| 组件 | 版本 | 用途 | 说明 |
|------|------|------|------|
| Bootstrap | 5.3.2 | UI框架 | 响应式Web界面 |
| jQuery | 3.7.1 | JavaScript库 | DOM操作和AJAX |
| Chart.js | 4.4.0 | 图表库 | 数据可视化 |
| Font Awesome | 6.4.0 | 图标库 | 用户界面图标 |

### 数据库驱动支持

| 数据库类型 | 驱动 | 版本要求 | 支持功能 |
|------------|------|----------|----------|
| PostgreSQL | psycopg[binary] | 12+ | 完整支持 |
| MySQL | PyMySQL | 5.7+ | 完整支持 |
| SQL Server | pymssql/pyodbc | 2016+ | 完整支持 |
| Oracle | oracledb | 12c+ | 完整支持 |


## 📊 数据模型设计

### 核心实体关系图

```mermaid
erDiagram
    User ||--o{ Instance : manages
    User ||--o{ Credential : owns
    User ||--o{ SyncSession : creates
    
    Instance ||--o{ InstanceAccount : contains
    Instance ||--o{ InstanceDatabase : contains
    Instance ||--o{ AccountPermission : has
    Instance ||--o{ DatabaseSizeStat : tracks
    Instance ||--o{ InstanceSizeStat : tracks
    Instance }o--o{ Tag : tagged
    
    Credential ||--o{ Instance : authenticates
    
    InstanceAccount ||--o{ AccountPermission : has_permissions
    InstanceAccount ||--o{ AccountClassificationAssignment : classified_as
    
    AccountClassification ||--o{ AccountClassificationAssignment : assigns
    AccountClassification ||--o{ ClassificationRule : defines
    
    SyncSession ||--o{ SyncInstanceRecord : contains
    
    Tag ||--o{ InstanceTag : tagged
    InstanceTag }o--|| Instance : belongs_to
    
    User {
        int id PK
        string username
        string email
        string password_hash
        string role
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    Instance {
        int id PK
        string name
        string db_type
        string host
        int port
        string database_name
        string database_version
        string main_version
        string detailed_version
        int credential_id FK
        boolean is_active
        datetime last_connected
        datetime created_at
        datetime updated_at
    }
    
    InstanceAccount {
        int id PK
        int instance_id FK
        string username
        string db_type
        boolean is_active
        datetime first_seen_at
        datetime last_seen_at
        datetime deleted_at
    }
    
    AccountPermission {
        int id PK
        int instance_id FK
        string db_type
        string username
        boolean is_superuser
        boolean is_active
        jsonb global_privileges
        jsonb database_privileges
        jsonb predefined_roles
        jsonb role_attributes
        jsonb server_roles
        jsonb server_permissions
        jsonb oracle_roles
        jsonb system_privileges
        datetime sync_time
        string status
    }
    
    Tag {
        int id PK
        string name
        string display_name
        string category
        string color
        string description
        int sort_order
        boolean is_active
    }
    
    AccountClassification {
        int id PK
        string name
        string description
        string risk_level
        boolean is_active
    }
    
    ClassificationRule {
        int id PK
        int classification_id FK
        string db_type
        jsonb rule_config
        int priority
        boolean is_active
    }
```


### 核心数据表结构

#### 1. 用户管理表

```sql
-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 2. 实例管理表

```sql
-- 数据库实例表
CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    db_type VARCHAR(50) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database_name VARCHAR(255),
    database_version VARCHAR(1000),
    main_version VARCHAR(20),
    detailed_version VARCHAR(50),
    sync_count INTEGER DEFAULT 0,
    credential_id INTEGER REFERENCES credentials(id),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_connected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_instances_name ON instances(name);
CREATE INDEX ix_instances_db_type ON instances(db_type);
```

#### 3. 实例账户关系表

```sql
-- 实例-账户关系表
CREATE TABLE instance_accounts (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    username VARCHAR(255) NOT NULL,
    db_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(instance_id, db_type, username)
);

CREATE INDEX ix_instance_accounts_instance_id ON instance_accounts(instance_id);
CREATE INDEX ix_instance_accounts_username ON instance_accounts(username);
CREATE INDEX ix_instance_accounts_active ON instance_accounts(is_active);
```

#### 4. 账户权限表

```sql
-- 账户权限表（统一存储所有数据库类型的权限）
CREATE TABLE account_permission (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    db_type VARCHAR(20) NOT NULL,
    username VARCHAR(255) NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    -- MySQL权限字段
    global_privileges JSONB,
    database_privileges JSONB,
    -- PostgreSQL权限字段
    predefined_roles JSONB,
    role_attributes JSONB,
    database_privileges_pg JSONB,
    tablespace_privileges JSONB,
    -- SQL Server权限字段
    server_roles JSONB,
    server_permissions JSONB,
    database_roles JSONB,
    database_permissions JSONB,
    -- Oracle权限字段
    oracle_roles JSONB,
    system_privileges JSONB,
    tablespace_privileges_oracle JSONB,
    -- 通用字段
    session_id VARCHAR(36),
    sync_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'success',
    message TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(instance_id, db_type, username)
);

CREATE INDEX ix_account_permission_instance_id ON account_permission(instance_id);
CREATE INDEX ix_account_permission_username ON account_permission(username);
CREATE INDEX ix_account_permission_sync_time ON account_permission(sync_time);
```


## 🔄 业务流程设计

### 账户同步流程

```mermaid
sequenceDiagram
    participant U as User
    participant W as Web UI
    participant R as Route
    participant S as Sync Service
    participant A as Adapter
    participant D as Database
    participant E as External DB
    
    U->>W: 触发账户同步
    W->>R: POST /accounts_sync/instances/{id}/sync
    R->>S: 调用同步服务
    S->>D: 创建同步会话
    S->>A: 获取连接适配器
    A->>E: 连接外部数据库
    E-->>A: 返回账户权限数据
    A-->>S: 返回标准化数据
    S->>D: 更新 InstanceAccount
    S->>D: 更新 AccountPermission
    S->>D: 记录同步状态
    S-->>R: 返回同步结果
    R-->>W: 返回JSON响应
    W-->>U: 显示同步结果
```

### 账户分类流程

```mermaid
flowchart TD
    A[开始分类] --> B[加载活跃分类规则]
    B --> C[按优先级排序规则]
    C --> D[获取需要分类的账户]
    D --> E{按数据库类型分组}
    E -->|MySQL| F[MySQL账户分类]
    E -->|PostgreSQL| G[PostgreSQL账户分类]
    E -->|SQL Server| H[SQL Server账户分类]
    E -->|Oracle| I[Oracle账户分类]
    F --> J[应用分类规则]
    G --> J
    H --> J
    I --> J
    J --> K[计算匹配度]
    K --> L[分配分类]
    L --> M[更新分类记录]
    M --> N[清除缓存]
    N --> O[完成分类]
```

### 容量聚合流程

```mermaid
sequenceDiagram
    participant T as Task
    participant S as Aggregation Service
    participant R as Runner
    participant C as Calculator
    participant D as Database
    
    T->>S: 触发聚合任务
    S->>D: 创建同步会话
    S->>R: 执行数据库聚合
    R->>D: 查询容量统计数据
    D-->>R: 返回统计数据
    R->>C: 计算聚合值
    C-->>R: 返回聚合结果
    R->>D: 保存聚合记录
    S->>R: 执行实例聚合
    R->>D: 查询实例统计数据
    D-->>R: 返回统计数据
    R->>C: 计算聚合值
    C-->>R: 返回聚合结果
    R->>D: 保存聚合记录
    S->>D: 更新会话状态
    S-->>T: 返回聚合结果
```


## 🔌 API 接口设计

### RESTful API 规范

#### 认证接口

```http
POST /auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "password123"
}

Response:
{
    "success": true,
    "message": "登录成功",
    "data": {
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin"
        }
    }
}
```

#### 实例管理接口

```http
GET /instances/api/list
Authorization: Bearer <token>

Response:
{
    "success": true,
    "data": [
        {
            "id": 1,
            "name": "MySQL Production",
            "db_type": "mysql",
            "host": "192.168.1.100",
            "port": 3306,
            "status": "active",
            "last_connected": "2025-11-21T10:30:00Z"
        }
    ],
    "total": 1
}
```

#### 账户同步接口

```http
POST /accounts_sync/instances/{id}/sync
Authorization: Bearer <token>
Content-Type: application/json
X-CSRFToken: <csrf_token>

{
    "sync_type": "manual_single"
}

Response:
{
    "success": true,
    "message": "同步完成",
    "data": {
        "session_id": "uuid-string",
        "synced_count": 25,
        "added_count": 3,
        "modified_count": 2,
        "removed_count": 1
    }
}
```

#### 容量聚合接口

```http
POST /aggregations/api/aggregate-current
Authorization: Bearer <token>
X-CSRFToken: <csrf_token>

Response:
{
    "success": true,
    "message": "聚合完成",
    "data": {
        "session_id": "uuid-string",
        "database_aggregations": 50,
        "instance_aggregations": 10,
        "duration": "2.5s"
    }
}
```

#### 分类管理接口

```http
GET /account_classification/api/list
Authorization: Bearer <token>

Response:
{
    "success": true,
    "data": [
        {
            "id": 1,
            "name": "高风险账户",
            "description": "具有危险权限的账户",
            "risk_level": "high",
            "rule_count": 5,
            "account_count": 12
        }
    ]
}
```

### API 响应格式

#### 成功响应
```json
{
    "success": true,
    "message": "操作成功",
    "data": { ... },
    "timestamp": "2025-11-21T10:30:00Z"
}
```

#### 错误响应
```json
{
    "success": false,
    "message": "操作失败",
    "error": "详细错误信息",
    "code": 400,
    "timestamp": "2025-11-21T10:30:00Z"
}
```


## 🔐 安全设计

### 认证与授权

```mermaid
graph TB
    subgraph "认证流程"
        A[用户登录] --> B[验证用户名密码]
        B --> C[生成Session]
        C --> D[设置Cookie]
        D --> E[返回认证信息]
    end
    
    subgraph "授权流程"
        F[API请求] --> G[验证Session]
        G --> H[检查用户权限]
        H --> I[验证资源访问权限]
        I --> J[执行操作]
    end
    
    subgraph "安全措施"
        K[密码加密<br/>bcrypt]
        L[CSRF保护<br/>CSRF Token]
        M[SQL注入防护<br/>参数化查询]
        N[XSS防护<br/>输入验证]
        O[会话安全<br/>HttpOnly Cookie]
    end
```

### 数据安全

| 安全措施 | 实现方式 | 说明 |
|----------|----------|------|
| 密码加密 | bcrypt | 12轮哈希加密 |
| 敏感数据 | AES加密 | 数据库连接信息 |
| SQL注入防护 | 参数化查询 | SQLAlchemy ORM |
| XSS防护 | 输入验证 | Flask-WTF + bleach |
| CSRF防护 | CSRF Token | Flask-WTF |
| 会话安全 | HttpOnly Cookie | 防止XSS攻击 |
| 权限控制 | 装饰器 | @view_required, @update_required |

### 权限级别

| 权限级别 | 说明 | 装饰器 |
|----------|------|--------|
| admin | 管理员权限 | @role_required('admin') |
| update | 更新权限 | @update_required |
| view | 查看权限 | @view_required |
| guest | 访客权限 | @login_required |


## 📈 性能设计

### 缓存策略

```mermaid
graph LR
    A[API请求] --> B{缓存命中?}
    B -->|是| C[返回缓存数据]
    B -->|否| D[查询数据库]
    D --> E[更新缓存]
    E --> F[返回数据]
    
    subgraph "缓存层级"
        G[L1: Redis缓存<br/>查询结果]
        H[L2: 应用缓存<br/>配置数据]
        I[L3: 数据库缓存<br/>查询计划]
    end
```

### 缓存使用场景

| 场景 | 缓存类型 | TTL | 说明 |
|------|----------|-----|------|
| 分类规则 | Redis | 300s | 账户分类规则缓存 |
| 标签列表 | Redis | 600s | 标签选项缓存 |
| 实例列表 | Redis | 60s | 实例查询结果 |
| 统计数据 | Redis | 300s | 统计查询结果 |
| 配置数据 | 应用内存 | 永久 | 系统配置 |

### 数据库优化

| 优化策略 | 实现方式 | 效果 |
|----------|----------|------|
| 索引优化 | 复合索引 | 查询性能提升80% |
| 连接池 | SQLAlchemy Pool | 连接复用 |
| 查询优化 | N+1查询避免 | 减少数据库访问 |
| 分页查询 | LIMIT/OFFSET | 大数据量处理 |
| 批量操作 | Batch Insert/Update | 减少往返次数 |
| 延迟加载 | Lazy Loading | 按需加载关联数据 |

### 性能监控指标

| 指标 | 目标值 | 监控方式 |
|------|--------|----------|
| API响应时间 | < 200ms | Structlog记录 |
| 数据库查询时间 | < 100ms | SQLAlchemy日志 |
| 缓存命中率 | > 80% | Redis监控 |
| 并发连接数 | < 50 | 连接池监控 |
| 内存使用 | < 512MB | psutil监控 |


## 🔄 任务调度设计

### 调度器架构

```mermaid
graph TB
    subgraph "APScheduler"
        A[BackgroundScheduler] --> B[Job Store<br/>SQLite]
        A --> C[Executor<br/>Thread Pool]
        A --> D[Trigger<br/>Cron/Interval]
    end
    
    subgraph "任务类型"
        E[账户同步任务]
        F[容量采集任务]
        G[容量聚合任务]
        H[日志清理任务]
        I[分区管理任务]
    end
    
    subgraph "任务执行"
        J[任务队列] --> K[任务执行器]
        K --> L[结果记录]
        L --> M[状态更新]
    end
    
    A --> E
    A --> F
    A --> G
    A --> H
    A --> I
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J
```

### 内置任务配置

```yaml
# scheduler_tasks.yaml
default_tasks:
  - id: "sync_accounts"
    name: "账户同步"
    function: "sync_accounts"
    trigger_type: "interval"
    trigger_params:
      minutes: 30
    enabled: true
    
  - id: "collect_capacity"
    name: "容量采集"
    function: "collect_capacity"
    trigger_type: "interval"
    trigger_params:
      hours: 1
    enabled: true
    
  - id: "aggregate_capacity"
    name: "容量聚合"
    function: "aggregate_capacity"
    trigger_type: "cron"
    trigger_params:
      hour: 1
      minute: 0
    enabled: true
    
  - id: "cleanup_logs"
    name: "清理旧日志"
    function: "cleanup_old_logs"
    trigger_type: "cron"
    trigger_params:
      hour: 2
      minute: 0
    enabled: true
```

### 任务管理功能

- 任务启用/禁用
- 任务立即执行
- 任务执行历史
- 任务状态监控
- 任务错误告警


## 📊 监控与日志

### 日志架构

```mermaid
graph TB
    subgraph "应用层"
        A[业务日志] --> B[Structlog]
        C[错误日志] --> B
        D[访问日志] --> B
    end
    
    subgraph "日志处理"
        B --> E[日志格式化]
        E --> F[日志存储]
        F --> G[日志查询]
    end
    
    subgraph "监控告警"
        G --> H[指标收集]
        H --> I[阈值检测]
        I --> J[告警通知]
    end
    
    subgraph "存储层"
        K[PostgreSQL<br/>unified_log表]
        L[文件系统<br/>userdata/logs/]
    end
    
    F --> K
    F --> L
```

### 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 调试信息 | 变量值、执行路径 |
| INFO | 一般信息 | 操作记录、状态变更 |
| WARNING | 警告信息 | 性能问题、配置问题 |
| ERROR | 错误信息 | 异常处理、失败操作 |
| CRITICAL | 严重错误 | 系统崩溃、安全事件 |

### 日志类型

| 类型 | 表名 | 说明 |
|------|------|------|
| 统一日志 | unified_log | 所有业务日志 |
| 账户变更日志 | account_change_log | 账户权限变更 |
| 同步会话 | sync_sessions | 同步任务记录 |
| 同步实例记录 | sync_instance_records | 实例同步详情 |

### 结构化日志格式

```json
{
    "timestamp": "2025-11-21T10:30:00.123Z",
    "level": "info",
    "event": "accounts_sync_completed",
    "module": "accounts_sync",
    "instance_id": 1,
    "instance_name": "MySQL Production",
    "synced_count": 25,
    "duration": 2.5,
    "user_id": 1,
    "username": "admin"
}
```


## 🚀 部署架构

### 容器化部署

```mermaid
graph TB
    subgraph "Docker Compose"
        A[Nginx<br/>反向代理] --> B[Flask App<br/>Web应用]
        B --> C[PostgreSQL<br/>主数据库]
        B --> D[Redis<br/>缓存]
        E[APScheduler<br/>任务调度] --> C
    end
    
    subgraph "数据持久化"
        F[PostgreSQL Data<br/>/userdata/postgres/]
        G[Redis Data<br/>/userdata/redis/]
        H[Logs<br/>/userdata/logs/]
        I[Uploads<br/>/userdata/uploads/]
        J[Scheduler DB<br/>/userdata/scheduler.db]
    end
    
    C --> F
    D --> G
    B --> H
    B --> I
    E --> J
```

### 环境配置

#### 开发环境
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: whalefall_dev
      POSTGRES_USER: whalefall_user
      POSTGRES_PASSWORD: dev_password
    volumes:
      - ./userdata/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    volumes:
      - ./userdata/redis:/data
    ports:
      - "6379:6379"
```

#### 生产环境
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./userdata/nginx:/var/log/nginx
    depends_on:
      - flask
  
  flask:
    build: .
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/whalefall
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./userdata:/app/userdata
    depends_on:
      - postgres
      - redis
```

### 部署方式

1. **Docker Compose部署** (推荐)
   - 一键启动所有服务
   - 数据持久化
   - 易于维护

2. **传统部署**
   - 手动安装依赖
   - 配置系统服务
   - 适合定制化需求

3. **云平台部署**
   - 支持各大云平台
   - 自动扩缩容
   - 高可用架构


## 📋 功能模块规格

### 1. 用户管理模块

**路由**: `app/routes/users.py`  
**服务**: `app/services/users/`, `app/services/form_service/user_service.py`  
**模型**: `app/models/user.py`

#### 功能特性
- 用户注册/登录/登出
- 密码修改和重置
- 用户资料管理
- 角色权限控制 (admin/update/view)

#### 技术实现
- Flask-Login 会话管理
- bcrypt 密码加密
- 基于装饰器的权限控制

---

### 2. 实例管理模块

**路由**: `app/routes/instance.py`, `app/routes/instance_detail.py`  
**服务**: `app/services/instances/`, `app/services/form_service/instance_service.py`  
**模型**: `app/models/instance.py`

#### 功能特性
- 多数据库类型支持 (MySQL, PostgreSQL, SQL Server, Oracle)
- 实例CRUD操作
- 连接测试和状态监控
- 标签和元数据管理
- 版本信息解析
- 批量创建和删除

#### 支持的数据库
- PostgreSQL (完整支持)
- MySQL (完整支持)
- SQL Server (完整支持)
- Oracle (完整支持)

---

### 3. 标签管理模块

**路由**: `app/routes/tags.py`, `app/routes/tags_batch.py`  
**服务**: `app/services/form_service/tag_service.py`  
**模型**: `app/models/tag.py`

#### 功能特性
- 灵活的标签分类管理
- 支持多种标签类型
- 标签与实例关联
- 批量标签操作
- 标签颜色和排序

#### 标签类型
- 资源类标签 (手动管理)
- 身份类标签 (自动同步)
- 支持颜色和描述
- 排序和筛选

---

### 4. 凭证管理模块

**路由**: `app/routes/credentials.py`  
**服务**: `app/services/form_service/credential_service.py`  
**模型**: `app/models/credential.py`

#### 功能特性
- 数据库连接凭证管理
- 密码加密存储
- 凭证类型分类
- 凭证与实例关联

---

### 5. 账户同步模块

**路由**: `app/routes/accounts_sync.py`, `app/routes/account.py`  
**服务**: `app/services/accounts_sync/`  
**模型**: `app/models/instance_account.py`, `app/models/account_permission.py`

#### 功能特性
- 统一的账户权限同步模型
- 权限变更追踪
- 增量同步支持
- 同步状态管理
- 减少80%存储空间

#### 同步操作方式
- 手动单实例同步
- 手动批量同步
- 定时任务同步
- 自定义任务同步

#### 服务架构
```
accounts_sync/
├── coordinator.py              # 协调器（入口）
├── accounts_sync_service.py     # 同步服务核心
├── account_query_service.py    # 账户查询服务
├── inventory_manager.py        # 库存管理
├── permission_manager.py       # 权限管理
├── accounts_sync_filters.py     # 同步过滤器
└── adapters/                   # 数据库适配器
    ├── mysql_adapter.py
    ├── oracle_adapter.py
    └── sqlserver_adapter.py
```

---

### 6. 账户分类模块

**路由**: `app/routes/account_classification.py`  
**服务**: `app/services/account_classification/`  
**模型**: `app/models/account_classification.py`

#### 功能特性
- 智能账户分类
- 权限规则配置
- 多分类支持
- 风险评估
- 自动分类和手动分类

#### 权限规则配置
- MySQL: 46个权限配置
- PostgreSQL: 26个权限配置
- SQL Server: 56个权限配置
- Oracle: 312个权限配置

#### 服务架构
```
account_classification/
├── orchestrator.py             # 编排器（入口）
├── auto_classify_service.py    # 自动分类服务
├── repositories.py             # 仓储层
├── cache.py                    # 缓存层
└── classifiers/                # 分类器
    ├── base_classifier.py
    ├── rule_classifier.py
    └── pattern_classifier.py
```

---

### 7. 容量统计模块

**路由**: `app/routes/capacity.py`, `app/routes/aggregations.py`  
**服务**: `app/services/aggregation/`  
**模型**: `app/models/database_size_stat.py`, `app/models/database_size_aggregation.py`

#### 功能特性
- 数据库容量采集
- 实例容量统计
- 容量聚合计算
- 历史趋势分析
- 容量预警

#### 服务架构
```
aggregation/
├── aggregation_service.py           # 聚合服务入口
├── database_aggregation_runner.py   # 数据库聚合执行器
├── instance_aggregation_runner.py   # 实例聚合执行器
├── calculator.py                    # 计算器
├── query_service.py                 # 查询服务
└── results.py                       # 结果封装
```

---

### 8. 数据库同步模块

**路由**: 无独立路由（通过容量模块调用）  
**服务**: `app/services/database_sync/`  
**模型**: `app/models/instance_database.py`

#### 功能特性
- 数据库列表同步
- 数据库元数据管理
- 数据库过滤规则

#### 服务架构
```
database_sync/
├── coordinator.py              # 协调器（入口）
├── database_sync_service.py    # 同步服务核心
├── inventory_manager.py        # 库存管理
├── persistence.py              # 持久化
├── database_filters.py         # 数据库过滤器
└── adapters/                   # 数据库适配器
    ├── mysql_adapter.py
    ├── oracle_adapter.py
    └── sqlserver_adapter.py
```

---

### 9. 任务调度模块

**路由**: `app/routes/scheduler.py`  
**服务**: `app/scheduler.py`, `app/tasks/`  
**存储**: SQLite (`userdata/scheduler.db`)

#### 功能特性
- 基于APScheduler的轻量级调度
- 任务状态持久化
- 批量操作支持
- 自定义任务执行
- 任务执行历史

#### 内置任务
- 账户同步任务 (`accounts_sync_tasks.py`)
- 容量采集任务 (`capacity_collection_tasks.py`)
- 容量聚合任务 (`capacity_aggregation_tasks.py`)
- 日志清理任务 (`log_cleanup_tasks.py`)
- 分区管理任务 (`partition_management_tasks.py`)

---

### 10. 日志监控模块

**路由**: `app/routes/logs.py`  
**服务**: `app/services/statistics/log_statistics_service.py`  
**模型**: `app/models/unified_log.py`

#### 功能特性
- 结构化日志记录 (Structlog)
- 操作审计追踪
- 日志查询和筛选
- 统计和导出

#### 日志类型
- 系统日志
- 业务日志
- 安全日志
- 任务日志
- 同步日志

---

### 11. 缓存管理模块

**路由**: `app/routes/cache.py`  
**服务**: `app/services/cache_service.py`  
**存储**: Redis

#### 功能特性
- Redis缓存管理
- 缓存统计和监控
- 缓存清理和优化
- 健康检查

#### 缓存类型
- 查询结果缓存
- 会话缓存
- 配置缓存
- 统计数据缓存

---

### 12. 连接适配器模块

**服务**: `app/services/connection_adapters/`

#### 功能特性
- 统一的数据库连接接口
- 连接测试服务
- 连接池管理
- 错误处理

#### 服务架构
```
connection_adapters/
├── connection_factory.py       # 连接工厂
├── connection_test_service.py  # 连接测试服务
└── adapters/                   # 具体适配器
    ├── base_adapter.py         # 基础适配器
    ├── mysql_adapter.py
    ├── oracle_adapter.py
    └── sqlserver_adapter.py
```


## 🔧 开发规范

### 代码规范

#### Python代码规范
- 遵循PEP 8代码风格
- 使用类型提示 (Type Hints)
- 函数和类必须有详细的docstring
- 使用JSDoc风格的注释格式

#### 命名规范（强制要求）
- **模块/文件**: 使用完整单词加 `snake_case`，禁止缩写
  - ✅ `database_aggregation.py`, `instance_aggregation.py`
  - ❌ `database_aggregations.py`, `db_agg.py`
- **服务目录**: 服务目录内文件名称不得使用服务名后缀
  - ✅ `app/services/form_service/resource_service.py`
  - ❌ `app/services/form_service/resource_service.py`
- **路由/视图**: 蓝图函数必须以动词短语命名
  - ✅ `list_instances`, `get_user`, `create_credential`
  - ❌ `api_list`, `statistics_api`, `instances_api`
- **函数**: 不允许带实现细节的后缀
  - ✅ `get_database_aggregations`, `calculate_total`
  - ❌ `get_database_aggregations_optimized`, `calculate_total_v2`
- **前端资源**: JS/CSS/目录一律使用 kebab-case
  - ✅ `capacity-stats/database-aggregations.js`
  - ❌ `capacity_stats/database_aggregations.js`

#### 代码质量工具
- **Black**: 代码格式化 (line-length=120)
- **isort**: 导入排序
- **Bandit**: 安全扫描

### 测试规范

#### 测试类型
- **单元测试**: 测试单个函数和类
- **集成测试**: 测试API接口
- **端到端测试**: 测试完整用户流程

#### 测试标记
```python
@pytest.mark.unit
def test_function():
    pass

@pytest.mark.integration
def test_api():
    pass

@pytest.mark.slow
def test_long_running():
    pass
```

#### 测试覆盖率
- 目标覆盖率: 80%以上
- 核心功能: 100%覆盖
- 业务逻辑: 90%覆盖

### 文档规范

#### 代码文档
- 所有函数必须有docstring
- 复杂算法必须有注释说明
- 配置文件必须有注释
- 数据库表结构必须有说明

#### 项目文档
- **README.md**: 项目概述和快速开始
- **spec.md**: 技术规格文档
- **MODULE_DEPENDENCY_GRAPH.md**: 模块依赖图
- **PROJECT_STRUCTURE.md**: 项目结构文档

### Git提交规范

#### 提交信息格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

#### 类型 (type)
- **feat**: 新功能
- **fix**: 修复bug
- **refactor**: 重构
- **docs**: 文档更新
- **style**: 代码格式
- **test**: 测试相关
- **chore**: 构建/工具

#### 示例
```
feat(account): 添加账户批量同步功能

- 实现批量同步API
- 添加同步进度显示
- 优化同步性能

Closes #123
```

### 质量门禁

#### 提交前检查
```bash
# 代码格式化
make format

# 代码质量检查
make quality

# 运行测试
make test

# 命名规范检查
./scripts/refactor_naming.sh --dry-run
```

#### CI/CD检查
- 代码格式检查
- 类型检查
- 安全扫描
- 测试覆盖率
- 命名规范检查


## 📈 性能指标

### 系统性能指标

| 指标 | 目标值 | 当前值 | 说明 |
|------|--------|--------|------|
| 响应时间 | < 200ms | 150ms | API平均响应时间 |
| 并发用户 | 100+ | 200+ | 支持并发用户数 |
| 数据库连接 | < 50 | 30 | 最大数据库连接数 |
| 内存使用 | < 512MB | 256MB | 应用内存使用 |
| CPU使用率 | < 70% | 45% | 平均CPU使用率 |

### 业务性能指标

| 指标 | 目标值 | 当前值 | 说明 |
|------|--------|--------|------|
| 账户同步速度 | 1000/分钟 | 1500/分钟 | 账户同步处理速度 |
| 分类准确率 | > 95% | 98% | 账户分类准确率 |
| 日志查询速度 | < 1s | 0.5s | 日志查询响应时间 |
| 任务执行成功率 | > 99% | 99.5% | 定时任务执行成功率 |
| 缓存命中率 | > 80% | 85% | Redis缓存命中率 |

### 数据库性能

| 指标 | 目标值 | 优化措施 |
|------|--------|----------|
| 查询响应时间 | < 100ms | 索引优化、查询优化 |
| 连接池利用率 | 60-80% | 连接池配置优化 |
| 慢查询数量 | < 10/天 | 查询分析、索引添加 |
| 数据库大小 | 监控 | 定期清理、分区管理 |

## 🔍 监控与告警

### 监控指标

#### 应用监控
- API响应时间
- 错误率
- 请求量
- 并发连接数

#### 数据库监控
- 连接数
- 查询性能
- 慢查询
- 数据库大小

#### 缓存监控
- 命中率
- 内存使用
- 连接数
- 键数量

#### 任务监控
- 任务执行状态
- 任务执行时间
- 任务失败率
- 任务队列长度

### 告警规则

| 告警项 | 阈值 | 级别 | 处理方式 |
|--------|------|------|----------|
| API响应时间 | > 500ms | Warning | 检查性能瓶颈 |
| 错误率 | > 5% | Critical | 立即处理 |
| 数据库连接 | > 80% | Warning | 扩容或优化 |
| 缓存命中率 | < 60% | Warning | 优化缓存策略 |
| 任务失败率 | > 10% | Critical | 检查任务配置 |
| 磁盘使用率 | > 80% | Warning | 清理或扩容 |

## 🔄 版本管理

### 版本号规范

采用语义化版本号: `MAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的API修改
- **MINOR**: 向下兼容的功能性新增
- **PATCH**: 向下兼容的问题修正

### 当前版本

- **项目版本**: v1.2.3
- **文档版本**: v2.0.0
- **数据库版本**: 由Alembic管理

### 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.2.3 | 2025-11-26 | 注释/文档补齐，版本号同步 |
| v1.2.2 | 2025-11-21 | 优化账户同步模型，减少存储空间 |
| v1.2.1 | 2025-11-05 | 添加容量聚合功能 |
| v1.2.0 | 2025-10-31 | 重构服务层架构 |
| v1.1.0 | 2024-12-19 | 添加账户分类功能 |
| v1.0.0 | 2024-12-01 | 初始版本发布 |

## 📚 参考文档

### 技术文档
- [Flask官方文档](https://flask.palletsprojects.com/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- [APScheduler文档](https://apscheduler.readthedocs.io/)
- [PostgreSQL文档](https://www.postgresql.org/docs/)
- [Redis文档](https://redis.io/docs/)

### 项目文档
- [README.md](../../README.md) - 项目概述
- [CHANGELOG.md](../../CHANGELOG.md) - 更新日志
- [MODULE_DEPENDENCY_GRAPH.md](./MODULE_DEPENDENCY_GRAPH.md) - 模块依赖图
- [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) - 项目结构
- [AGENTS.md](../../AGENTS.md) - 开发规范

### 开发文档
- [快速开始](../../README.md#快速开始) - 开发环境搭建
- [Makefile命令](../../Makefile) - 常用命令
- [Docker部署](../../docker-compose.prod.yml) - 生产部署

## 🤝 贡献指南

### 开发流程

1. **Fork项目** - 从主仓库fork到个人仓库
2. **创建分支** - 基于develop分支创建功能分支
3. **开发功能** - 遵循代码规范进行开发
4. **提交代码** - 遵循提交规范提交代码
5. **运行测试** - 确保所有测试通过
6. **提交PR** - 提交Pull Request到develop分支
7. **代码审查** - 等待代码审查和合并

### 分支管理

- **main**: 生产环境分支
- **develop**: 开发环境分支
- **feature/***: 功能开发分支
- **bugfix/***: Bug修复分支
- **hotfix/***: 紧急修复分支

### 代码审查清单

- [ ] 代码符合规范
- [ ] 命名符合规范
- [ ] 测试覆盖充分
- [ ] 文档更新完整
- [ ] 无安全隐患
- [ ] 性能无明显下降

---

**文档维护**: 本文档由鲸落开发团队维护，如有问题请提交Issue或联系开发团队。

**最后更新**: 2025-11-21  
**文档版本**: v2.0.0  
**维护者**: 鲸落开发团队
