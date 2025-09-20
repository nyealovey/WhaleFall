# 鲸落 (TaifishV4) - 项目结构文档

## 技术栈

- **后端**: Flask 3.1.2, SQLAlchemy 2.0.43, APScheduler 3.11.0
- **前端**: Bootstrap 5.3.2, jQuery 3.7.1, Chart.js 4.4.0
- **数据库**: PostgreSQL (主数据库), MySQL, SQL Server, Oracle
- **缓存**: Redis 7.4.0
- **Python版本**: 3.11+

## 项目目录结构

```
TaifishV4/
├── app/                    # Flask应用主目录
│   ├── models/            # 数据模型
│   ├── routes/            # 路由控制器
│   ├── services/          # 业务服务层
│   ├── utils/             # 工具类
│   ├── templates/         # Jinja2模板文件
│   └── static/            # 静态文件
├── docs/                  # 项目文档
│   ├── architecture/      # 架构文档
│   ├── database/          # 数据库文档
│   ├── deployment/        # 部署文档
│   ├── guides/            # 使用指南
│   └── api/               # API文档
├── sql/                   # SQL脚本目录
├── scripts/               # 脚本文件
├── tests/                 # 测试文件
├── userdata/              # 用户数据目录
├── migrations/            # 数据库迁移
└── docker/                # Docker配置
```

## 核心功能模块

### 1. 用户认证与权限管理
- 基于Flask-Login的会话管理
- JWT令牌认证
- 密码加密存储

### 2. 数据库实例管理
- 支持PostgreSQL、MySQL、SQL Server、Oracle
- 实例创建、编辑、删除、连接测试

### 3. 账户分类管理 (核心功能)
- 智能账户分类与权限规则管理
- 支持多种数据库权限规则
- 自动分类、多分类分配

### 4. 定时任务管理
- 基于APScheduler的轻量级任务调度
- 任务持久化存储
- 启用/禁用、立即执行

### 5. 日志监控
- 结构化日志记录
- 操作审计日志
- 日志聚合和过滤

## 数据库设计

### 核心表结构
- **users**: 用户表
- **instances**: 数据库实例表
- **credentials**: 凭据表
- **accounts**: 账户表
- **account_classifications**: 账户分类表
- **tasks**: 任务表
- **logs**: 日志表

### 数据库支持
- **主数据库**: PostgreSQL
- **缓存**: Redis

## 部署架构

### 开发环境
- Flask开发服务器
- PostgreSQL数据库
- Redis缓存

### 生产环境
- Gunicorn WSGI服务器
- PostgreSQL数据库
- Redis缓存
- Docker容器化部署