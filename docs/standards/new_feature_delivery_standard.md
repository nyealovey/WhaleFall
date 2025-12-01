# 新增功能复用标准指南

> 目标：在 **WhaleFall V4** 中交付新增功能时，优先复用既有“通用组件 + 目录结构”，减少重复造轮子，确保服务端、前端与任务链条的命名与质量门禁保持一致。

## 1. 适用范围与前置检查

1. 适用于所有面向用户或后台运营的新功能，包括 API、仪表盘、批处理任务和可视化报表。
2. 开工前必须完成以下检查：
   - `git status` 保持干净，确认当前分支与主线同步。
   - 阅读 `docs/architecture` 中的最新结构图，理解组件之间的边界。
   - 运行 `./scripts/refactor_naming.sh --dry-run`，确保现有命名零告警，作为后续提交的基线。
   - 复核 `Makefile` 里的命令，确认需要的服务（PostgreSQL、Redis）均可通过 `make dev start` 拉起。

## 2. 目录映射与可复用资产

| 能力层 | 现有目录/组件 | 复用要点 |
| --- | --- | --- |
| 配置与常量 | `app/config.py`、`app/config/`、`app/constants/` | 优先在已存在的配置类/常量模块中挂载新开关，不要散落在业务代码。 |
| 路由与视图 | `app/routes/`、`app/views/` | 按业务域选择蓝图文件，函数名使用动词短语（例：`list_instances`）。若已存在同类蓝图（如 `users.py`），先扩展原蓝图。 |
| 服务编排 | `app/services/*` | 通过已有服务层封装：如账号/实例/统计等子目录。新增逻辑默认放入对应 `*_service.py` 或新增模块，但禁止 `_api` 或 `_form_service` 后缀。 |
| 表单与校验 | `app/forms/`、`app/utils/data_validator.py`、`app/utils/query_filter_utils.py` | 优先复用 `WTForms` 表单和通用校验器，严禁在路由中手写重复验证。 |
| 工具与基础设施 | `app/utils/`（`response_utils.py`、`rate_limiter.py`、`structlog_config.py` 等） | 统一使用结构化日志、响应包装和速率限制工具，避免自建装饰器。 |
| 模板与组件 | `app/templates/base.html`、`app/templates/components/`、`app/static/css|js` | 通过现有 `components/forms`、`components/ui` 下的片段扩展 UI，CSS/JS 文件名保持 kebab-case。 |
| 异步任务 | `app/tasks/`、`app/scheduler.py`、`app/services/scheduler/` | APScheduler 定时任务入口已就绪，新增任务应归属业务域目录并在 `scheduler.py` 登记，避免重复创建执行器。 |
| 数据与迁移 | `migrations/`、`sql/` | 如需结构更新，沿现有 Alembic/Migration 规范追加版本，不得直接修改历史脚本。 |
| 测试基线 | `tests/unit/`、`tests/integration/`、`tests/conftest.py` | 单元/集成测试共用基线夹具，新增测试必须加上 `@pytest.mark.unit` 或 `@pytest.mark.integration`。 |

> **提示**：在选择落点时先定位业务域，再确认是否已有抽象（如 `app/services/aggregation/`）。如果存在相近功能，优先扩展原模块；只有在逻辑完全独立时才新增目录。

## 3. 新功能落地流程

### 3.1 需求澄清与复用评估

1. 提炼核心用例 -> 列出涉及的领域模型（用户、实例、统计等）。
2. 通过 `rg` 或 IDE 搜索关键术语，定位可直接复用的服务/模板/任务。
3. 在设计稿或技术方案中明确“复用来源”，并注明具体文件（例如 `app/services/statistics/overview_service.py`）。

### 3.2 后端实现步骤

1. **路由**：在对应 `app/routes/<domain>.py` 蓝图中新增动词式函数；如需新蓝图，保持与文件名一致并在 `app/routes/__init__.py` 注册。
2. **服务层**：将业务逻辑下推到 `app/services/<domain>/`；若操作跨域，提炼到 `app/services/cache_service.py`、`app/services/sync_session_service.py` 等通用模块或 `app/utils/*` 中已有工具。
3. **模型/Schema**：复用 `app/models/` 中的 ORM 实体；若必须新增字段，先补迁移再落代码。
4. **任务与调度**：涉及批处理时，在 `app/tasks/` 中实现 APScheduler/内部调度任务，并通过 `app/scheduler.py` 或 `app/services/scheduler` 中现有调度器挂载；日志使用 `structlog_config` 定义的 logger。
5. **配置开关**：新增 feature flag 时统一放入 `app/config/feature_flags.py`（若不存在则创建），并在 `env.*` 样例中注释说明。

### 3.3 前端与模板

1. HTML 统一继承 `app/templates/base.html`，复用 `app/templates/components/` 的表单、过滤器、弹窗等片段。
2. JS/CSS 资源放在 `app/static/js|css/<domain>/`，文件及目录命名需使用 kebab-case，例如 `app/static/js/capacity-stats/usage-chart.js`。
3. 所有交互文本写入现有 `translations` 文件（如有），或在模板中统一使用中文，并避免硬编码 API 路径，改用模板变量。

### 3.4 数据流与集成

1. 若功能依赖外部系统，优先复用 `app/services/connection_adapters/` 中的适配器；需要新协议时遵循同级目录的结构。
2. 缓存策略参考 `app/services/cache_service.py` 与 `app/utils/cache_utils.py`；不要重复实现缓存封装。
3. 多步骤同步先检查 `app/services/accounts_sync/`、`database_sync/` 等现有流水线，确认是否可插入 Hook，而不是新建整条链路。

## 4. 质量与验证

1. **静态检查**：
   - `make format`（触发 `black + isort`）。
   - `make quality`，确保 `ruff`、命名守卫脚本均通过。
2. **测试策略**：
   - 单元测试写在 `tests/unit/<domain>/`，覆盖服务层与工具函数。
   - 集成测试写在 `tests/integration/<domain>/`，依赖 `make dev start` 提供的 PostgreSQL + Redis 组合。
   - 必要时执行 `pytest --cov=app --cov-report=term-missing`，并关注新增路径的覆盖率。
3. **命名确认**：提交前再次运行 `./scripts/refactor_naming.sh --dry-run`，必须输出“无需要替换的内容”。
4. **文档同步**：若引入新的配置项、端口或外部依赖，更新 `README.md`、`docs/architecture/PROJECT_STRUCTURE.md` 及相关部署文档。

## 5. 交付清单（Checklist）

- [ ] 需求文档中列出复用的组件及对应路径。
- [ ] 设计稿/接口定义引用现有服务或模板，避免全新实现。
- [ ] 代码落位符合目录约定，未新增 `_api`、`_form_service` 等违规命名。
- [ ] 配置、迁移、脚本、文档同步更新并注明验证步骤。
- [ ] 单测/集测标注 `@pytest.mark.unit`、`@pytest.mark.integration` 并通过 `make test`。
- [ ] `make quality`、`make format`、`./scripts/refactor_naming.sh --dry-run` 均通过。
- [ ] PR 描述中附带复用说明与验证记录，确保评审可快速确认无重复造轮子。

通过上述流程，可以用最少的增量代码交付新功能，并确保复用既有通用组件，降低维护成本。
