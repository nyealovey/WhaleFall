# WhaleFall API 和路由文档

> 基于 `app/routes/` 手动维护，最后更新时间：2025-11-21 16:47:09.

## 使用说明

- 每个小节对应单一源文件，方便按文件追踪路由。
- 同一蓝图可能在多个文件中扩展，本表使用 `app/__init__.py` 中注册的 URL 前缀计算完整路径。
- “页面路由”指返回 HTML 的视图；路径包含 `/api` 的统一归为 “API 接口”。

## 1. 认证模块

- **源文件**: `app/routes/auth.py`
- **蓝图与前缀**: `auth_bp` → `/auth`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/auth/change-password` | GET, POST | `change_password` | 修改密码页面 |
| `/auth/login` | GET, POST | `login` | 用户登录页面 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/auth/api/change-password` | POST | `submit_change_password` | 修改密码API |
| `/auth/api/csrf-token` | GET | `get_csrf_token` | 获取CSRF令牌 |
| `/auth/api/login` | POST | `authenticate_user` | 用户登录API |
| `/auth/api/logout` | GET, POST | `logout` | 用户登出 |
| `/auth/api/me` | GET | `me` | 获取当前用户信息 |
| `/auth/api/refresh` | POST | `refresh` | 刷新JWT token |


---

## 2. 账户管理模块

- **源文件**: `app/routes/account.py`
- **蓝图与前缀**: `account_bp` → `/account`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/account/` | GET | `list_accounts` | 账户列表页面 |
| `/account/<db_type>` | GET | `list_accounts` | 账户列表页面 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/account/api/<int:account_id>/permissions` | GET | `get_account_permissions` | 获取账户权限详情 |


---

## 3. 账户统计模块

- **源文件**: `app/routes/accounts/statistics.py`
- **蓝图与前缀**: `accounts_statistics_bp` → `/accounts`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/accounts/statistics` | GET | `statistics` | 账户统计页面 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/accounts/api/statistics` | GET | `get_account_statistics` | 账户统计API |
| `/accounts/api/statistics/classifications` | GET | `get_account_statistics_by_classification` | 按分类统计 |
| `/accounts/api/statistics/db-types` | GET | `get_account_statistics_by_db_type` | 按数据库类型统计 |
| `/accounts/api/statistics/summary` | GET | `get_account_statistics_summary` | 账户统计汇总 |


---

## 4. 账户分类模块

- **源文件**: `app/routes/accounts/classifications.py`
- **蓝图与前缀**: `accounts_classifications_bp` → `/accounts/classifications`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/accounts/classifications/` | GET | `index` | 账户分类管理首页 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/accounts/classifications/api/assignments` | GET | `get_assignments` | 获取账户分类分配 |
| `/accounts/classifications/api/assignments/<int:assignment_id>` | DELETE | `remove_assignment` | 移除账户分类分配 |
| `/accounts/classifications/api/auto-classify` | POST | `auto_classify` | 自动分类账户 - 使用优化后的服务 |
| `/accounts/classifications/api/classifications` | GET | `get_classifications` | 获取所有账户分类 |
| `/accounts/classifications/api/classifications` | POST | `create_classification` | 创建账户分类 |
| `/accounts/classifications/api/classifications/<int:classification_id>` | GET | `get_classification` | 获取单个账户分类 |
| `/accounts/classifications/api/classifications/<int:classification_id>` | PUT | `update_classification` | 更新账户分类 |
| `/accounts/classifications/api/classifications/<int:classification_id>` | DELETE | `delete_classification` | 删除账户分类 |
| `/accounts/classifications/api/colors` | GET | `get_color_options` | 获取可用颜色选项 |
| `/accounts/classifications/api/permissions/<db_type>` | GET | `get_permissions` | 获取数据库权限列表 |
| `/accounts/classifications/api/rules` | GET | `list_rules` | 获取所有规则列表（按数据库类型分组） |
| `/accounts/classifications/api/rules` | POST | `create_rule` | 创建分类规则 |
| `/accounts/classifications/api/rules/<int:rule_id>` | GET | `get_rule` | 获取单个规则详情 |
| `/accounts/classifications/api/rules/<int:rule_id>` | PUT | `update_rule` | 更新分类规则 |
| `/accounts/classifications/api/rules/<int:rule_id>` | DELETE | `delete_rule` | 删除分类规则 |
| `/accounts/classifications/api/rules/filter` | GET | `get_rules` | 获取分类规则 |


