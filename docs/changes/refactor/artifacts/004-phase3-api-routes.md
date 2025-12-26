# Phase 3 `/api` 端点清单（自动生成）

> 注意: 本文件为生成产物，请勿手工编辑。
> 来源: `docs/reference/api/api-routes-documentation.md` 的 `### API 接口` 表格。
> 口径: 路径包含 `/api` 的 JSON API 端点。
> 去重规则: `METHOD + Path`。
> 总计: 131
> 生成命令: `python3 scripts/dev/docs/generate_api_routes_inventory.py`

---

## API 清单(按模块)

### 1. 认证模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/auth/api/change-password` | POST | 修改密码API |
| `/auth/api/csrf-token` | GET | 获取CSRF令牌 |
| `/auth/api/login` | POST | 用户登录API |
| `/auth/api/logout` | POST | 用户登出 |
| `/auth/api/me` | GET | 获取当前用户信息 |
| `/auth/api/refresh` | POST | 刷新JWT token |

### 2. 账户管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/accounts/api/ledgers` | GET | Grid.js 账户列表API |
| `/accounts/api/ledgers/<int:account_id>/permissions` | GET | 获取账户权限详情 |

### 3. 账户统计模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/accounts/api/statistics` | GET | 账户统计API |
| `/accounts/api/statistics/classifications` | GET | 按分类统计 |
| `/accounts/api/statistics/db-types` | GET | 按数据库类型统计 |
| `/accounts/api/statistics/summary` | GET | 账户统计汇总 |

### 4. 账户分类模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/accounts/classifications/api/assignments` | GET | 获取账户分类分配列表 |
| `/accounts/classifications/api/assignments/<int:assignment_id>` | DELETE | 移除账户分类分配 |
| `/accounts/classifications/api/auto-classify` | POST | 自动分类账户 - 使用优化后的服务 |
| `/accounts/classifications/api/classifications` | GET | 获取所有账户分类 |
| `/accounts/classifications/api/classifications` | POST | 创建账户分类 |
| `/accounts/classifications/api/classifications/<int:classification_id>` | DELETE | 删除账户分类 |
| `/accounts/classifications/api/classifications/<int:classification_id>` | GET | 获取单个账户分类 |
| `/accounts/classifications/api/classifications/<int:classification_id>` | PUT | 更新账户分类 |
| `/accounts/classifications/api/colors` | GET | 获取可用颜色选项 |
| `/accounts/classifications/api/permissions/<db_type>` | GET | 获取数据库权限列表 |
| `/accounts/classifications/api/rules` | GET | 获取所有规则列表(按数据库类型分组) |
| `/accounts/classifications/api/rules` | POST | 创建分类规则 |
| `/accounts/classifications/api/rules/<int:rule_id>` | DELETE | 删除分类规则 |
| `/accounts/classifications/api/rules/<int:rule_id>` | GET | 获取单个规则详情 |
| `/accounts/classifications/api/rules/<int:rule_id>` | PUT | 更新分类规则 |
| `/accounts/classifications/api/rules/filter` | GET | 获取分类规则 |
| `/accounts/classifications/api/rules/stats` | GET | 获取规则命中统计 |

### 5. 账户同步模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/accounts/sync/api/instances/<int:instance_id>/sync` | POST | 同步指定实例的账户信息,统一返回 JSON |
| `/accounts/sync/api/sync-all` | POST | 触发后台批量同步所有实例的账户信息 |

### 6. 容量聚合模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/capacity/api/aggregations/current` | POST | 手动触发当前周期数据聚合 |

### 7. 数据库容量同步模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/databases/api/instances/<int:instance_id>/sync-capacity` | POST | 同步指定实例的容量信息 |

### 8. 数据库台账模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/databases/api/ledgers` | GET | 获取数据库台账列表数据 |
| `/databases/api/ledgers/<int:database_id>/capacity-trend` | GET | 获取单个数据库的容量走势 |

