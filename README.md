# 鲸落 (WhaleFall)

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.3.2-blue.svg)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()
[![Code Quality](https://img.shields.io/badge/Code%20Quality-B+-success.svg)](docs/reports/clean-code-analysis.md)

> 鲸落是一套面向 DBA 团队的数据库资源管理平台，围绕实例、账户、容量与任务调度等场景提供统一的管理与审计能力。支持 PostgreSQL、MySQL、SQL Server、Oracle 等主流数据库。

---

## 📋 目录

- [核心能力](#-核心能力)
- [技术栈](#-技术栈)
- [快速开始](#️-快速开始)
- [项目结构](#️-项目结构)
- [开发指南](#-开发指南)
- [文档索引](#️-文档索引)
- [贡献指南](#-贡献指南)

---

## ✨ 核心能力

### 🗄️ 实例管理
- 集中管理 PostgreSQL、MySQL、SQL Server、Oracle 等数据库实例
- 实例连接测试、健康检查、标签分类
- 批量创建、编辑、删除实例
- 实例详情页面展示账户、容量、统计信息

### 👥 账户与权限治理
- 账户自动同步（支持两阶段同步：清单 + 权限）
- 智能账户分类（基于规则自动分类）
- 权限差异分析与审计日志
- 账户变更历史追踪
- 支持多数据库类型的权限模型

### 📊 容量洞察
- 实例/数据库容量自动采集
- 周期聚合（日/周/月/季度）
- 容量趋势分析与预测
- TOP 榜单（最大数据库、增长最快等）
- 分区自动管理（创建、清理）

### ⏰ 调度与自动化
- 基于 APScheduler 的任务调度中心
- 支持 Cron、Interval、Date 三种触发器
- 手动执行、暂停、恢复任务
- 任务执行历史与日志
- 批量同步账户、容量采集等预定义任务

### 📝 统一日志中心
- 结构化日志（基于 structlog）
- 日志级别筛选（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 模块筛选、时间范围筛选
- 日志详情查看（包含上下文信息）
- 同步会话追踪

### 🔒 安全与合规
- 凭据加密存储（基于 cryptography）
- CSRF 防护（Flask-WTF）
- SQL 注入防护（SQLAlchemy ORM）
- 基于角色的访问控制（RBAC）
- 全链路审计日志

### 🎨 现代化前端
- 基于 Bootstrap 5 的响应式界面
- Grid.js 统一表格组件
- 实时数据更新
- 友好的用户交互体验

更多模块拆解参见 [docs/architecture/PROJECT_STRUCTURE.md](docs/architecture/PROJECT_STRUCTURE.md)。

---

## 🛠️ 技术栈

### 后端
- **框架**: Flask 3.1.2
- **ORM**: SQLAlchemy 2.0+
- **数据库**: PostgreSQL（主库）
- **缓存**: Redis
- **任务调度**: APScheduler 3.11+
- **日志**: structlog + loguru
- **认证**: Flask-Login + Flask-JWT-Extended

### 前端
- **UI框架**: Bootstrap 5
- **表格组件**: Grid.js
- **选择器**: Tom Select
- **图标**: Font Awesome

### 数据库驱动
- **PostgreSQL**: psycopg 3.2+
- **MySQL**: PyMySQL 1.1+
- **SQL Server**: pymssql 2.3+
- **Oracle**: oracledb 3.3+

### 开发工具
- **代码格式化**: Black 25.1+
- **导入排序**: isort 6.0+
- **安全扫描**: Bandit 1.8+

---

## ⚙️ 快速开始

### 前置要求

- Python 3.13+
- PostgreSQL 14+
- Redis 6+
- uv（推荐）或 pip

### 开发环境搭建

```bash
# 1. 克隆代码
git clone https://github.com/nyealovey/WhaleFall.git
cd WhaleFall

# 2. 安装依赖（推荐使用 uv）
make install
# 或使用 pip
# pip install -r requirements.txt

# 3. 准备环境变量
cp env.development .env
# 编辑 .env 文件，配置数据库、Redis、密钥等
# vim .env

# 4. 启动开发环境（PostgreSQL + Redis）
make dev-start

# 5. 初始化数据库
# 注意：需要先确保 PostgreSQL 已创建数据库
# 然后运行迁移
make init-db

# 6. 启动 Flask 应用
python app.py
```

访问 http://localhost:5000 即可使用。

### 常用命令

```bash
# 代码格式化
make format

# 代码质量检查
make quality

# 运行测试
make test

# 停止开发环境
make dev-stop

# 查看开发环境状态
make dev-status

# 查看开发环境日志
make dev-logs
```

> 生产部署请参考 [docs/deployment/deployment-guide.md](docs/deployment/deployment-guide.md)。

---

## 🗂️ 项目结构

```
WhaleFall/
├── app/                    # 应用主目录
│   ├── models/             # 数据模型
│   ├── routes/             # 路由控制器
│   ├── services/           # 业务服务
│   ├── tasks/              # 异步任务
│   ├── utils/              # 工具函数
│   ├── views/              # 视图类
│   ├── templates/          # Jinja2 模板
│   └── static/             # 静态资源
├── docs/                   # 项目文档
│   ├── architecture/       # 架构文档
│   ├── api/                # API 文档
│   ├── refactor/           # 重构文档
│   └── reports/            # 分析报告
├── tests/                  # 测试文件
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
├── scripts/                # 工具脚本
├── migrations/             # 数据库迁移
├── nginx/                  # Nginx 配置
├── sql/                    # SQL 脚本
├── AGENTS.md               # 编码规范
├── pyproject.toml          # 项目配置
├── requirements.txt        # Python 依赖
└── Makefile                # Make 命令
```

详细结构参见 [docs/architecture/PROJECT_STRUCTURE.md](docs/architecture/PROJECT_STRUCTURE.md)。

---

## 📖 开发指南

### 编码规范

项目遵循严格的编码规范，详见 [AGENTS.md](AGENTS.md)：

- **命名规范**: 
  - Python: `snake_case`（模块/函数/变量）、`CapWords`（类名）
  - JavaScript: `kebab-case`（文件/目录）、`camelCase`（函数/变量）
- **代码风格**: 使用 Black、isort 统一格式
- **提交规范**: 使用 `fix:`、`feat:`、`refactor:` 等前缀

### 提交前检查

```bash
# 检查命名规范
./scripts/refactor_naming.sh --dry-run

# 代码格式化
make format

# 代码质量检查
make quality

# 运行测试
make test
```

### Grid.js 迁移标准

前端表格统一使用 Grid.js，遵循 [docs/refactor/gridjs-migration-standard.md](docs/refactor/gridjs-migration-standard.md) 标准：

- 统一的 API 接口格式
- 标准的 GridWrapper 封装
- 服务端分页、排序、筛选
- 禁止修改 `grid-wrapper.js`

### 代码质量

项目代码质量评分：**B+ (85/100)**

详细分析报告：[docs/reports/clean-code-analysis.md](docs/reports/clean-code-analysis.md)

---

## 🗂️ 文档索引

### 架构文档
- [项目结构](docs/architecture/PROJECT_STRUCTURE.md) - 详细的项目目录结构
- [架构规范](docs/architecture/spec.md) - 体系结构与设计背景

### API 文档
- [API 路由文档](docs/api/API_ROUTES_DOCUMENTATION.md) - 完整的 API 接口文档
- [服务与工具文档](docs/api/SERVICES_UTILS_DOCUMENTATION.md) - 服务层和工具类文档

### 数据库文档
- [数据库驱动](docs/database/DATABASE_DRIVERS.md) - 数据库驱动配置
- [数据库权限概览](docs/database/DATABASE_PERMISSIONS_OVERVIEW.md) - 权限模型说明

### 开发文档
- [代码风格指南](docs/development/STYLE_GUIDE.md) - 代码风格规范

### 部署文档
- [生产部署指南](docs/deployment/PRODUCTION_DEPLOYMENT.md) - 生产环境部署步骤
- [热更新指南](docs/deployment/HOT_UPDATE_GUIDE.md) - 生产环境热更新

### 重构文档
- [Grid.js 迁移标准](docs/refactor/gridjs-migration-standard.md) - 前端表格迁移规范
- [日志中心重构方案](docs/grid-refactor-logs.md) - 日志中心 Grid.js 重构
- [账户管理重构方案](docs/grid-refactor-accounts.md) - 账户管理 Grid.js 重构

### 分析报告
- [Clean Code 分析报告](docs/reports/clean-code-analysis.md) - 代码质量分析

### 其他文档
- [更新日志](CHANGELOG.md) - 版本更新记录
- [编码规范](AGENTS.md) - 项目编码规范

---

## 🤝 贡献指南

欢迎提交 Issue / PR，共创更好的数据库管理平台！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 提交规范

- `feat:` 新功能
- `fix:` 修复 Bug
- `refactor:` 重构代码
- `docs:` 文档更新
- `style:` 代码格式调整
- `test:` 测试相关
- `chore:` 构建/工具相关

### 代码审查

所有 PR 需要通过以下检查：

- ✅ 代码格式检查（Black、isort）
- ✅ 命名规范检查
- ✅ 文档更新

### 问题反馈

- 问题反馈：[GitHub Issues](https://github.com/nyealovey/WhaleFall/issues)
- 讨论交流：[GitHub Discussions](https://github.com/nyealovey/WhaleFall/discussions)

---

## 📊 项目统计

- **代码行数**: ~50,000 行
- **测试覆盖率**: 目标 80%+
- **代码质量**: B+ (85/100)
- **支持数据库**: 4 种（PostgreSQL、MySQL、SQL Server、Oracle）
- **活跃维护**: ✅

---

## 🙏 致谢

感谢所有贡献者和使用者的支持！

特别感谢以下开源项目：

- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM 框架
- [APScheduler](https://apscheduler.readthedocs.io/) - 任务调度
- [Grid.js](https://gridjs.io/) - 表格组件
- [Bootstrap](https://getbootstrap.com/) - UI 框架

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 发布。欢迎在遵守许可证的前提下使用并衍生。

---

## 📮 联系方式

- 项目主页：https://github.com/nyealovey/WhaleFall
- 问题反馈：https://github.com/nyealovey/WhaleFall/issues

---

**最后更新**: 2025-12-05 | **版本**: v1.3.2 | **维护团队**: WhaleFall Team
