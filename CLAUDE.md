# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库工作时提供指导。

## 项目概览

鲸落（WhaleFall）是面向 DBA 团队的数据库资源管理平台，提供实例、账户、容量与任务调度的统一管理与审计能力。支持 PostgreSQL、MySQL、SQL Server、Oracle。

**技术栈**: Flask 3.1.2, SQLAlchemy 2.0+, APScheduler, Redis, PostgreSQL（主库）, Bootstrap 5, Grid.js

## 核心命令

### 开发环境搭建
```bash
# 安装依赖（需要 uv 或 pip）
make install

# 启动开发环境（通过 Docker 启动 PostgreSQL + Redis）
make dev-start

# 初始化数据库
make init-db

# 运行 Flask 应用
python app.py  # 启动在 http://127.0.0.1:5001
```

### 代码质量
```bash
# 代码格式化（Black + isort）
make format

# 类型检查（Pyright）
make typecheck

# 运行测试
uv run pytest -m unit

# 命名规范检查
./scripts/ci/refactor-naming.sh --dry-run

# Ruff 风格检查
./scripts/ci/ruff-report.sh style

# ESLint（JS 改动时）
./scripts/ci/eslint-report.sh quick
```

### 环境管理
```bash
# 停止开发环境
make dev-stop

# 查看环境状态
make dev-status

# 查看日志
make dev-logs
```

## 架构概览