### 9. 通用数据模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/common/api/databases-options` | GET | 获取指定实例的数据库下拉选项(通用) |
| `/common/api/dbtypes-options` | GET | 获取数据库类型选项(通用) |
| `/common/api/instances-options` | GET | 获取实例下拉选项(通用) |

### 10. 连接管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/connections/api/batch-test` | POST | 批量测试连接 |
| `/connections/api/status/<int:instance_id>` | GET | 获取实例连接状态 |
| `/connections/api/test` | POST | 测试数据库连接API |
| `/connections/api/validate-params` | POST | 验证连接参数 |

### 11. 凭据管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/credentials/api/<int:credential_id>/edit` | POST | 编辑凭据API |
| `/credentials/api/create` | POST | 创建凭据API |
| `/credentials/api/credentials` | GET | 获取凭据列表API |
| `/credentials/api/credentials` | POST | RESTful 创建凭据API,供前端 CredentialsService 使用 |
| `/credentials/api/credentials/<int:credential_id>` | GET | 获取凭据详情API |
| `/credentials/api/credentials/<int:credential_id>` | PUT | RESTful 更新凭据API |
| `/credentials/api/credentials/<int:credential_id>/delete` | POST | 删除凭据 |

### 12. 仪表板模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/dashboard/api/activities` | GET | 获取最近活动API (已废弃) |
| `/dashboard/api/charts` | GET | 获取仪表板图表数据 |
| `/dashboard/api/overview` | GET | 获取系统概览API |
| `/dashboard/api/status` | GET | 获取系统状态API |

### 13. 数据库聚合页面模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/capacity/api/databases` | GET | 获取数据库统计聚合数据(数据库统计层面) |
| `/capacity/api/databases/summary` | GET | 获取数据库统计聚合汇总信息 |

### 14. 实例详情扩展模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/api/<int:instance_id>/accounts/<int:account_id>/change-history` | GET | 获取账户变更历史 |
| `/instances/api/<int:instance_id>/accounts/<int:account_id>/permissions` | GET | 获取账户权限详情 |
| `/instances/api/<int:instance_id>/edit` | POST | 编辑实例API |
| `/instances/api/databases/<int:instance_id>/sizes` | GET | 获取指定实例的数据库大小数据(最新或历史) |

### 15. 实例聚合模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/capacity/api/instances` | GET | 获取实例聚合数据(实例统计层面) |
| `/capacity/api/instances/summary` | GET | 获取实例聚合汇总信息(实例统计层面) |

### 16. 实例管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/api/<int:instance_id>` | GET | 获取实例详情API |
| `/instances/api/<int:instance_id>/accounts` | GET | 获取实例账户数据API |
| `/instances/api/<int:instance_id>/delete` | POST | 删除实例 |
| `/instances/api/<int:instance_id>/restore` | POST | 恢复实例 |
| `/instances/api/create` | POST | 创建实例API |
| `/instances/api/instances` | GET | Grid.js 实例列表API |

### 17. 实例批量操作模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/batch/api/create` | POST | 批量创建实例 |
| `/instances/batch/api/delete` | POST | 批量删除实例 |

### 18. 实例统计模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/api/statistics` | GET | 获取实例统计API |

### 19. 健康检查模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/health/api/basic` | GET | 基础健康检查 |
| `/health/api/cache` | GET | 缓存服务健康检查 |
| `/health/api/detailed` | GET | 详细健康检查 |
| `/health/api/health` | GET | 健康检查(供外部监控使用) |

### 20. 缓存管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/cache/api/classification/clear` | POST | 清除分类相关缓存 |
| `/cache/api/classification/clear/<db_type>` | POST | 清除特定数据库类型的缓存 |
| `/cache/api/classification/stats` | GET | 获取分类缓存统计信息 |
| `/cache/api/clear/all` | POST | 清除所有缓存 |
| `/cache/api/clear/instance` | POST | 清除实例缓存 |
| `/cache/api/clear/user` | POST | 清除用户缓存 |
| `/cache/api/stats` | GET | 获取缓存统计信息 |

