# 命名与路径重构方案

## 目标

确立一套覆盖后台路由、前端模板/资源与服务层的统一命名体系，做到：
1. 所有 URL 使用 kebab-case，结构固定为 `/{domain}/{resource}`（集合）或 `/{domain}/{resource}/{resource_id}`（实体）。
2. 蓝图、服务、前端目录名称与 URL 完全对齐，禁止出现 `_`、缩写或无语义后缀。
3. API 与页面共享命名空间，API 子路径固定为 `/{domain}/api/{resource}`，避免重复 `api_`、`_api` 前后缀。
4. 单复数约束：集合资源使用复数；具体实体及 Python 类使用单数；聚合函数名使用单数语义（例如 `get_database_aggregation`）。
5. 前端 JS/CSS 目录全部使用 kebab-case，与模板/蓝图保持一致。
6. `./scripts/refactor_naming.sh --dry-run` 必须返回“无需要替换的内容”。

## 命名域模型

| 业务域 | URL 前缀 | 蓝图命名 | 模板目录 | JS 目录 | 说明 |
| --- | --- | --- | --- | --- | --- |
| 数据库域（Databases） | `/databases` | `databases_ledgers_bp`、`databases_capacity_bp` | `app/templates/databases/` | `app/static/js/modules/views/databases/` | 数据库台账、容量采集与同步 API。 |
| 容量统计（Capacity） | `/capacity` | `capacity_instances_bp`、`capacity_databases_bp`、`capacity_aggregations_bp` | `app/templates/capacity/` | `app/static/js/modules/views/capacity/` | 承载实例/数据库容量趋势、聚合等页面。 |
| 账户域（Accounts） | `/accounts` | `accounts_bp`、`accounts_statistics_bp`、`accounts_sync_bp` 等 | `app/templates/accounts/` | `app/static/js/modules/views/accounts/` | 账户管理、统计、同步、分类等统一在该前缀下。 |
| 实例域（Instances） | `/instances` | `instances_bp`、`instances_detail_bp`、`instances_api_bp` | `app/templates/instances/` | `app/static/js/modules/views/instances/` | 实例管理、详情、批量任务及 REST API。 |
| 标签域（Tags） | `/tags` | `tags_bp`、`tags_bulk_bp`（批量） | `app/templates/tags/` | `app/static/js/modules/views/tags/` | 普通标签与批量任务分离命名空间。 |
| 历史域（History） | `/history` | `history_logs_bp`、`history_sessions_bp` | `app/templates/history/` | `app/static/js/modules/views/history/` | 日志、同步会话、操作追踪统一入口。 |
| 文件导出（Files） | `/files` | `files_bp` | 无页面（API 为主） | `app/static/js/modules/services/files/` | 所有导出/下载接口集中管理。 |
| 基础设施（Infrastructure） | `/infrastructure` | `infrastructure_connections_bp` 等 | `app/templates/infrastructure/` | `app/static/js/modules/views/infrastructure/` | 连接、主机、任务等底层能力。 |
| 安全域（Security） | `/security` | `security_credentials_bp` 等 | `app/templates/security/` | `app/static/js/modules/views/security/` | 凭据、用户、权限管理等。 |

### Databases 域

- 路径：`/databases/ledgers`（数据库台账）、`/databases/api/instances/<id>/sync-capacity`（容量同步）。
- API：`/databases/api/ledgers`、`/databases/api/ledgers/{database_id}/capacity-trend`、`/databases/api/instances/{instance_id}/sync-capacity`。
- 蓝图：`databases_ledgers_bp`、`databases_capacity_bp`，位于 `app/routes/databases/`。
- 服务：`app/services/ledgers/database_ledger_service.py`、`app/services/database_sync/*`。
- 前端：使用 `app/static/js/modules/views/databases/ledgers.js`、`app/static/js/bootstrap/databases/ledgers.js`。

### Capacity 域

- 路径：`/capacity/instances`、`/capacity/databases`。
- API：`/capacity/api/instances`、`/capacity/api/databases`、`/capacity/api/instances/{instance_id}/trend`、`/capacity/api/aggregations/current`。
- 蓝图：`capacity_instances_bp`、`capacity_databases_bp`、`capacity_aggregations_bp`。
- 前端资源移动到 `app/static/js/modules/views/capacity/instances.js`、`.../databases.js`，CSS 路径 `app/static/css/pages/capacity/`。

### Accounts 域

- 路径：
  - 列表 `GET /accounts`
  - 统计 `GET /accounts/statistics`
  - 同步任务 `GET /accounts/sync`
  - 分类管理 `GET /accounts/classifications`
- 台账：`GET /accounts/ledgers`，API 统一走 `/accounts/api/ledgers`。
- API：`/accounts/api/accounts`、`/accounts/api/statistics`、`/accounts/api/sync`、`/accounts/api/classifications`、`/accounts/api/ledgers` 等。
- 蓝图：`accounts_bp`、`accounts_statistics_bp`、`accounts_sync_bp`、`accounts_classifications_bp`，全部放入 `app/routes/accounts/`，共享同一 `url_prefix='/accounts'`（子蓝图使用 `subdomain` 参数或 `url_prefix` 补充子路径）。
- SQLAlchemy 服务层位于 `app/services/accounts/`。

