# 聚合服务重构待办

> 记录：`app/services/database_size_aggregation_service.py` 与 `app/tasks/database_size_aggregation_tasks.py`

## 当前状态
- 仍使用标准库 `logging`，未接入统一的 `structlog` 日志接口。
- 多处返回 `{"success": ...}` / `{"error": ...}` 字典，尚未切换到 `unified_success_response` / `unified_error_response` 体系。
- 函数返回结构与同步会话 (`sync_sessions`) 以及手动聚合路由 (`app/routes/aggregations.py`) 紧密耦合，直接调整会触发连锁改动，风险较高。

## 后续重构建议
1. 在 `DatabaseSizeAggregationService` 内拆分聚合结果结构，明确 `completed / skipped / failed` 等状态，并抛出自定义异常 (`DatabaseError`、`NotFoundError`)。
2. 调整 `database_size_aggregation_tasks`，让定时任务统一解析新状态并通过统一日志接口输出，同时更新同步会话状态写入逻辑。
3. 等服务与任务完成改造后，再更新 `aggregations` 路由、调度器及相关调用方，替换旧的 `success` 判断与日志写法。
4. 最后补充/修正对应的单元测试与文档说明。

> 备注：在完成整体重构前，请避免对上述两个文件做局部调整，以免与后续统一改造冲突。
