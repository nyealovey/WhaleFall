# 账户同步功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供账户同步记录的统一管理界面，支持分页、筛选、聚合显示。
- 实现批量同步所有实例账户的功能，使用会话管理架构。
- 支持单个实例的账户同步操作。
- 提供同步详情查看，包括批量同步的实例级别统计。

### 1.2 代码定位
- 路由：`app/routes/account_sync.py`
- 模板：`app/templates/accounts/sync_records.html`
- 脚本：`app/static/js/pages/accounts/sync_records.js`
- 服务：`app/services/account_sync_service.py`、`app/services/sync_session_service.py`
- 模型：`app/models/sync_session.py`、`app/models/instance.py`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 前端 UI (sync_records.html) │
│  - 统一搜索表单            │
│  - 同步记录表格            │
│  - 详情模态框              │
└───────▲───────────┬──────┘
        │AJAX        │
┌───────┴───────────▼──────┐
│ Flask 路由 (account_sync_bp)│
│  - / (记录列表)           │
│  - /sync-all (批量同步)   │
│  - /sync-details-* (详情) │
│  - /instances/*/sync      │
└───────▲───────────┬──────┘
        │SQLAlchemy │服务调用
┌───────┴───────────▼──────┐
│ 数据层与服务              │
│  - SyncSession (会话)     │
│  - Instance (实例)        │
│  - account_sync_service   │
│  - sync_session_service   │
└────────────────────────────┘
```

### 2.2 权限控制
- 所有接口使用 `@login_required`，查看操作需 `@view_required`，同步操作需 `@update_required`（路由 27）。

## 3. 前端实现

### 3.1 页面结构（`sync_records.html`）
- 统一搜索表单（21-37）：包含同步操作方式、状态筛选，使用 `unified_search_form.html` 组件。
- 同步记录表格（57-186）：显示开始/结束时间、耗时、类型、状态、数量统计、操作按钮。
- 详情模态框（246-261）：用于显示同步详情。
- 分页控件（189-229）：支持上一页/下一页和页码导航。

### 3.2 记录显示逻辑
- 聚合显示：批量类型（`manual_batch`、`manual_task`、`scheduled_task`）按时间或会话ID分组聚合。
- 单独显示：`manual_single` 类型记录直接显示。
- 状态徽章：根据 `record.status` 显示不同颜色的状态标识（134-138）。
- 同步操作方式徽章：区分手动单次、批量、任务等操作方式（109-133）。

### 3.3 交互功能（`sync_records.js`）
- 详情查看：`viewDetails()`（18-45）显示单个记录详情。
- 批量详情：`viewBatchDetails()`（113-151）调用 `/sync-details-batch` 获取聚合记录详情。
- 失败详情：`viewFailedDetails()`（154-192）专门显示失败的实例记录。
- 重试同步：`retrySync()`（48-79）POST `/accounts/sync/${instanceId}` 重试单个实例。
- 统一搜索：`initUnifiedSearch()`（406-454）集成搜索组件，`applyFilters()`（457-483）应用筛选条件。

### 3.4 模态框展示
- 批量详情：`showBatchDetailsModal()`（195-222）显示成功/失败统计和实例列表。
- 失败详情：`showFailedDetailsModal()`（308-327）专门展示失败的实例信息。
- 动态生成：通过 `createBatchDetailsModalHtml()`（225-305）和 `createFailedDetailsModalHtml()`（330-382）动态创建模态框内容。

## 4. 后端路由实现（`account_sync.py`）

### 4.1 记录列表接口
- `GET /`（34-346）：支持分页、同步操作方式、状态、时间范围筛选。
- 聚合逻辑（77-212）：
  - 批量类型按 `session_id` 或时间分组。
  - 统计成功/失败实例数、账户数量、增删改数量。
  - 创建 `AggregatedRecord` 类（157-191）统一显示格式。
- 分页处理（214-249）：手动分页，支持 `iter_pages()` 方法兼容 Flask-SQLAlchemy。

### 4.2 批量同步接口
- `POST /sync-all`（348-550）：
  - 创建同步会话（370-374）。
  - 遍历所有活跃实例，调用 `account_sync_service.sync_accounts()`（411-413）。
  - 使用 `sync_session_service` 管理实例记录状态（401-426、435-439、464-469）。
  - 统计成功/失败数量，更新会话统计（491-492）。
  - 记录详细的操作日志（507-518）。

### 4.3 详情查看接口
- `GET /sync-details-batch`（553-614）：根据记录ID列表获取批量同步详情，按实例去重。
- `GET /sync-details/<sync_id>`（616-650）：获取单个同步会话的详情和关联实例记录。

### 4.4 单实例同步接口
- `POST /instances/<instance_id>/sync`（653-736）：
  - 调用 `account_sync_service.sync_accounts()`（673）。
  - 更新实例同步计数（677-678）。
  - 记录操作日志（662-670、681-688、696-705、716-725）。

## 5. 数据模型与服务

### 5.1 核心模型
- `SyncSession`：同步会话记录，包含 `session_id`、`sync_type`、`sync_category`、`status` 等字段。
- `Instance`：数据库实例，包含 `is_active`、`sync_count` 等字段。
- 关联关系：`SyncSession.instance_records` 获取会话下的实例记录。

### 5.2 服务层
- `account_sync_service`：核心同步逻辑，`sync_accounts(instance, sync_type, session_id)` 方法。
- `sync_session_service`：会话管理，包含 `create_session()`、`add_instance_records()`、`start_instance_sync()`、`complete_instance_sync()`、`fail_instance_sync()` 等方法。

## 6. 聚合显示逻辑

### 6.1 分组策略
- `manual_batch`：按 `session_id` 分组，同一批次的所有实例记录聚合。
- `manual_task`、`scheduled_task`：按时间分组，相同分钟的记录为一组。

### 6.2 统计计算
- 从 `instance_records` 关系获取详细统计（126-145）。
- 计算总账户数、新增、删除、修改数量。
- 统计成功和失败的实例数量。

### 6.3 显示优化
- 聚合记录显示为单行，包含所有统计信息。
- 支持查看详情按钮，显示具体的实例记录。
- 失败记录提供专门的失败详情查看。

## 7. 错误处理与日志

### 7.1 异常处理
- 路由层统一异常捕获（296-345、531-550、642-650、712-735）。
- 区分 AJAX 和普通请求的错误响应。
- 提供友好的错误提示和调试信息。

### 7.2 日志记录
- 使用 `log_info`、`log_error`、`log_warning` 记录操作过程。
- 包含用户ID、实例信息、会话ID等上下文。
- API 操作日志通过 `get_api_logger()` 记录（507-518）。

## 8. 性能优化

### 8.1 查询优化
- 使用 `filter_by(is_active=True)` 限制活跃实例。
- 聚合查询避免 N+1 问题，通过 `instance_records.all()` 批量获取。
- 手动分页减少数据库查询次数。

### 8.2 前端优化
- 模态框动态创建和销毁，避免 DOM 污染。
- 统一搜索组件复用，减少代码重复。
- 异步加载详情，提升用户体验。

## 9. 测试建议

### 9.1 功能测试
- 批量同步：验证多实例同步的统计准确性。
- 聚合显示：检查不同同步操作方式的分组逻辑。
- 详情查看：验证批量详情和失败详情的正确性。

### 9.2 性能测试
- 大量记录的分页性能。
- 聚合查询的响应时间。
- 并发同步操作的稳定性。

## 10. 后续优化方向

### 10.1 功能增强
- 添加同步进度实时显示。
- 支持同步任务的暂停和恢复。
- 提供同步历史的数据导出功能。

### 10.2 性能优化
- 实现同步记录的缓存机制。
- 优化大量实例的批量同步性能。
- 添加同步任务的异步队列处理。

### 10.3 监控告警
- 集成监控系统，实时跟踪同步状态。
- 添加同步失败的自动告警机制。
- 提供同步性能的统计分析。
