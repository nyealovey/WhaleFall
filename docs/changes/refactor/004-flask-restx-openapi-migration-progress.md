# Flask-RESTX OpenAPI API 全量迁移进度

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-26
> 更新: 2025-12-26
> 范围: 同 `004-flask-restx-openapi-migration-plan.md`
> 关联: `004-flask-restx-openapi-migration-plan.md`

关联方案: `004-flask-restx-openapi-migration-plan.md`

---

## 1. 当前状态(摘要)

- 未开始. 先完成 Phase 0 的最小闭环, 再按域推进迁移.

## 2. Checklist

### Phase 0: 基础设施与最小闭环

- [ ] 新增 `app/api/**` 目录与 `/api/v1` blueprint
- [ ] RestX `Api` 基础配置与 docs/spec 路由
- [ ] envelope/error 的 RestX Model
- [ ] OpenAPI 导出脚本与最小校验

### Phase 1: 低风险域验证

- [ ] 迁移 health 或只读域到 RestX Resource
- [ ] 增加最小 HTTP 契约测试(200/4xx)

### Phase 2: 核心业务域迁移

- [ ] instances
- [ ] tags
- [ ] credentials
- [ ] accounts

### Phase 3: 全量覆盖与文档完善

- [ ] 覆盖所有 `/api` 端点到 RestX(见 Phase 3.1 清单)
- [ ] 补齐关键 model 的 description/example
- [ ] 增加"认证/CSRF 使用说明"文档入口

#### Phase 3.1: `/api` 端点清单(追踪用)

> 口径: 路径包含 `/api` 的 JSON API 端点.
> 清单来源: `docs/reference/api/api-routes-documentation.md` 的 "API 接口" 路由索引.
> 去重规则: 以 `METHOD + Path` 去重(总计: 131).
> 如需 handler/源文件追踪, 请以路由索引文档为准.

##### 1. 认证模块

- [ ] `POST /auth/api/change-password` - 修改密码API
- [ ] `GET /auth/api/csrf-token` - 获取CSRF令牌
- [ ] `POST /auth/api/login` - 用户登录API
- [ ] `POST /auth/api/logout` - 用户登出
- [ ] `GET /auth/api/me` - 获取当前用户信息
- [ ] `POST /auth/api/refresh` - 刷新JWT token

##### 2. 账户管理模块

- [ ] `GET /accounts/api/ledgers` - Grid.js 账户列表API
- [ ] `GET /accounts/api/ledgers/<int:account_id>/permissions` - 获取账户权限详情

##### 3. 账户统计模块

- [ ] `GET /accounts/api/statistics` - 账户统计API
- [ ] `GET /accounts/api/statistics/classifications` - 按分类统计
- [ ] `GET /accounts/api/statistics/db-types` - 按数据库类型统计
- [ ] `GET /accounts/api/statistics/summary` - 账户统计汇总

##### 4. 账户分类模块

- [ ] `GET /accounts/classifications/api/assignments` - 获取账户分类分配列表
- [ ] `DELETE /accounts/classifications/api/assignments/<int:assignment_id>` - 移除账户分类分配
- [ ] `POST /accounts/classifications/api/auto-classify` - 自动分类账户 - 使用优化后的服务
- [ ] `GET /accounts/classifications/api/classifications` - 获取所有账户分类
- [ ] `POST /accounts/classifications/api/classifications` - 创建账户分类
- [ ] `DELETE /accounts/classifications/api/classifications/<int:classification_id>` - 删除账户分类
- [ ] `GET /accounts/classifications/api/classifications/<int:classification_id>` - 获取单个账户分类
- [ ] `PUT /accounts/classifications/api/classifications/<int:classification_id>` - 更新账户分类
- [ ] `GET /accounts/classifications/api/colors` - 获取可用颜色选项
- [ ] `GET /accounts/classifications/api/permissions/<db_type>` - 获取数据库权限列表
- [ ] `GET /accounts/classifications/api/rules` - 获取所有规则列表(按数据库类型分组)
- [ ] `POST /accounts/classifications/api/rules` - 创建分类规则
- [ ] `DELETE /accounts/classifications/api/rules/<int:rule_id>` - 删除分类规则
- [ ] `GET /accounts/classifications/api/rules/<int:rule_id>` - 获取单个规则详情
- [ ] `PUT /accounts/classifications/api/rules/<int:rule_id>` - 更新分类规则
- [ ] `GET /accounts/classifications/api/rules/filter` - 获取分类规则
- [ ] `GET /accounts/classifications/api/rules/stats` - 获取规则命中统计

##### 5. 账户同步模块

- [ ] `POST /accounts/sync/api/instances/<int:instance_id>/sync` - 同步指定实例的账户信息,统一返回 JSON
- [ ] `POST /accounts/sync/api/sync-all` - 触发后台批量同步所有实例的账户信息