---

## 5. 账户同步模块

- **源文件**: `app/routes/accounts/sync.py`
- **蓝图与前缀**: `accounts_sync_bp` → `/accounts/sync`

### 页面路由

*无此类路由*

### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/accounts/sync/api/instances/<int:instance_id>/sync` | POST | `sync_instance_accounts` | 同步指定实例的账户信息，统一返回 JSON |
| `/accounts/sync/api/sync-all` | POST | `sync_all_accounts` | 触发后台批量同步所有实例的账户信息 |


---

## 6. 容量聚合模块

- **源文件**: `app/routes/capacity/aggregations.py`
- **蓝图与前缀**: `capacity_aggregations_bp` → `/capacity`

### 页面路由

*无此类路由*

### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/capacity/api/aggregations/current` | POST | `aggregate_current` | 手动触发当前周期数据聚合 |


---

## 7. 数据库容量同步模块

- **源文件**: `app/routes/databases/capacity_sync.py`
- **蓝图与前缀**: `databases_capacity_bp` → `/databases`

### 页面路由

*无此类路由*

### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/databases/api/instances/<int:instance_id>/sync-capacity` | POST | `sync_instance_capacity` | 同步指定实例的容量信息 |


---

## 8. 通用数据模块

- **源文件**: `app/routes/common.py`
- **蓝图与前缀**: `common_bp` → `/common`

### 页面路由

*无此类路由*

### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/common/api/databases-options` | GET | `get_database_options` | 获取指定实例的数据库下拉选项（通用） |
| `/common/api/dbtypes-options` | GET | `get_database_type_options` | 获取数据库类型选项（通用） |
| `/common/api/instances-options` | GET | `get_instance_options` | 获取实例下拉选项（通用） |


---

## 9. 连接管理模块

- **源文件**: `app/routes/connections.py`
- **蓝图与前缀**: `connections_bp` → `/connections`

### 页面路由

*无此类路由*

### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/connections/api/batch-test` | POST | `batch_test_connections` | 批量测试连接 |
| `/connections/api/status/<int:instance_id>` | GET | `get_connection_status` | 获取实例连接状态 |
| `/connections/api/test` | POST | `test_connection` | 测试数据库连接API |
| `/connections/api/validate-params` | POST | `validate_connection_params` | 验证连接参数 |


---

## 10. 凭据管理模块

- **源文件**: `app/routes/credentials.py`
- **蓝图与前缀**: `credentials_bp` → `/credentials`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/credentials/` | GET | `index` | 凭据管理首页 |
| `/credentials/<int:credential_id>` | GET | `detail` | 查看凭据详情 |
| `/credentials/<int:credential_id>/edit` | GET, POST | `edit` | 编辑凭据 |
| `/credentials/create` | GET, POST | `create` | 创建凭据 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/credentials/api/<int:credential_id>/edit` | POST | `update_credential` | 编辑凭据API |
| `/credentials/api/create` | POST | `create_credential` | 创建凭据API |
| `/credentials/api/credentials` | GET | `list_credentials` | 获取凭据列表API |
| `/credentials/api/credentials/<int:credential_id>` | GET | `get_credential` | 获取凭据详情API |
| `/credentials/api/credentials/<int:credential_id>/delete` | POST | `delete` | 删除凭据 |


---

## 11. 仪表板模块

- **源文件**: `app/routes/dashboard.py`
- **蓝图与前缀**: `dashboard_bp` → `/dashboard`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/dashboard/` | GET | `index` | 系统仪表板首页 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/dashboard/api/activities` | GET | `list_dashboard_activities` | 获取最近活动API - 已废弃，返回空数据 |
| `/dashboard/api/charts` | GET | `get_dashboard_charts` | 获取图表数据API |
| `/dashboard/api/overview` | GET | `get_dashboard_overview` | 获取系统概览API |
| `/dashboard/api/status` | GET | `get_dashboard_status` | 获取系统状态API |