### Instances 域

- 路径：`/instances`（列表）、`/instances/<instance_id>`（详情）、`/instances/batch`（批量创建/删除）。
- API：`/instances/api/instances`、`/instances/api/health-check` 等。
- 蓝图：`instances_bp`、`instances_detail_bp`、`instances_batch_bp`。
- 容量统计不在该域，统一走 `/capacity`。

### Tags 域

- 路径：`/tags`（常规）、`/tags/bulk`（批量导入/导出、清洗）。
- API：`/tags/api/tags`、`/tags/bulk/api/import` 等。
- 蓝图：`tags_bp`、`tags_bulk_bp`。批量任务 JS/CSS/模板也放入 `tags/bulk` 子目录。

### History 域

- 路径：`/history/logs`、`/history/sessions`、`/history/audits`（预留）。
- API：`/history/api/logs`、`/history/api/sessions`。
- 蓝图：`history_logs_bp`、`history_sessions_bp`，源文件 `app/routes/history/logs.py` 等。

### Files 域

- 路径：`/files/api/<resource>-export`。
- 所有导出的 Flask 视图搬到 `app/routes/files.py`，使用 `url_prefix='/files'`。
- 前端若需要触发导出，采用 `data-export-url="{{ url_for('files.export_database_ledger') }}"`，同时 `export_database_ledger` 视图保持在 `files_bp` 下。

### Infrastructure 与 Security 域

- Infrastructure：`/infrastructure/connections`、`/infrastructure/schedulers` 等。
- Security：`/security/credentials`、`/security/users`、`/security/permissions`。
- 这些域帮助前后端在导航和文档中清晰划分职责，避免 `/connections`、`/credentials` 混淆。

## 实施步骤

1. **目录重构**
   - 创建 `app/routes/{domain}/` 层级；蓝图文件命名 `domain_resource.py`。
   - 服务层、模板、JS、CSS 同步使用 `domain/resource`、`domain/resource.js`、`domain/resource.css`。

2. **路由注册**
   - 在 `app/__init__.py` 中以域为单位注册蓝图：
     ```python
     from app.routes.accounts.ledgers import accounts_ledgers_bp
     app.register_blueprint(accounts_ledgers_bp, url_prefix='/accounts')
     ```
   - 所有新蓝图名称遵循 `domain_resource_bp` 模式。

3. **API 规范化**
  - 所有 API 路径形如 `/accounts/api/ledgers`，请求方法通过 REST 语义区分。
   - 函数命名使用 `list_accounts`, `get_account`, `export_database_ledger` 等动词短语。

4. **前端同步**
   - 模板路径 `app/templates/{domain}/{resource}.html`。
   - JS/CSS 引用示例：
     ```html
    <script src="{{ url_for('static', filename='js/modules/views/accounts/ledgers.js') }}"></script>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/pages/accounts/ledgers.css') }}">
     ```
  - API 调用通过 `data-api-url="{{ url_for('accounts_ledgers.list_accounts_data') }}"` 等方式注入。

5. **测试与脚本**
   - 更新 `tests/unit`、`tests/integration` 中的 URL 与蓝图引用。
   - 在每次提交前运行：
     ```bash
     ./scripts/refactor_naming.sh --dry-run
     make test
     make quality
     ```

6. **迁移策略**
   - 以域为单位完成改造后立即移除旧蓝图与路径，禁止在代码、模板、脚本或文档中继续引用旧 URL。
   - 不允许在 Nginx/Flask 层新增跳转或回退逻辑，所有调用方必须同步更新到新命名空间。

## 验证清单

- [ ] `/accounts/ledgers`、`/databases/ledgers` 页面与 API 可用，模板/JS 路径一致。
- [ ] `/capacity/instances`、`/capacity/databases` 控制台/图表交互正常，筛选卡片维持 `col-md-2 col-12`。
- [ ] `/accounts` 域下的列表、统计、同步、分类均使用统一 URL 与蓝图命名。
- [ ] `/tags/bulk` 承载全部批量任务，常规标签接口不暴露 `/batch` 字段。
- [ ] `/history/logs` 与 `/history/sessions` 的 API/视图均无 `_` 符号。
- [ ] `/files/api/*` 承接所有导出，其他蓝图不再直接暴露导出路径。
- [ ] `./scripts/refactor_naming.sh --dry-run` 输出“无需要替换的内容”。
- [ ] `make test`、`make quality`、`pytest --cov=app --cov-report=term-missing` 全部通过。

---

**维护要求**：新功能立项前必须在本文件新增命名记录；命名争议以此文档为准。任何未在此文档登记的路径或蓝图视为违规，代码评审需立即驳回并要求作者运行命名守卫脚本。EOF