##### 6. 容量聚合模块

- [ ] `POST /capacity/api/aggregations/current` - 手动触发当前周期数据聚合

##### 7. 数据库容量同步模块

- [ ] `POST /databases/api/instances/<int:instance_id>/sync-capacity` - 同步指定实例的容量信息

##### 8. 数据库台账模块

- [ ] `GET /databases/api/ledgers` - 获取数据库台账列表数据
- [ ] `GET /databases/api/ledgers/<int:database_id>/capacity-trend` - 获取单个数据库的容量走势

##### 9. 通用数据模块

- [ ] `GET /common/api/databases-options` - 获取指定实例的数据库下拉选项(通用)
- [ ] `GET /common/api/dbtypes-options` - 获取数据库类型选项(通用)
- [ ] `GET /common/api/instances-options` - 获取实例下拉选项(通用)

##### 10. 连接管理模块

- [ ] `POST /connections/api/batch-test` - 批量测试连接
- [ ] `GET /connections/api/status/<int:instance_id>` - 获取实例连接状态
- [ ] `POST /connections/api/test` - 测试数据库连接API
- [ ] `POST /connections/api/validate-params` - 验证连接参数

##### 11. 凭据管理模块

- [ ] `POST /credentials/api/<int:credential_id>/edit` - 编辑凭据API
- [ ] `POST /credentials/api/create` - 创建凭据API
- [ ] `GET /credentials/api/credentials` - 获取凭据列表API
- [ ] `POST /credentials/api/credentials` - RESTful 创建凭据API,供前端 CredentialsService 使用
- [ ] `GET /credentials/api/credentials/<int:credential_id>` - 获取凭据详情API
- [ ] `PUT /credentials/api/credentials/<int:credential_id>` - RESTful 更新凭据API
- [ ] `POST /credentials/api/credentials/<int:credential_id>/delete` - 删除凭据

##### 12. 仪表板模块

- [ ] `GET /dashboard/api/activities` - 获取最近活动API (已废弃)
- [ ] `GET /dashboard/api/charts` - 获取仪表板图表数据
- [ ] `GET /dashboard/api/overview` - 获取系统概览API
- [ ] `GET /dashboard/api/status` - 获取系统状态API

##### 13. 数据库聚合页面模块

- [ ] `GET /capacity/api/databases` - 获取数据库统计聚合数据(数据库统计层面)
- [ ] `GET /capacity/api/databases/summary` - 获取数据库统计聚合汇总信息

##### 14. 实例详情扩展模块

- [ ] `GET /instances/api/<int:instance_id>/accounts/<int:account_id>/change-history` - 获取账户变更历史
- [ ] `GET /instances/api/<int:instance_id>/accounts/<int:account_id>/permissions` - 获取账户权限详情
- [ ] `POST /instances/api/<int:instance_id>/edit` - 编辑实例API
- [ ] `GET /instances/api/databases/<int:instance_id>/sizes` - 获取指定实例的数据库大小数据(最新或历史)

##### 15. 实例聚合模块

- [ ] `GET /capacity/api/instances` - 获取实例聚合数据(实例统计层面)
- [ ] `GET /capacity/api/instances/summary` - 获取实例聚合汇总信息(实例统计层面)

##### 16. 实例管理模块

- [ ] `GET /instances/api/<int:instance_id>` - 获取实例详情API
- [ ] `GET /instances/api/<int:instance_id>/accounts` - 获取实例账户数据API
- [ ] `POST /instances/api/<int:instance_id>/delete` - 删除实例
- [ ] `POST /instances/api/<int:instance_id>/restore` - 恢复实例
- [ ] `POST /instances/api/create` - 创建实例API
- [ ] `GET /instances/api/instances` - Grid.js 实例列表API

##### 17. 实例批量操作模块

- [ ] `POST /instances/batch/api/create` - 批量创建实例
- [ ] `POST /instances/batch/api/delete` - 批量删除实例

##### 18. 实例统计模块

- [ ] `GET /instances/api/statistics` - 获取实例统计API

##### 19. 健康检查模块

- [ ] `GET /health/api/basic` - 基础健康检查
- [ ] `GET /health/api/cache` - 缓存服务健康检查
- [ ] `GET /health/api/detailed` - 详细健康检查
- [ ] `GET /health/api/health` - 健康检查(供外部监控使用)

##### 20. 缓存管理模块

- [ ] `POST /cache/api/classification/clear` - 清除分类相关缓存
- [ ] `POST /cache/api/classification/clear/<db_type>` - 清除特定数据库类型的缓存
- [ ] `GET /cache/api/classification/stats` - 获取分类缓存统计信息
- [ ] `POST /cache/api/clear/all` - 清除所有缓存
- [ ] `POST /cache/api/clear/instance` - 清除实例缓存
- [ ] `POST /cache/api/clear/user` - 清除用户缓存
- [ ] `GET /cache/api/stats` - 获取缓存统计信息