### 21. 日志模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/history/logs/api/detail/<int:log_id>` | GET | 获取日志详情API |
| `/history/logs/api/list` | GET | Grid.js 日志列表API |
| `/history/logs/api/modules` | GET | 获取日志模块列表API |
| `/history/logs/api/search` | GET | 搜索日志API |
| `/history/logs/api/statistics` | GET | 获取日志统计信息API |

### 22. 分区管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/partition/api/aggregations/core-metrics` | GET | 获取核心聚合指标数据 |
| `/partition/api/cleanup` | POST | 清理旧分区 |
| `/partition/api/create` | POST | 创建分区任务 |
| `/partition/api/info` | GET | 获取分区信息API |
| `/partition/api/partitions` | GET | 分页返回分区列表,供 Grid.js 使用 |
| `/partition/api/statistics` | GET | 获取分区统计信息 |
| `/partition/api/status` | GET | 获取分区管理状态 |

### 23. 定时任务模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/scheduler/api/jobs` | GET | 获取所有定时任务 |
| `/scheduler/api/jobs/<job_id>` | GET | 获取指定任务详情 |
| `/scheduler/api/jobs/<job_id>` | PUT | 更新定时任务 |
| `/scheduler/api/jobs/<job_id>/pause` | POST | 暂停任务 |
| `/scheduler/api/jobs/<job_id>/resume` | POST | 恢复任务 |
| `/scheduler/api/jobs/<job_id>/run` | POST | 立即执行任务 |
| `/scheduler/api/jobs/reload` | POST | 重新加载所有任务配置 |

### 24. 同步会话模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/history/sessions/api/sessions` | GET | 获取同步会话列表API |
| `/history/sessions/api/sessions/<session_id>` | GET | 获取同步会话详情API |
| `/history/sessions/api/sessions/<session_id>/cancel` | POST | 取消同步会话API |
| `/history/sessions/api/sessions/<session_id>/error-logs` | GET | 获取同步会话错误日志API |

### 25. 标签管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/tags/api/<int:tag_id>` | GET | 根据 ID 获取标签详情 |
| `/tags/api/batch_delete` | POST | 批量删除标签API,返回每个标签的处理结果 |
| `/tags/api/categories` | GET | 获取标签分类列表API |
| `/tags/api/create` | POST | 创建标签API |
| `/tags/api/delete/<int:tag_id>` | POST | 删除标签 |
| `/tags/api/edit/<int:tag_id>` | POST | 编辑标签API |
| `/tags/api/list` | GET | Grid.js 标签列表API |
| `/tags/api/tags` | GET | 获取标签列表API |
| `/tags/api/tags/<tag_name>` | GET | 获取标签详情API |

### 26. 标签批量操作模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/tags/bulk/api/assign` | POST | 批量分配标签给实例 |
| `/tags/bulk/api/instance-tags` | POST | 获取实例的已关联标签API |
| `/tags/bulk/api/instances` | GET | 获取所有实例列表API |
| `/tags/bulk/api/remove` | POST | 批量移除实例的标签 |
| `/tags/bulk/api/remove-all` | POST | 批量移除实例的所有标签 |
| `/tags/bulk/api/tags` | GET | 获取所有标签列表API(包括非活跃标签) |

### 27. 用户管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/users/api/users` | GET | 获取用户列表API |
| `/users/api/users` | POST | 创建用户API |
| `/users/api/users/<int:user_id>` | DELETE | 删除用户API |
| `/users/api/users/<int:user_id>` | GET | 获取单个用户信息API |
| `/users/api/users/<int:user_id>` | PUT | 更新用户API |
| `/users/api/users/stats` | GET | 获取用户统计信息API |

### 28. 文件导入导出模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/files/api/account-export` | GET | 导出账户数据为 CSV |
| `/files/api/database-ledger-export` | GET | 导出数据库台账列表为 CSV |
| `/files/api/instance-export` | GET | 导出实例数据为 CSV |
| `/files/api/log-export` | GET | 导出日志API |
| `/files/api/template-download` | GET | 下载实例批量导入模板 |

### 29. 主路由模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/admin/api/app-info` | GET | 获取应用信息(供前端展示应用名称等) |
