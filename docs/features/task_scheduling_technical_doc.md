# 任务调度功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供系统定时任务的统一管理，包括创建、启用/禁用、立即执行、重新加载配置。
- 基于 APScheduler 的 `BackgroundScheduler` 管理所有任务执行及持久化。
- 前端提供可视化管理界面，支持查看任务状态、触发器配置与执行结果。

来源：后端蓝图 `scheduler_bp` (`app/routes/scheduler.py`)、调度器核心 `TaskScheduler` (`app/scheduler.py`)、模板 `app/templates/scheduler/management.html`、脚本 `app/static/js/pages/scheduler/management.js`、任务实现 `app/tasks/*`。

### 1.2 核心能力与代码定位
- 调度器初始化与默认任务加载：`app/scheduler.py` 20-365 行。
- 调度器启动入口（命令行/守护进程）：`app/scheduler.py` 168-185 行。
- 任务列表接口：`app/routes/scheduler.py` 43-107 行。
- 任务启用/禁用/暂停/恢复：`app/routes/scheduler.py` 144-224 行。
- 任务立即执行：`app/routes/scheduler.py` 226-270 行。
- 任务重新加载：`app/routes/scheduler.py` 276-337 行。
- 触发器更新：`app/routes/scheduler.py` 339-518 行。
- 前端任务管理界面：`management.html` 10-332 行，脚本 `management.js` 全文。
- 默认任务定义：`app/config/scheduler_tasks.yaml`、`app/tasks/*.py`。

## 2. 架构设计

### 2.1 模块关系
```
┌────────────────────────┐    ┌──────────────────────────┐    ┌────────────────────────┐
│ 前端界面层             │    │ Flask 路由层              │    │ 调度器&任务实现         │
│ management.html + JS   │◄──►│ scheduler_bp / APIResponse│◄──►│ TaskScheduler + app/tasks│
└────────────────────────┘    └──────────────────────────┘    └────────────────────────┘
```

### 2.2 关键组件
- 调度器核心：`TaskScheduler` 提供实例管理和任务操作 (`app/scheduler.py` 20-118)。
- 路由蓝图：`scheduler_bp` 定义页面与全部 API (`app/routes/scheduler.py`)。
- 持久化配置：`userdata/scheduler.db` 由 APScheduler `SQLAlchemyJobStore` 管理。
- 默认任务配置：`app/config/scheduler_tasks.yaml`，加载到调度器中。
- 实际任务函数：位于 `app/tasks/` 目录，使用服务层完成实际业务。

## 3. 调度器实现

### 3.1 初始化流程
```30:64:app/scheduler.py
class TaskScheduler:
    def _setup_scheduler(self):
        jobstores = {"default": SQLAlchemyJobStore(url=database_url)}
        executors = {"default": ThreadPoolExecutor(max_workers=5)}
        job_defaults = {...}
        self.scheduler = BackgroundScheduler(...)
        self.scheduler.add_listener(...)
```
- 使用 `userdata/scheduler.db` 持久化任务。
- 默认执行器为线程池，最大 5 个工作线程。
- 默认任务配置：合并相同任务、最大实例数 1、容忍 300 秒误差。
- 注册执行成功/失败事件 (`_job_executed` / `_job_error`)。

### 3.2 启动与初始化
```130:165:app/scheduler.py
def init_scheduler(app):
    if scheduler.app is not None: ...
    scheduler.app = app
    ensure sqlite file
    scheduler.start()
    time.sleep(2)
    _load_existing_jobs()
    _add_default_jobs()
```
- 保证只初始化一次。
- 确保数据库存在后启动调度器。
- 加载现有任务 `_load_existing_jobs`，若为空加载默认任务 `_add_default_jobs`。

### 3.3 默认任务加载
```236:365:app/scheduler.py
def _load_tasks_from_config(force=False):
    read app/config/scheduler_tasks.yaml
    import任务函数
    scheduler.add_job(func, trigger_type, ...)
```
- 支持强制重新加载（删除后重新添加）。
- 若配置文件缺失，回退到硬编码默认任务 `_add_hardcoded_default_jobs`。
- 支持的任务函数：`sync_accounts`、`collect_database_sizes`、`calculate_database_size_aggregations`、`monitor_partition_health` 等。

### 3.4 任务执行回调
```65:72:app/scheduler.py
def _job_executed(...): logger.info(...)
def _job_error(...): logger.error(...)
```
- 通过结构化日志记录任务执行结果和异常。

### 3.5 任务接口封装
- `add_job/remove_job/get_jobs/pause_job/resume_job` 为 APScheduler 操作的轻量封装（88-117 行）。
- `start_scheduler()` 提供独立启动入口（168-185 行）。

## 4. 路由层实现

### 4.1 页面渲染
```35:41:app/routes/scheduler.py
@scheduler_bp.route("/")
@login_required
@scheduler_view_required
def index():
    return render_template("scheduler/management.html")
```
- 权限：登录 + 定时任务查看权限。

### 4.2 列表与详情
- `GET /scheduler/api/jobs`：返回所有任务（触发器信息、状态等）（43-107 行）。
- `GET /scheduler/api/jobs/<id>`：返回单任务详情（109-136 行）。
- 数据通过 `APIResponse.success/error` 统一包装。

### 4.3 任务控制
- 禁用/启用：`POST /api/jobs/<id>/disable|enable`（144-191 行）。
- 暂停/恢复：`POST /api/jobs/<id>/pause|resume`（194-224 行）。
- 立即执行：`POST /api/jobs/<id>/run`（226-270 行）。
  - 内置任务直接调用函数；自定义任务需要重新创建应用上下文。

