# Pyright 专项修复方案：reportAttributeAccessIssue（基于 2025-12-15 13:05 报告）

最新报告：`docs/reports/pyright_full_2025-12-15_130530.txt`  
本规则命中数：**255**（总错误 893）  
目标：继续集中清理 AttributeAccess，预期再减 150+ 条。

## 优先修复文件清单（按出现频次/影响度）
- **查询链/分页/排序**（按最新报告高频度）  
  - `app/routes/accounts/sync.py`（新增多个 returnType + AttributeAccess）
  - `app/routes/accounts/statistics.py`
  - `app/routes/databases/ledgers.py`、`app/routes/databases/capacity_sync.py`
  - `app/routes/history/logs.py`、`app/routes/history/sessions.py`
  - `app/routes/instances/detail.py`、`app/routes/instances/manage.py`、`app/routes/instances/batch.py`
  - `app/routes/tags/manage.py`、`app/routes/tags/bulk.py`
  - `app/routes/capacity/*`（aggregations/databases/instances）
  - `app/services/statistics/database_statistics_service.py`
  - `app/services/partition_management_service.py`
  - `app/tasks/capacity_collection_tasks.py`、`app/tasks/partition_management_tasks.py`

- **关系字段缺失/错误类型**  
  - `app/models/credential.py`（relationship 到 Instance? 行为检查）  
  - `app/models/instance.py`（tags/query 相关）  
  - `app/models/unified_log.py`（字段/关系 + to_china 传 Column）

- **SQL 查询/适配器**  
  - `app/services/accounts_sync/adapters/sqlserver_adapter.py`（`setdefault/execute_query` 等）  
  - `app/services/database_type_service.py`（query 链）  
  - `app/services/form_service/resource_service.py`（`current_app.logger` 已有类型，视情况 cast）

- **工具/日志**  
  - `app/utils/structlog_config.py`、`app/utils/logging/*`
  - `app/utils/sensitive_data.py`（items/get 访问）

## 处理策略
1) **补关系/字段声明**：在模型中声明缺失的 relationship/列（如 `trend_direction`、`assigned_at` 已添加），确保访问存在。  
2) **Query 类型兜底**：对热点查询加 `cast(Query[Any], ...)` 或在 stub 已覆盖的方法仍报错时局部 cast。  
3) **避免 Column 直接布尔/方法调用**：取实际值或使用表达式 API；序列化时先赋临时变量。  
4) **分页/contains/in_/is_**：若 stub 覆盖仍报，局部 `cast(Query[Any], q)` 后链式调用。  
5) **字典方法 on Any（setdefault/get/items）**：为推断不出的对象显式 `Mapping[str, Any]` 或转换为 `dict(...)`。  

## 执行顺序建议
1. 路由层：capacity/accounts/databases/instances/tags/history 下的查询链与分页。  
2. 服务层：statistics、partition_management、database_type_service。  
3. 任务与适配器：capacity_collection_tasks、partition_management_tasks、sqlserver_adapter。  
4. 模型层：unified_log、credential/instance 关系字段补齐。  
5. 工具层：structlog/logging/sensitive_data 等零散报错。

## 验证
- 每一批次后运行：`npx pyright --warnings app/routes/<子目录>` 或对应文件集；`ruff check <文件>` 确保无新 Ruff 告警。  
- 更新报告快照并在本计划中勾选“已处理”文件。  

## 预期收敛
- 路由 + 服务 + 任务 + 适配器的 AttributeAccess 可下降约 200+；模型/工具补充后预计剩余零星十余条。  