##### 21. 日志模块

- [ ] `GET /history/logs/api/detail/<int:log_id>` - 获取日志详情API
- [ ] `GET /history/logs/api/list` - Grid.js 日志列表API
- [ ] `GET /history/logs/api/modules` - 获取日志模块列表API
- [ ] `GET /history/logs/api/search` - 搜索日志API
- [ ] `GET /history/logs/api/statistics` - 获取日志统计信息API

##### 22. 分区管理模块

- [ ] `GET /partition/api/aggregations/core-metrics` - 获取核心聚合指标数据
- [ ] `POST /partition/api/cleanup` - 清理旧分区
- [ ] `POST /partition/api/create` - 创建分区任务
- [ ] `GET /partition/api/info` - 获取分区信息API
- [ ] `GET /partition/api/partitions` - 分页返回分区列表,供 Grid.js 使用
- [ ] `GET /partition/api/statistics` - 获取分区统计信息
- [ ] `GET /partition/api/status` - 获取分区管理状态

##### 23. 定时任务模块

- [ ] `GET /scheduler/api/jobs` - 获取所有定时任务
- [ ] `GET /scheduler/api/jobs/<job_id>` - 获取指定任务详情
- [ ] `PUT /scheduler/api/jobs/<job_id>` - 更新定时任务
- [ ] `POST /scheduler/api/jobs/<job_id>/pause` - 暂停任务
- [ ] `POST /scheduler/api/jobs/<job_id>/resume` - 恢复任务
- [ ] `POST /scheduler/api/jobs/<job_id>/run` - 立即执行任务
- [ ] `POST /scheduler/api/jobs/reload` - 重新加载所有任务配置

##### 24. 同步会话模块

- [ ] `GET /history/sessions/api/sessions` - 获取同步会话列表API
- [ ] `GET /history/sessions/api/sessions/<session_id>` - 获取同步会话详情API
- [ ] `POST /history/sessions/api/sessions/<session_id>/cancel` - 取消同步会话API
- [ ] `GET /history/sessions/api/sessions/<session_id>/error-logs` - 获取同步会话错误日志API

##### 25. 标签管理模块

- [ ] `GET /tags/api/<int:tag_id>` - 根据 ID 获取标签详情
- [ ] `POST /tags/api/batch_delete` - 批量删除标签API,返回每个标签的处理结果
- [ ] `GET /tags/api/categories` - 获取标签分类列表API
- [ ] `POST /tags/api/create` - 创建标签API
- [ ] `POST /tags/api/delete/<int:tag_id>` - 删除标签
- [ ] `POST /tags/api/edit/<int:tag_id>` - 编辑标签API
- [ ] `GET /tags/api/list` - Grid.js 标签列表API
- [ ] `GET /tags/api/tags` - 获取标签列表API
- [ ] `GET /tags/api/tags/<tag_name>` - 获取标签详情API

##### 26. 标签批量操作模块

- [ ] `POST /tags/bulk/api/assign` - 批量分配标签给实例
- [ ] `POST /tags/bulk/api/instance-tags` - 获取实例的已关联标签API
- [ ] `GET /tags/bulk/api/instances` - 获取所有实例列表API
- [ ] `POST /tags/bulk/api/remove` - 批量移除实例的标签
- [ ] `POST /tags/bulk/api/remove-all` - 批量移除实例的所有标签
- [ ] `GET /tags/bulk/api/tags` - 获取所有标签列表API(包括非活跃标签)

##### 27. 用户管理模块

- [ ] `GET /users/api/users` - 获取用户列表API
- [ ] `POST /users/api/users` - 创建用户API
- [ ] `DELETE /users/api/users/<int:user_id>` - 删除用户API
- [ ] `GET /users/api/users/<int:user_id>` - 获取单个用户信息API
- [ ] `PUT /users/api/users/<int:user_id>` - 更新用户API
- [ ] `GET /users/api/users/stats` - 获取用户统计信息API

##### 28. 文件导入导出模块

- [ ] `GET /files/api/account-export` - 导出账户数据为 CSV
- [ ] `GET /files/api/database-ledger-export` - 导出数据库台账列表为 CSV
- [ ] `GET /files/api/instance-export` - 导出实例数据为 CSV
- [ ] `GET /files/api/log-export` - 导出日志API
- [ ] `GET /files/api/template-download` - 下载实例批量导入模板

##### 29. 主路由模块

- [ ] `GET /admin/api/app-info` - 获取应用信息(供前端展示应用名称等)

### Phase 4: 下线旧 API 与清理

- [ ] 移除旧 `*/api/*` 路由实现或按策略返回 410/301
- [ ] 移除迁移期兼容分支与 feature flag

## 3. 变更记录(按日期追加)

- 2025-12-26: 创建 plan/progress 文档, 待开始实施.
