# 鲸落 (WhaleFall)

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.5.0-blue.svg)](CHANGELOG.md)
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
- 支持 Cron 触发器配置（UI/API）
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

### 运维控制台前端
- 视觉系统以根目录 `DESIGN.md` 为单一真源
- Flask + Jinja + Bootstrap 5 + Grid.js
- 高密度 DBA cockpit 信息布局
- 统一筛选、表格、异步任务反馈与语义状态组件

更多模块拆解参见 [docs/Obsidian/architecture/project-structure.md](docs/Obsidian/architecture/project-structure.md)。

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
- **视觉系统**: `DESIGN.md`

### 数据库驱动
- **PostgreSQL**: psycopg 3.2+
- **MySQL**: PyMySQL 1.1+
- **SQL Server**: pymssql 2.3+
- **Oracle**: oracledb 3.3+

### 开发工具
- **代码格式化**: Black 25.1+
- **导入排序**: isort 6.0+
- **安全扫描**: Bandit 1.8+
- **类型检查**: Pyright 1.1+

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

访问 http://127.0.0.1:5001 即可使用。

API 文档（OpenAPI/Swagger）：

- Swagger UI：`/api/v1/docs`
- OpenAPI JSON：`/api/v1/openapi.json`

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

# 运行静态类型检查
make typecheck
```

> 生产部署请参考 [docs/Obsidian/operations/deployment/deployment-guide.md](docs/Obsidian/operations/deployment/deployment-guide.md)。

### 📘 类型检查工作流

执行 `make typecheck`（或 `uv run pyright`）即可按 `pyrightconfig.json` 对 `app/`, `scripts/`, `tests/` 做标准级别的类型推断，提前发现接口误用或可空引用。

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
│   ├── Obsidian/           # Obsidian vault（架构/规范/参考/运维/API/canvas）
│   ├── changes/            # 变更记录（feature/bugfix/refactor）
│   ├── reports/            # 评审与报告
│   └── prompts/            # Prompts/协作模板
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

详细结构参见 [docs/Obsidian/architecture/project-structure.md](docs/Obsidian/architecture/project-structure.md)。

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
./scripts/ci/refactor-naming.sh --dry-run

# 代码格式化
make format

# 代码质量检查
make quality

# 运行测试
make test
```

### Grid.js 列表页(规范与迁移)

前端列表页统一使用 Grid.js + GridWrapper, 规范 SSOT 与迁移自检入口如下:

- [Grid 列表页标准](docs/Obsidian/standards/ui/gate/grid.md) - wiring/分页/日志单一真源
- [Grid.js 列表页迁移 checklist](docs/Obsidian/reference/development/gridjs-migration-checklist.md) - 交付自检清单

### 代码质量

项目代码质量评分：**B+ (85/100)**

详细分析报告：[docs/reports/clean-code-analysis.md](docs/reports/clean-code-analysis.md)

### 路由异常模板

后端路由需统一通过 `app/infra/route_safety.py` 中的 `safe_route_call` 封装异常与结构化日志，避免裸 `Exception`：

```python
from app.infra.route_safety import safe_route_call

@blueprint.route("/api/example")
def example_view() -> Response:
    def _execute() -> Response:
        ...
        return jsonify_unified_success(data=payload)

    return safe_route_call(
        _execute,
        module="example",
        action="example_view",
        public_error="操作失败",
        context={"resource_id": resource_id},
        expected_exceptions=(ValidationError,),  # 允许透传的业务异常
    )
```

- **module/action**：对应 structlog 的基本维度，便于查询；按“域 + 动作”命名。
- **context**：传入路由关键参数（如 `instance_id`、`account_id`），避免重复拼接日志。
- **expected_exceptions**：声明可接受的业务异常（`ValidationError`、`NotFoundError` 等），其余异常将被包装为 `SystemError`。
- **批量/导入/导出路由**：务必结合 `safe_route_call` 与 `with db.session.begin()` 之类的事务上下文，保证一次性操作失败时自动回滚，并复用同一份结构化日志；`app/api/v1/namespaces/accounts.py`、`app/api/v1/namespaces/instances.py`、`app/api/v1/namespaces/databases.py` 与 `app/routes/instances/manage.py` 可作为参考。

新增路由默认遵循此模板，增量修改若发现裸 `try/except Exception` 也需优先改造。

---

## 🗂️ 文档索引

完整索引请从 [docs/README.md](docs/README.md) 进入。

### 架构文档
- [项目结构](docs/Obsidian/architecture/project-structure.md) - 详细的项目目录结构
- [架构规范](docs/Obsidian/architecture/spec.md) - 体系结构与设计背景

### API 文档
- [API Contract(v1) 索引](docs/Obsidian/API/api-v1-api-contract.md) - `/api/v1/**` contract 分域索引
- [Service 服务层文档索引](docs/Obsidian/reference/service/README.md) - `app/services/**` 实现解读与边界

### 数据库文档
- [数据库驱动](docs/Obsidian/reference/database/database-drivers.md) - 数据库驱动配置
- [数据库权限概览](docs/Obsidian/reference/database/database-permissions-overview.md) - 权限模型说明

### 开发文档
- [编码规范](AGENTS.md) - 项目编码与门禁规范（单一真源）
- [编码风格补充](docs/Obsidian/standards/core/guide/coding.md) - 编码与命名基础规范
- [文档规范](docs/Obsidian/standards/doc/guide/documentation.md) - 文档结构与编写规范

### 部署文档
- [生产部署指南](docs/Obsidian/operations/deployment/production-deployment.md) - 生产环境部署步骤
- [热更新指南](docs/Obsidian/operations/hot-update/hot-update-guide.md) - 生产环境热更新

### 重构文档
- [Refactor 索引](docs/changes/refactor/README.md) - 重构/瘦身/治理文档入口
- [Grid.js 列表页迁移 checklist](docs/Obsidian/reference/development/gridjs-migration-checklist.md) - 前端表格迁移交付自检

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

**最后更新**: 2026-01-28 | **版本**: v1.5.0 | **维护团队**: WhaleFall Team