---

## 12. 数据库聚合页面模块

- **源文件**: `app/routes/database_aggregations.py`
- **蓝图与前缀**: `database_aggregations_bp` → `/database_aggregations`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/database_aggregations/` | GET | `database_aggregations` | 数据库统计聚合页面（数据库统计层面） |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/database_aggregations/api/databases/aggregations` | GET | `get_database_aggregations` | 获取数据库统计聚合数据（数据库统计层面） |
| `/database_aggregations/api/databases/aggregations/summary` | GET | `get_database_aggregations_summary` | 获取数据库统计聚合汇总信息 |


---

## 13. 实例详情扩展模块

- **源文件**: `app/routes/instances/detail.py`
- **蓝图与前缀**: `instances_detail_bp` → `/instances`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/instances/<int:instance_id>` | GET | `detail` | 实例详情 |
| `/instances/<int:instance_id>/edit` | GET, POST | `edit` | 编辑实例 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/instances/api/<int:instance_id>/accounts/<int:account_id>/change-history` | GET | `get_account_change_history` | 获取账户变更历史 |
| `/instances/api/<int:instance_id>/edit` | POST | `update_instance_detail` | 编辑实例API |
| `/instances/api/databases/<int:instance_id>/sizes` | GET | `get_instance_database_sizes` | 获取指定实例的数据库大小历史数据 |
| `/instances/api/<int:instance_id>/accounts/<int:account_id>/permissions` | GET | `get_account_permissions` | 获取账户权限详情 |


---

## 14. 实例聚合模块

- **源文件**: `app/routes/instance_aggregations.py`
- **蓝图与前缀**: `instance_aggregations_bp` → `/instance_aggregations`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/instance_aggregations/instance` | GET | `instance_aggregations` | 实例统计聚合页面（实例统计层面） |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/instance_aggregations/api/instances/aggregations` | GET | `get_instance_aggregations` | 获取实例聚合数据（实例统计层面） |
| `/instance_aggregations/api/instances/aggregations/summary` | GET | `get_instance_aggregations_summary` | 获取实例聚合汇总信息（实例统计层面） |


---

## 15. 实例管理模块

- **源文件**: `app/routes/instances/manage.py`
- **蓝图与前缀**: `instances_bp` → `/instances`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/instances/` | GET | `index` | 实例管理首页 |
| `/instances/create` | GET, POST | `create` | 创建实例页面 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/instances/api` | GET | `list_instances_data` | 获取实例列表API |
| `/instances/api/<int:instance_id>` | GET | `get_instance_detail` | 获取实例详情API |
| `/instances/api/<int:instance_id>/accounts` | GET | `list_instance_accounts` | 获取实例账户数据API |
| `/instances/api/<int:instance_id>/delete` | POST | `delete` | 删除实例 |
| `/instances/batch/api/create` | POST | `create_instances_batch` | 批量创建实例 |
| `/instances/batch/api/delete` | POST | `delete_instances_batch` | 批量删除实例 |
| `/instances/api/create` | POST | `create_instance` | 创建实例API |

> **批量操作蓝图**: `instances_batch_bp`（源文件：`app/routes/instances/batch.py`）使用前缀 `/instances/batch` 暴露批量导入与删除接口。


---

## 16. 实例统计模块

- **源文件**: `app/routes/instances/statistics.py`
- **蓝图与前缀**: `instances_bp` → `/instances`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/instances/statistics` | GET | `statistics` | 实例统计页面 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/instances/api/statistics` | GET | `get_instance_statistics` | 获取实例统计API |


---

## 17. 健康检查模块

- **源文件**: `app/routes/health.py`
- **蓝图与前缀**: `health_bp` → `/health`

### 页面路由

*无此类路由*

### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/health/api/basic` | GET | `health_check` | 基础健康检查 |
| `/health/api/cache` | GET | `get_cache_health` | 缓存服务健康检查 |
| `/health/api/detailed` | GET | `detailed_health_check` | 详细健康检查 |
| `/health/api/health` | GET | `get_health` | 健康检查（供外部监控使用） |


---

## 18. 缓存管理模块

- **源文件**: `app/routes/cache.py`
- **蓝图与前缀**: `cache_bp` → `/cache`

