# 架构与关键模式（速查）

> 这是一份帮助快速定位代码位置、避免踩坑的速查。规范与细节以 `docs/Obsidian/standards/` 为 SSOT。

## 技术栈（概览）

Flask、SQLAlchemy、APScheduler、Redis、PostgreSQL（主库）、Bootstrap 5、Grid.js。

## 目录结构（高层）

- `app/routes/`：路由控制器（按域划分）
- `app/models/`：SQLAlchemy ORM 模型
- `app/services/`：业务逻辑层（同步/分类/聚合等）
- `app/tasks/`：后台任务（APScheduler 作业）
- `app/utils/`：工具函数与辅助模块
- `app/templates/`：Jinja2 模板
- `app/static/`：前端资源（JS/CSS）
- `migrations/`：Alembic 迁移
- `sql/`：初始化与运维 SQL

## 配置管理（必须）

- 所有配置集中在 `app/settings.py`：解析环境变量、默认值、校验。
- 新增/调整配置项必须走 `app/settings.py`（禁止硬编码/散落在模块里）。
- 参考：`docs/Obsidian/standards/backend/standard/configuration-and-secrets.md`

## 路由安全模式（safe_route_call）

所有路由尽量使用 `app/infra/route_safety.py` 的 `safe_route_call` 统一错误处理与结构化日志（尤其是 API）。

```python
from flask import Response

from app.infra.route_safety import safe_route_call
from app.utils.response_utils import jsonify_unified_success


def example_view() -> Response:
    def _execute() -> Response:
        payload: dict = {}
        return jsonify_unified_success(data=payload)

    return safe_route_call(
        _execute,
        module="example",
        action="example_view",
        public_error="操作失败",
        context={},
    )
```

## API 响应封套（必须）

统一使用 `app/utils/response_utils.py`：

- 成功：`jsonify_unified_success(data=..., message=...)`
- 错误：`jsonify_unified_error_message(message=..., status_code=...)`

参见：`docs/Obsidian/standards/backend/gate/layer/api-layer.md#响应封套(JSON Envelope)`

## 数据库适配器（多数据库支持）

- 基础适配器：`app/services/connection_adapters/adapters/base_adapter.py`
- 数据库专用适配器：PostgreSQL/MySQL/SQL Server/Oracle
- 一般通过工厂模式实例化适配器（根据实例类型选择实现）

## 账户同步（两阶段）

两阶段同步（轻量清单 → 重量权限详情），数据库差异逻辑在：

- `app/services/accounts_sync/adapters/`

## 账户分类（V2 进行中）

- 分类器：`app/services/account_classification/classifiers/`
- 编排器：`app/services/account_classification/orchestrator.py`
- 设计文档（V2）：`docs/Obsidian/architecture/account-classification-v2-design.md`

## 容量聚合 / 时序数据

容量聚合相关的任务通常通过 APScheduler 定期运行（聚合表/分区管理等）。

常见表（按现有命名）：

- 原始数据：`database_size_stat`、`instance_size_stat`
- 聚合数据：`database_size_aggregation`、`instance_size_aggregation`

## 任务调度（必须）

- 调度器初始化：`app/scheduler.py`
- 任务定义：`app/tasks/`
- 所有任务必须在 Flask `app.app_context()` 内运行

参见：`docs/Obsidian/standards/backend/standard/task-and-scheduler.md`

## 结构化日志

- structlog 配置：`app/utils/structlog_config.py`
- 上下文变量：`app/utils/logging/context_vars.py`
- 统一日志表：`unified_log`
- UI 查看统一日志：`/history/logs`

## 安全与敏感数据（要点）

- 数据脱敏工具：`app/utils/sensitive_data.py`
- 密码/凭据加密：`app/utils/password_crypto_utils.py`（密钥配置见 `app/settings.py`）
- CSRF：全局 `CSRFProtect`（`app/__init__.py`）+ 路由级 `require_csrf`（`app/utils/decorators.py`）

## 性能（提醒）

- Redis 缓存与 TTL：通过 Settings 统一配置
- JSONB 列索引：优先考虑 GIN（按实际查询模式落地）
- 列表类端点必须分页（避免一次性全量返回）

## 前端：Grid.js 列表页

- Grid 封装：`app/static/js/common/grid-wrapper.js`（`GridWrapper`）
- 列表页骨架：`window.Views.GridPage.mount(...)`（收敛 wiring）
- 分页参数：`page`（从 1 开始）与 `limit`

关键前端组件（按现有封装）：

- `FilterCard`：`app/static/js/common/filter-card.js`（统一筛选 UI，带防抖）
- `ActionDelegation`：批量操作与行动作（按各页封装位置复用）
- `URLSync`：筛选/分页状态与 URL 同步（按各页封装位置复用）
- `ExportButton`：CSV/Excel 导出（按各页封装位置复用）

**必须遵循（SSOT）**：`docs/Obsidian/standards/ui/gate/grid.md`

**迁移交付自检**：`docs/Obsidian/reference/development/gridjs-migration-checklist.md`

## 关键参考文件（入口）

- `AGENTS.md`：仓库协作规则与硬约束
- `app/settings.py`：配置管理
- `app/infra/route_safety.py`：路由错误处理模式（`safe_route_call`）
- `app/utils/response_utils.py`：统一响应封套
- `app/static/js/common/grid-wrapper.js`：前端 Grid 封装
- `docs/Obsidian/standards/backend/README.md`：后端规范索引
- `docs/Obsidian/standards/ui/README.md`：UI 规范索引