### 核心结构
- **app/**: Flask 应用代码
  - **routes/**: 路由控制器（按域划分：instances、accounts、capacity 等）
  - **models/**: SQLAlchemy ORM 模型
  - **services/**: 业务逻辑层（账户同步、分类、聚合等）
  - **tasks/**: 后台任务（APScheduler 作业）
  - **utils/**: 工具函数与辅助模块
  - **templates/**: Jinja2 模板
  - **static/**: 前端资源（JS、CSS）
- **migrations/**: Alembic 数据库迁移
- **sql/**: SQL 初始化与运维脚本
- **docs/**: 项目文档（架构、规范、运维）
- **scripts/**: 工具脚本（CI 检查、管理工具）
- **tests/**: 单元测试与集成测试

### 关键架构模式

#### 1. 配置管理
所有配置集中在 `app/settings.py`。环境变量从 `.env` 解析，带校验与默认值。禁止硬编码配置。

#### 2. 路由安全模式
所有路由必须使用 `app/utils/route_safety.py` 的 `safe_route_call` 进行统一错误处理与结构化日志：

```python
from app.utils.route_safety import safe_route_call

@blueprint.route("/api/example")
def example_view() -> Response:
    def _execute() -> Response:
        # 实现逻辑
        return jsonify_unified_success(data=payload)

    return safe_route_call(
        _execute,
        module="example",
        action="example_view",
        public_error="操作失败",
        context={"resource_id": resource_id},
        expected_exceptions=(ValidationError,),
    )
```

#### 3. API 响应封套
所有 API 响应使用 `app/utils/response_utils.py` 的统一封套格式：
- 成功：`jsonify_unified_success(data=..., message=...)`
- 错误：`jsonify_unified_error(error=..., message=...)`

参见：`docs/standards/backend/api-response-envelope.md`

#### 4. 数据库适配器
通过适配器模式支持多数据库：
- 基础适配器：`app/services/connection_adapters/adapters/base_adapter.py`
- 数据库专用适配器：PostgreSQL、MySQL、SQL Server、Oracle
- 工厂模式实例化适配器

#### 5. 账户同步架构
两阶段同步流程：
1. **阶段 1**：拉取账户清单（轻量）
2. **阶段 2**：拉取详细权限（重量）

适配器位于 `app/services/accounts_sync/adapters/`，实现数据库专用逻辑。

#### 6. 账户分类系统
- **分类器**：`app/services/account_classification/classifiers/` - 数据库专用分类逻辑
- **规则**：存储在数据库，针对账户权限评估
- **编排器**：`app/services/account_classification/orchestrator.py` - 协调分类流程

**注意**：V2 架构重构进行中（见 `docs/architecture/account-classification-v2-design.md`），支持 schema-less 权限与统一分类引擎。

#### 7. 容量聚合
- 原始数据：`database_size_stat`、`instance_size_stat`
- 聚合数据：`database_size_aggregation`、`instance_size_aggregation`
- 通过 APScheduler 任务定期聚合
- 时序数据分区管理

#### 8. 任务调度
基于 APScheduler 的任务系统：
- 调度器初始化：`app/scheduler.py`
- 任务定义：`app/tasks/`
- 所有任务必须在 Flask `app.app_context()` 内运行

参见：`docs/standards/backend/task-and-scheduler.md`

#### 9. 结构化日志
使用 structlog 进行结构化日志：
- 配置：`app/utils/structlog_config.py`
- 上下文变量：`app/utils/logging/context_vars.py`
- 日志级别：DEBUG/INFO/WARNING/ERROR/CRITICAL
- 统一日志存储：`unified_log` 表

### 前端架构

#### Grid.js 标准
所有列表页使用 Grid.js 统一封装：
- **封装器**：`app/static/js/common/grid-wrapper.js`（GridWrapper 类）
- **骨架**：`window.Views.GridPage.mount(...)` 实现一致的 wiring
- **分页**：使用 `page`（从 1 开始）与 `page_size` 参数
- **后端契约**：返回 `{success: true, data: {items: [], total: N}}`

**必须遵循**：`docs/standards/ui/gridjs-migration-standard.md`

#### 关键前端组件
- **FilterCard**：`app/static/js/common/filter-card.js` - 统一筛选 UI，带防抖
- **ActionDelegation**：批量操作与行动作
- **URLSync**：筛选/分页状态与 URL 同步
- **ExportButton**：CSV/Excel 导出功能

## 关键规范

### 后端规范（docs/standards/backend/）
- **API 响应封套**：统一 JSON 响应结构
- **错误消息 Schema**：一致的 error/message 字段
- **配置与密钥**：Settings.py + .env 管理
- **数据库迁移**：Alembic 迁移规则（禁止修改历史）
- **敏感数据处理**：加密、脱敏、导出规则
- **任务与调度**：APScheduler 使用模式

### UI 规范（docs/standards/ui/）
- **Grid.js 迁移**：分页、排序、筛选标准
- **Grid 列表页骨架**：统一页面结构
- **分页与排序**：参数命名约定

### 编码规范
- **Python**：模块/函数/变量用 `snake_case`，类名用 `CapWords`
- **JavaScript**：文件/目录用 `kebab-case`，函数/变量用 `camelCase`
- **行长度**：120 字符（Black/Ruff 已配置）
- **导入**：由 isort 排序（first-party: `app`，third-party，stdlib）

参见：`docs/standards/coding-standards.md`、`docs/standards/naming-standards.md`

### Git 工作流
- **开发分支**：`dev`（默认 PR 目标）
- **生产分支**：`main`（仅发布与热修复）
- **提交格式**：`fix:`、`feat:`、`refactor:`、`docs:`、`chore:`
- **PR 要求**：明确范围、验证命令、迁移/配置影响说明

参见：`docs/standards/git-workflow-standards.md`

## 重要约束

### 安全
- 禁止提交 `.env` 文件
- 禁止在 `env.example` 中写入真实凭据
- 使用 `app/utils/sensitive_data.py` 进行数据脱敏
- 所有凭据通过 `cryptography` 库加密
- 启用 CSRF 防护（Flask-WTF）

### 数据库
- **禁止修改历史迁移** - 创建新迁移
- 使用 SQLAlchemy ORM（适配器除外禁止原生 SQL）
- 所有写操作应使用事务
- 时序表分区管理

### 性能
- Redis 缓存频繁访问的数据
- 缓存 TTL 在 Settings 中配置
- JSONB 列使用 GIN 索引
- 所有列表端点必须分页

### 测试
- 单元测试：`tests/unit/`（隔离、快速、无外部依赖）
- 集成测试：`tests/integration/`（需要 DB/Redis）
- 运行单元测试：`uv run pytest -m unit`
- 测试标记：`@pytest.mark.unit`、`@pytest.mark.integration`

## 常见模式

### 新增路由
1. 在相应 `app/routes/` 模块创建路由
2. 使用 `safe_route_call` 封装
3. 返回统一响应格式
4. 在 `app/__init__.py` 注册蓝图
5. 必要时更新 API 文档

### 新增数据库类型
当前（V1）：需要模型变更、迁移、适配器、分类器
未来（V2）：仅需新增带 schema 定义的适配器（见 V2 设计文档）

### 新增后台任务
1. 在 `app/tasks/` 定义任务
2. 在 `app/scheduler.py` 注册
3. 确保任务在 `app.app_context()` 内运行
4. 添加作业配置到 `app/constants/scheduler_jobs.py`

### 新增 Grid.js 列表页
1. 使用 `grid-wrapper.js` 的 `GridWrapper`
2. 实现支持 `page`/`page_size` 的后端 API
3. 返回 `{success: true, data: {items: [], total: N}}`
4. 使用 `Views.GridPage.mount()` 骨架进行 wiring
5. 添加 FilterCard 实现带防抖的搜索/筛选

## 文档

- **架构**：`docs/architecture/` - 系统设计、项目结构
- **API 参考**：`docs/reference/api/` - API 路由、服务、工具
- **数据库参考**：`docs/reference/database/` - 驱动、权限、schema
- **运维**：`docs/operations/` - 部署、热更新、监控
- **规范**：`docs/standards/` - 编码、命名、文档规范
- **变更**：`docs/changes/` - 功能、修复、重构日志

入口：`docs/README.md`

## 开发技巧

### 运行单个测试
```bash
uv run pytest tests/unit/test_specific.py::test_function_name -v
```

### 调试
- 在 `.env` 设置 `FLASK_DEBUG=true`
- 使用 structlog 进行结构化日志
- 检查 `logs/` 目录的应用日志
- 通过 `/history/logs` UI 查看统一日志

### 数据库迁移
```bash
# 创建新迁移
flask db migrate -m "description"

# 应用迁移
flask db upgrade

# 回滚
flask db downgrade
```

### 管理员账户管理
```bash
# 显示管理员密码
python scripts/show_admin_password.py

# 重置管理员密码
python scripts/reset_admin_password.py
```

## 关键参考文件

- `AGENTS.md` - 仓库协作规则与硬约束
- `app/settings.py` - 配置管理
- `app/utils/route_safety.py` - 路由错误处理模式
- `app/utils/response_utils.py` - 统一响应辅助函数
- `app/static/js/common/grid-wrapper.js` - 前端表格封装
- `docs/standards/backend/README.md` - 后端规范索引
- `docs/standards/ui/README.md` - UI 规范索引

## 当前开发重点

- Grid.js 迁移：标准化所有列表页
- 账户分类 V2：schema-less 权限架构（设计阶段）
- 路由安全：迁移所有路由到 `safe_route_call` 模式
- 类型检查：提升 Pyright 覆盖率