### 页面路由

*无此类路由*

### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/cache/api/classification/clear` | POST | `clear_classification_cache` | 清除分类相关缓存 |
| `/cache/api/classification/clear/<db_type>` | POST | `clear_db_type_cache` | 清除特定数据库类型的缓存 |
| `/cache/api/classification/stats` | GET | `get_classification_cache_stats` | 获取分类缓存统计信息 |
| `/cache/api/clear/all` | POST | `clear_all_cache` | 清除所有缓存 |
| `/cache/api/clear/instance` | POST | `clear_instance_cache` | 清除实例缓存 |
| `/cache/api/clear/user` | POST | `clear_user_cache` | 清除用户缓存 |
| `/cache/api/stats` | GET | `get_cache_stats` | 获取缓存统计信息 |


---

## 19. 日志模块

- **源文件**: `app/routes/history/logs.py`
- **蓝图与前缀**: `history_logs_bp` → `/history/logs`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/history/logs/` | GET | `logs_dashboard` | 日志中心仪表板 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/history/logs/api/detail/<int:log_id>` | GET | `get_log_detail` | 获取日志详情API |
| `/history/logs/api/modules` | GET | `list_log_modules` | 获取日志模块列表API |
| `/history/logs/api/search` | GET | `search_logs` | 搜索日志API |
| `/history/logs/api/statistics` | GET | `get_log_statistics` | 获取日志统计信息API |
| `/history/logs/api/stats` | GET | `get_log_stats` | 获取日志统计信息API |


---

## 20. 分区管理模块

- **源文件**: `app/routes/partition.py`
- **蓝图与前缀**: `partition_bp` → `/partition`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/partition/` | GET | `partitions_page` | 分区管理页面 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/partition/api/aggregations/core-metrics` | GET | `get_core_aggregation_metrics` | 获取核心聚合指标数据 |
| `/partition/api/cleanup` | POST | `cleanup_partitions` | 清理旧分区 |
| `/partition/api/create` | POST | `create_partition` | 创建分区 |
| `/partition/api/info` | GET | `get_partition_info` | 获取分区信息API |
| `/partition/api/statistics` | GET | `get_partition_statistics` | 获取分区统计信息 |
| `/partition/api/status` | GET | `get_partition_status` | 获取分区管理状态 |


---

## 21. 定时任务模块

- **源文件**: `app/routes/scheduler.py`
- **蓝图与前缀**: `scheduler_bp` → `/scheduler`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/scheduler/` | GET | `index` | 定时任务管理页面 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/scheduler/api/jobs` | GET | `get_jobs` | 获取所有定时任务 |
| `/scheduler/api/jobs/<job_id>` | GET | `get_job` | 获取指定任务详情 |
| `/scheduler/api/jobs/<job_id>` | PUT | `update_job_trigger` | 更新内置任务的触发器配置（仅限内置任务） |
| `/scheduler/api/jobs/<job_id>/pause` | POST | `pause_job` | 暂停任务 |
| `/scheduler/api/jobs/<job_id>/resume` | POST | `resume_job` | 恢复任务 |
| `/scheduler/api/jobs/<job_id>/run` | POST | `run_job` | 立即执行任务 |
| `/scheduler/api/jobs/reload` | POST | `reload_jobs` | 重新加载所有任务配置 |


---

## 22. 同步会话模块

- **源文件**: `app/routes/history/sessions.py`
- **蓝图与前缀**: `history_sessions_bp` → `/history/sessions`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/history/sessions/` | GET | `index` | 会话中心首页 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/history/sessions/api/sessions` | GET | `list_sessions` | 获取同步会话列表 API |
| `/history/sessions/api/sessions/<session_id>` | GET | `get_sync_session_detail` | 获取同步会话详情 API |
| `/history/sessions/api/sessions/<session_id>/cancel` | POST | `cancel_sync_session` | 取消同步会话 API |
| `/history/sessions/api/sessions/<session_id>/error-logs` | GET | `list_sync_session_errors` | 获取同步会话错误日志 API |


---

## 23. 标签管理模块