### 4.4 重新加载与更新
- `POST /api/jobs/reload`：删除所有任务并从配置重建（276-337 行）。
- `PUT /api/jobs/<id>`：更新触发器配置，仅允许内置任务（339-518 行）。
  - `_build_trigger` 支持 cron/interval/date 三类触发器。

### 4.5 权限控制
- 依赖 `scheduler_view_required`、`scheduler_manage_required` (`app/utils/decorators.py`)，限制非管理员操作。
- 内置任务 ID 集合 `BUILTIN_TASK_IDS` 用于保护核心任务（19-26 行）。

## 5. 前端实现

### 5.1 页面模板 `app/templates/scheduler/management.html`
- 页面头部与按钮布局：10-27 行。
- 任务列表容器：34-63 行。
- 添加/编辑模态框（预设字段、cron 输入等）：65-330 行。
- 依赖脚本：`management.js`（335-337 行）。

### 5.2 脚本 `app/static/js/pages/scheduler/management.js`
- 初始化流程：`initializeSchedulerPage` 36-41 行。
- 事件绑定：`initializeEventHandlers` 43-147 行。
- 任务列表加载与渲染：`loadJobs` 149-183 行、`displayJobs` 186-198 行、`createJobCard` 200-245 行。
- 状态按钮操作：`enableJob`/`disableJob`/`runJobNow` 330-411 行。
- 编辑逻辑：`editJob` 414-518 行，`updateJob` 521-624 行。
- 添加任务：`addJob` 677-749 行（调用 `/scheduler/api/jobs/by-func`）。
- 重新初始化按钮：`#purgeKeepBuiltinBtn` 91-136 行，对应 `POST /api/jobs/reload`。
- 辅助函数：通知、时间格式化、加载状态等 756-838 行。

### 5.3 交互流程
1. 页面加载调用 `initializeSchedulerPage`，拉取任务数据。
2. 多种按钮触发对应 API，成功后刷新任务列表并提示。
3. 编辑模态支持 cron 参数实时预览，提交后调用触发器更新接口。

## 6. 默认任务与任务实现

### 6.1 配置文件 `app/config/scheduler_tasks.yaml`
- 定义 `default_tasks` 列表，每项包含 `id/name/function/trigger_type/trigger_params/enabled/description`。
- 例如 `collect_database_sizes` 每日 3 点执行容量同步，`calculate_database_size_aggregations` 每日 4 点执行聚合。

### 6.2 任务函数示例
- 容量采集：`collect_database_sizes` (`app/tasks/database_size_collection_tasks.py` 17-826 行) 调用 `DatabaseSizeCollectorService`、`SyncSessionService`。
- 聚合统计：`calculate_database_size_aggregations` (`app/tasks/database_size_aggregation_tasks.py` 17-200 行) 使用 `DatabaseSizeAggregationService` 生成周期数据。
- 账户同步、日志清理、分区管理等任务分别位于 `app/tasks/legacy_tasks.py`、`app/tasks/partition_management_tasks.py`。

## 7. 权限与安全
- 所有页面/API 均需登录。
- 查看接口需 `scheduler_view_required`，管理操作需 `scheduler_manage_required`，参见 `app/utils/decorators.py`。
- 内置任务通过 ID 白名单防止删除关键任务。
- 前端请求携带 CSRF Token (`management.js` 中 Ajax 请求统一设置)。
- 任务立即执行时按任务类型选择合适的执行方式，并捕获异常返回。

## 8. 日志与审计
- 调度器事件通过 `TaskScheduler` 的 `_job_executed` 和 `_job_error` 记录结构化日志。
- 路由层所有操作使用 `system_logger` 记录（例如 `get_jobs`、`reload_jobs`）。
- 任务函数内部使用业务日志（`get_sync_logger` 等）记录执行详情。

## 9. 扩展能力
- `_reload_all_jobs()` 支持运行时重新加载配置，便于部署后调整任务。
- `_add_hardcoded_default_jobs()` 提供配置缺失时的 fallback。
- 可通过 `scheduled_task` 装饰器（445-454 行）标记任务元信息，便于未来做自动注册。
- `POST /api/jobs/by-func`（在路由中另行定义）支持基于函数名新增任务，前端已集成调用。

## 10. 测试与运维建议
- 单元测试：验证 `_load_tasks_from_config` 加载逻辑、`reload_jobs` 接口返回值、触发器构建 `_build_trigger`。
- 集成测试：模拟管理员身份调用 API，覆盖成功与失败场景。
- 前端测试：使用 Cypress/Jest 验证任务列表渲染、模态框交互、按钮调用。
- 运维：生产环境建议将 `jobstore` 指向 PostgreSQL（配置可在 `Config` 中覆盖）。
- 监控：可扩展调度器健康检查接口与执行日志表（示例见旧文档，可结合 `TaskExecutionLog` 模型）。

## 11. 配置要点
- 在 `create_app` 中注册 `scheduler_bp`，URL 前缀通常为 `/scheduler`。
- 调度器在应用启动时调用 `init_scheduler(app)`；如需独立进程，可运行 `start_scheduler()`。
- 环境变量可覆盖默认路径、最大线程数等参数。

## 12. 后续优化方向
- 引入任务执行历史持久化与可视化（目前仅日志）。
- 实现任务依赖/分组/模板系统（基础结构在旧文档可参考）。
- 完善前端添加任务功能（当前 demo 仅按函数创建）。
- 扩展告警服务，结合 `alert_service` 推送任务失败通知。
