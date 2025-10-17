# 聚合服务重构待办

> 记录：`app/services/database_size_aggregation_service.py` 与 `app/tasks/database_size_aggregation_tasks.py`

## 当前状态
- ✅ `DatabaseSizeAggregationService` 已改用统一的 `structlog` 接口，聚合结果以 `completed / skipped / failed` 状态返回，并在关键异常场景抛出 `DatabaseError`、`NotFoundError` 等自定义异常。
- ✅ `database_size_aggregation_tasks` 完成重写，定时任务基于新状态模型更新同步会话记录并输出结构化日志，所有结果字典移除 `success` 兼容字段。
- ✅ `app/routes/aggregations.py` 中的手动触发端点已切换至新结果结构，去除了旧的兼容逻辑。

## 后续工作
1. 评估是否需要补充针对聚合服务的单元测试与集成测试，覆盖 `skipped` / `failed` 场景。
2. 观察部署后的同步日志与会话记录，确认新结构与监控告警兼容。
3. 若前端仍引用旧字段（如 `aggregations_created`），同步更新消费逻辑或在接口文档中明确字段替换。