- **源文件**: `app/routes/tags.py`
- **蓝图与前缀**: `tags_bp` → `/tags`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/tags/` | GET | `index` | 标签管理首页 |
| `/tags/create` | GET, POST | `create` | 创建标签 |
| `/tags/edit/<int:tag_id>` | GET, POST | `edit` | 编辑标签 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/tags/api/categories` | GET | `list_tag_categories` | 获取标签分类列表API |
| `/tags/api/create` | POST | `create_tag` | 创建标签API |
| `/tags/api/delete/<int:tag_id>` | POST | `delete` | 删除标签 |
| `/tags/api/edit/<int:tag_id>` | POST | `update_tag` | 编辑标签API |
| `/tags/api/tags` | GET | `list_tag_options` | 获取标签列表API |
| `/tags/api/tags/<tag_name>` | GET | `get_tag_by_name` | 获取标签详情API |


---

## 24. 标签批量操作模块

- **源文件**: `app/routes/tags/bulk.py`
- **蓝图与前缀**: `tags_bulk_bp` → `/tags/bulk`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/tags/batch_assign` | GET | `batch_assign` | 批量分配标签页面 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/tags/bulk/api/tags` | GET | `list_all_tags` | 获取所有标签列表API (包括非活跃标签) |
| `/tags/bulk/api/assign` | POST | `batch_assign_tags` | 批量分配标签给实例 |
| `/tags/bulk/api/remove-all` | POST | `batch_remove_all_tags` | 批量移除实例的所有标签 |
| `/tags/bulk/api/remove` | POST | `batch_remove_tags` | 批量移除实例的标签 |
| `/tags/bulk/api/instance-tags` | POST | `list_instance_tags` | 获取实例的已关联标签API |
| `/tags/bulk/api/instances` | GET | `list_taggable_instances` | 获取所有实例列表API |


---

## 25. 用户管理模块

- **源文件**: `app/routes/users.py`
- **蓝图与前缀**: `users_bp` → `/users`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/users/` | GET | `index` | 用户管理首页 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/users/api/users` | GET | `list_users` | 获取用户列表API |
| `/users/api/users` | POST | `create_user` | 创建用户API |
| `/users/api/users/<int:user_id>` | GET | `get_user` | 获取单个用户信息API |
| `/users/api/users/<int:user_id>` | PUT | `update_user` | 更新用户API |
| `/users/api/users/<int:user_id>` | DELETE | `delete_user` | 删除用户API |
| `/users/api/users/stats` | GET | `get_user_stats` | 获取用户统计信息API |


---

## 26. 文件导入导出模块

- **源文件**: `app/routes/files.py`
- **蓝图与前缀**: `files_bp` → `/`

### 页面路由

*无此类路由*

### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/files/api/account-export` | GET | `export_accounts` | 导出账户数据为CSV |
| `/api/instance-export` | GET | `export_instances` | 导出实例数据为CSV |
| `/api/log-export` | GET | `export_logs` | 导出日志API |
| `/api/template-download` | GET | `download_instances_template` | 下载实例批量导入模板 |


---

## 27. 主路由模块

- **源文件**: `app/routes/main.py`
- **蓝图与前缀**: `main_bp` → `/`

### 页面路由

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/` | GET | `index` | 首页 - 重定向到登录页面 |
| `/.well-known/appspecific/com.chrome.devtools.json` | GET | `chrome_devtools` | 处理Chrome开发者工具的请求 |
| `/about` | GET | `about` | 关于页面 |
| `/apple-touch-icon-precomposed.png` | GET | `apple_touch_icon` | 提供 Apple Touch Icon，避免 Safari 等设备请求 404 |
| `/apple-touch-icon.png` | GET | `apple_touch_icon` | 提供 Apple Touch Icon，避免 Safari 等设备请求 404 |
| `/favicon.ico` | GET | `favicon` | 提供favicon.ico文件 |


### API 接口

| 路径 | 方法 | 处理函数 | 描述 |
|------|------|----------|------|
| `/admin/api/app-info` | GET | `app_info` | 获取应用信息（供前端展示应用名称等） |


---

## 统计汇总

- 页面路由: 34 条
- API 接口: 120 条
- 总路由: 154 条

*本页内容由脚本生成，如需更新请重新运行路由扫描脚本。*
