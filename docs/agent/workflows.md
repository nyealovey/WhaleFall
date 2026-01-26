# 常见工作流（速查）

> 目标：把“新增/改造的典型步骤”固化为可复用 checklist，减少遗漏。

## 新增路由（页面或 API）

1. 在相应模块创建路由：`app/routes/**` 或 `app/api/v1/**`
2. 尽量使用 `safe_route_call` 做统一错误处理与结构化日志：`app/infra/route_safety.py`
3. API 返回统一响应封套：`app/utils/response_utils.py`
4. 必要时注册蓝图（按现有模式在应用初始化处注册）
5. 需要权限/CSRF 时使用现有装饰器（如 `app/utils/decorators.py`）
6. 补测试（至少 unit），并跑 `uv run pytest -m unit`

## 新增后台任务（APScheduler）

1. 在 `app/tasks/` 定义任务
2. 在 `app/scheduler.py` 注册
3. 确保任务在 Flask `app.app_context()` 内运行
4. 如需常量/作业配置，按现有约定更新 `app/core/constants/`（若存在）
5. 补充任务的幂等性/失败处理与可观测性（日志字段/告警留钩子）

参见（SSOT）：`docs/Obsidian/standards/backend/standard/task-and-scheduler.md`

## 新增 Grid.js 列表页（UI）

1. 使用 `GridWrapper`：`app/static/js/common/grid-wrapper.js`
2. 后端 API 支持分页参数 `page`/`limit`，并返回统一封套
3. 前端使用 `Views.GridPage.mount()` 做 wiring（筛选/分页/URL 同步）
4. 需要筛选时复用 FilterCard，并确保防抖与 URLSync 一致
5. 对照迁移 checklist 自检

- 标准（SSOT）：`docs/Obsidian/standards/ui/gate/grid.md`
- Checklist：`docs/Obsidian/reference/development/gridjs-migration-checklist.md`

## 新增数据库类型（多数据库适配）

当前（V1）通常涉及：模型/迁移/适配器/分类器/同步逻辑。

未来（V2）目标是：新增带 schema 定义的适配器即可（见 V2 设计文档）。

- 适配器入口：`app/services/connection_adapters/adapters/`
- 分类相关：`app/services/account_classification/`
- V2 设计：`docs/Obsidian/architecture/account-classification-v2-design.md`
