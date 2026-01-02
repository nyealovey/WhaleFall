# Flask-RESTX OpenAPI API 全量迁移进度

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-26
> 更新: 2025-12-28
> 范围: 同 `004-flask-restx-openapi-migration-plan.md`
> 关联: `004-flask-restx-openapi-migration-plan.md`

关联方案: `004-flask-restx-openapi-migration-plan.md`

---

## 1. 当前状态(摘要)

- Phase 0 已完成: `/api/v1` blueprint + RestX docs/spec + envelope/error Model + OpenAPI 导出脚本.
- Phase 1 已完成: health 最小只读端点样板 + 最小 HTTP 契约测试(200/4xx).
- Phase 2 已完成: instances/tags/credentials/accounts(ledgers) 已提供 API v1 入口与最小契约测试.
- Phase 3 已完成: 清单内所有 `/api` 端点均已迁移到 `/api/v1/**` 并补齐最小契约测试, 补齐关键 model 的 description/example, 并增加认证/CSRF 使用说明文档入口.
- Phase 4 已完成(强下线): legacy `*/api/*` handler 已从 `app/routes/**` 清理, 前端/模板切换到 `/api/v1/**`, 并移除 `API_V1_ENABLED` 开关(`/api/v1` 始终启用); 旧路径不再提供路由(404).

## 2. Checklist

### Phase 0: 基础设施与最小闭环

- [x] 新增 `app/api/**` 目录与 `/api/v1` blueprint
- [x] RestX `Api` 基础配置与 docs/spec 路由
- [x] envelope/error 的 RestX Model
- [x] OpenAPI 导出脚本与最小校验

### Phase 1: 低风险域验证

- [x] 迁移 health 或只读域到 RestX Resource
- [x] 增加最小 HTTP 契约测试(200/4xx)

### Phase 2: 核心业务域迁移

- [x] instances(只读: list/detail)
- [x] tags(只读: list/options/categories/detail)
- [x] credentials(只读: list/detail)
- [x] accounts(只读: ledgers list/permissions)

### Phase 3: 全量覆盖与文档完善

- [x] 覆盖所有 `/api` 端点到 RestX(见 Phase 3.1 清单)
- [x] 补齐关键 model 的 description/example
- [x] 增加"认证/CSRF 使用说明"文档入口

### Phase 4: 强下线与切换

- [x] 移除旧 `*/api/*` 路由实现（旧路径不再提供路由/404）
- [x] 前端静态资源与模板统一切换到 `/api/v1/**`（含导出/模板下载）
- [x] 移除 `API_V1_ENABLED`（避免旧 API 下线后出现“API 全不可用”的配置组合）

#### Phase 3.1: `/api` 端点清单(追踪用)

> 口径: 路径包含 `/api` 的 JSON API 端点.
> 清单来源: `docs/reference/api/api-routes-documentation.md` 的 "API 接口" 路由索引.
> 去重规则: 以 `METHOD + Path` 去重(总计以生成清单统计为准).
> 如需 handler/源文件追踪, 请以路由索引文档为准.
> 生成清单: `docs/changes/refactor/artifacts/004-phase3-api-routes.md`
> 说明: 生成/校验脚本已在迁移清理中移除, 清单作为历史产物保留.

列说明(最小口径):

- `状态`: TODO / DOING / DONE
- `RestX`/`OpenAPI`/`测试`: TODO / DONE / N/A

##### 1. 认证模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /auth/api/change-password` | 修改密码API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/auth/change-password` |
| `GET /auth/api/csrf-token` | 获取CSRF令牌 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/auth/csrf-token` |
| `POST /auth/api/login` | 用户登录API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/auth/login` |
| `POST /auth/api/logout` | 用户登出 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/auth/logout` |
| `GET /auth/api/me` | 获取当前用户信息 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/auth/me` |
| `POST /auth/api/refresh` | 刷新JWT token | DONE | DONE | DONE | DONE | 新入口: `/api/v1/auth/refresh` |

##### 2. 账户管理模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /accounts/api/ledgers` | Grid.js 账户列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/ledgers` |
| `GET /accounts/api/ledgers/<int:account_id>/permissions` | 获取账户权限详情 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/ledgers/<id>/permissions` |

##### 3. 账户统计模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /accounts/api/statistics` | 账户统计API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/statistics` |
| `GET /accounts/api/statistics/classifications` | 按分类统计 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/statistics/classifications` |
| `GET /accounts/api/statistics/db-types` | 按数据库类型统计 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/statistics/db-types` |
| `GET /accounts/api/statistics/summary` | 账户统计汇总 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/statistics/summary` |

##### 4. 账户分类模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /accounts/classifications/api/assignments` | 获取账户分类分配列表 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/assignments` |
| `DELETE /accounts/classifications/api/assignments/<int:assignment_id>` | 移除账户分类分配 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/assignments/<id>` |
| `POST /accounts/classifications/api/auto-classify` | 自动分类账户 - 使用优化后的服务 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/actions/auto-classify` |
| `GET /accounts/classifications/api/classifications` | 获取所有账户分类 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications` |
| `POST /accounts/classifications/api/classifications` | 创建账户分类 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications` |
| `DELETE /accounts/classifications/api/classifications/<int:classification_id>` | 删除账户分类 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/<id>` |
| `GET /accounts/classifications/api/classifications/<int:classification_id>` | 获取单个账户分类 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/<id>` |
| `PUT /accounts/classifications/api/classifications/<int:classification_id>` | 更新账户分类 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/<id>` |
| `GET /accounts/classifications/api/colors` | 获取可用颜色选项 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/colors` |
| `GET /accounts/classifications/api/permissions/<db_type>` | 获取数据库权限列表 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/permissions/<db_type>` |
| `GET /accounts/classifications/api/rules` | 获取所有规则列表(按数据库类型分组) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/rules` |
| `POST /accounts/classifications/api/rules` | 创建分类规则 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/rules` |
| `DELETE /accounts/classifications/api/rules/<int:rule_id>` | 删除分类规则 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/rules/<id>` |
| `GET /accounts/classifications/api/rules/<int:rule_id>` | 获取单个规则详情 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/rules/<id>` |
| `PUT /accounts/classifications/api/rules/<int:rule_id>` | 更新分类规则 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/rules/<id>` |
| `GET /accounts/classifications/api/rules/filter` | 获取分类规则 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/rules/filter` |
| `GET /accounts/classifications/api/rules/stats` | 获取规则命中统计 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/classifications/rules/stats` |

##### 5. 账户同步模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /accounts/sync/api/instances/<int:instance_id>/sync` | 同步指定实例的账户信息,统一返回 JSON | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/actions/sync` (body: instance_id) |
| `POST /accounts/sync/api/sync-all` | 触发后台批量同步所有实例的账户信息 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/accounts/actions/sync-all` |

##### 6. 容量聚合模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /capacity/api/aggregations/current` | 手动触发当前周期数据聚合 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/capacity/aggregations/current` |

##### 7. 数据库容量同步模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /databases/api/instances/<int:instance_id>/sync-capacity` | 同步指定实例的容量信息 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>/actions/sync-capacity` |

##### 8. 数据库台账模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /databases/api/ledgers` | 获取数据库台账列表数据 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/databases/ledgers` |
| `GET /databases/api/ledgers/<int:database_id>/capacity-trend` | 获取单个数据库的容量走势 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/databases/ledgers/<id>/capacity-trend` |

##### 9. 通用数据模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /common/api/databases-options` | 获取指定实例的数据库下拉选项(通用) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/common/databases/options` |
| `GET /common/api/dbtypes-options` | 获取数据库类型选项(通用) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/common/database-types/options` |
| `GET /common/api/instances-options` | 获取实例下拉选项(通用) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/common/instances/options` |

##### 10. 连接管理模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /connections/api/batch-test` | 批量测试连接 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/connections/actions/batch-test` |
| `GET /connections/api/status/<int:instance_id>` | 获取实例连接状态 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/connections/status/<id>` |
| `POST /connections/api/test` | 测试数据库连接API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/connections/actions/test` |
| `POST /connections/api/validate-params` | 验证连接参数 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/connections/actions/validate-params` |

##### 11. 凭据管理模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /credentials/api/<int:credential_id>/edit` | 编辑凭据API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/credentials/<id>` (PUT) |
| `POST /credentials/api/create` | 创建凭据API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/credentials` |
| `GET /credentials/api/credentials` | 获取凭据列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/credentials` |
| `POST /credentials/api/credentials` | RESTful 创建凭据API,供前端 CredentialsService 使用 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/credentials` |
| `GET /credentials/api/credentials/<int:credential_id>` | 获取凭据详情API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/credentials/<id>` |
| `PUT /credentials/api/credentials/<int:credential_id>` | RESTful 更新凭据API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/credentials/<id>` |
| `POST /credentials/api/credentials/<int:credential_id>/delete` | 删除凭据 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/credentials/<id>/delete` |

##### 12. 仪表板模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /dashboard/api/activities` | 获取最近活动API (已废弃) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/dashboard/activities` |
| `GET /dashboard/api/charts` | 获取仪表板图表数据 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/dashboard/charts` |
| `GET /dashboard/api/overview` | 获取系统概览API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/dashboard/overview` |
| `GET /dashboard/api/status` | 获取系统状态API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/dashboard/status` |

##### 13. 数据库聚合页面模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /capacity/api/databases` | 获取数据库统计聚合数据(数据库统计层面) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/capacity/databases` |
| `GET /capacity/api/databases/summary` | 获取数据库统计聚合汇总信息 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/capacity/databases/summary` |

##### 14. 实例详情扩展模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /instances/api/<int:instance_id>/accounts/<int:account_id>/change-history` | 获取账户变更历史 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>/accounts/<account_id>/change-history` |
| `GET /instances/api/<int:instance_id>/accounts/<int:account_id>/permissions` | 获取账户权限详情 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>/accounts/<account_id>/permissions` |
| `POST /instances/api/<int:instance_id>/edit` | 编辑实例API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>` (PUT) |
| `GET /instances/api/databases/<int:instance_id>/sizes` | 获取指定实例的数据库大小数据(最新或历史) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>/databases/sizes` |

##### 15. 实例聚合模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /capacity/api/instances` | 获取实例聚合数据(实例统计层面) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/capacity/instances` |
| `GET /capacity/api/instances/summary` | 获取实例聚合汇总信息(实例统计层面) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/capacity/instances/summary` |

##### 16. 实例管理模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /instances/api/<int:instance_id>` | 获取实例详情API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>` |
| `GET /instances/api/<int:instance_id>/accounts` | 获取实例账户数据API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>/accounts` |
| `POST /instances/api/<int:instance_id>/delete` | 删除实例 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>/delete` |
| `POST /instances/api/<int:instance_id>/restore` | 恢复实例 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/<id>/restore` |
| `POST /instances/api/create` | 创建实例API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances` |
| `GET /instances/api/instances` | Grid.js 实例列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances` |

##### 17. 实例批量操作模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /instances/batch/api/create` | 批量创建实例 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/batch-create` |
| `POST /instances/batch/api/delete` | 批量删除实例 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/batch-delete` |

##### 18. 实例统计模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /instances/api/statistics` | 获取实例统计API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/instances/statistics` |

##### 19. 健康检查模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /health/api/basic` | 基础健康检查 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/health/basic` |
| `GET /health/api/cache` | 缓存服务健康检查 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/health/cache` |
| `GET /health/api/detailed` | 详细健康检查 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/health/detailed` |
| `GET /health/api/health` | 健康检查(供外部监控使用) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/health/health` |

##### 20. 缓存管理模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /cache/api/classification/clear` | 清除分类相关缓存 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/cache/classification/clear` |
| `POST /cache/api/classification/clear/<db_type>` | 清除特定数据库类型的缓存 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/cache/classification/clear/<db_type>` |
| `GET /cache/api/classification/stats` | 获取分类缓存统计信息 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/cache/classification/stats` |
| `POST /cache/api/clear/all` | 清除所有缓存 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/cache/clear/all` |
| `POST /cache/api/clear/instance` | 清除实例缓存 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/cache/clear/instance` |
| `POST /cache/api/clear/user` | 清除用户缓存 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/cache/clear/user` |
| `GET /cache/api/stats` | 获取缓存统计信息 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/cache/stats` |

##### 21. 日志模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /history/logs/api/detail/<int:log_id>` | 获取日志详情API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/logs/detail/<int:log_id>` |
| `GET /history/logs/api/list` | Grid.js 日志列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/logs/list` |
| `GET /history/logs/api/modules` | 获取日志模块列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/logs/modules` |
| `GET /history/logs/api/search` | 搜索日志API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/logs/search` |
| `GET /history/logs/api/statistics` | 获取日志统计信息API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/logs/statistics` |

##### 22. 分区管理模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /partition/api/aggregations/core-metrics` | 获取核心聚合指标数据 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/partition/aggregations/core-metrics` |
| `POST /partition/api/cleanup` | 清理旧分区 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/partition/cleanup` |
| `POST /partition/api/create` | 创建分区任务 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/partition/create` |
| `GET /partition/api/info` | 获取分区信息API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/partition/info` |
| `GET /partition/api/partitions` | 分页返回分区列表,供 Grid.js 使用 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/partition/partitions` |
| `GET /partition/api/statistics` | 获取分区统计信息 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/partition/statistics` |
| `GET /partition/api/status` | 获取分区管理状态 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/partition/status` |

##### 23. 定时任务模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /scheduler/api/jobs` | 获取所有定时任务 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/scheduler/jobs` |
| `GET /scheduler/api/jobs/<job_id>` | 获取指定任务详情 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/scheduler/jobs/<job_id>` |
| `PUT /scheduler/api/jobs/<job_id>` | 更新定时任务 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/scheduler/jobs/<job_id>` |
| `POST /scheduler/api/jobs/<job_id>/pause` | 暂停任务 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/scheduler/jobs/<job_id>/pause` |
| `POST /scheduler/api/jobs/<job_id>/resume` | 恢复任务 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/scheduler/jobs/<job_id>/resume` |
| `POST /scheduler/api/jobs/<job_id>/run` | 立即执行任务 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/scheduler/jobs/<job_id>/run` |
| `POST /scheduler/api/jobs/reload` | 重新加载所有任务配置 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/scheduler/jobs/reload` |

##### 24. 同步会话模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /history/sessions/api/sessions` | 获取同步会话列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/sessions` |
| `GET /history/sessions/api/sessions/<session_id>` | 获取同步会话详情API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/sessions/<session_id>` |
| `POST /history/sessions/api/sessions/<session_id>/cancel` | 取消同步会话API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/sessions/<session_id>/cancel` |
| `GET /history/sessions/api/sessions/<session_id>/error-logs` | 获取同步会话错误日志API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/history/sessions/<session_id>/error-logs` |

##### 25. 标签管理模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /tags/api/<int:tag_id>` | 根据 ID 获取标签详情 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/<id>` |
| `POST /tags/api/batch_delete` | 批量删除标签API,返回每个标签的处理结果 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/batch-delete` |
| `GET /tags/api/categories` | 获取标签分类列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/categories` |
| `POST /tags/api/create` | 创建标签API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags` |
| `POST /tags/api/delete/<int:tag_id>` | 删除标签 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/<id>/delete` |
| `POST /tags/api/edit/<int:tag_id>` | 编辑标签API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/<id>` (PUT) |
| `GET /tags/api/list` | Grid.js 标签列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags` |
| `GET /tags/api/tags` | 获取标签列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/options` |
| `GET /tags/api/tags/<tag_name>` | 获取标签详情API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/by-name/<tag_name>` |

##### 26. 标签批量操作模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `POST /tags/bulk/api/assign` | 批量分配标签给实例 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/bulk/assign` |
| `POST /tags/bulk/api/instance-tags` | 获取实例的已关联标签API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/bulk/instance-tags` |
| `GET /tags/bulk/api/instances` | 获取所有实例列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/bulk/instances` |
| `POST /tags/bulk/api/remove` | 批量移除实例的标签 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/bulk/remove` |
| `POST /tags/bulk/api/remove-all` | 批量移除实例的所有标签 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/bulk/remove-all` |
| `GET /tags/bulk/api/tags` | 获取所有标签列表API(包括非活跃标签) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/tags/bulk/tags` |

##### 27. 用户管理模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /users/api/users` | 获取用户列表API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/users` |
| `POST /users/api/users` | 创建用户API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/users` |
| `DELETE /users/api/users/<int:user_id>` | 删除用户API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/users/<id>` |
| `GET /users/api/users/<int:user_id>` | 获取单个用户信息API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/users/<id>` |
| `PUT /users/api/users/<int:user_id>` | 更新用户API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/users/<id>` |
| `GET /users/api/users/stats` | 获取用户统计信息API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/users/stats` |

##### 28. 文件导入导出模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /files/api/account-export` | 导出账户数据为 CSV | DONE | DONE | DONE | DONE | 新入口: `/api/v1/files/account-export` |
| `GET /files/api/database-ledger-export` | 导出数据库台账列表为 CSV | DONE | DONE | DONE | DONE | 新入口: `/api/v1/files/database-ledger-export` |
| `GET /files/api/instance-export` | 导出实例数据为 CSV | DONE | DONE | DONE | DONE | 新入口: `/api/v1/files/instance-export` |
| `GET /files/api/log-export` | 导出日志API | DONE | DONE | DONE | DONE | 新入口: `/api/v1/files/log-export` |
| `GET /files/api/template-download` | 下载实例批量导入模板 | DONE | DONE | DONE | DONE | 新入口: `/api/v1/files/template-download` |

##### 29. 主路由模块

| Endpoint | 描述 | 状态 | RestX | OpenAPI | 测试 | 备注 |
|---|---|---|---|---|---|---|
| `GET /admin/api/app-info` | 获取应用信息(供前端展示应用名称等) | DONE | DONE | DONE | DONE | 新入口: `/api/v1/admin/app-info` |

### Phase 4: 下线旧 API 与清理

- [x] 移除旧 `*/api/*` 路由实现（旧路径不再提供路由/404，保留页面路由）
- [x] 移除迁移期兼容分支与 feature flag

## 3. 变更记录(按日期追加)

- 2025-12-26: 创建 plan/progress 文档, 待开始实施.
- 2025-12-27: Phase 1 health 完成; Phase 2 核心域只读端点新增 `/api/v1` 入口并补齐最小契约测试.
- 2025-12-27: Phase 3 清单全量覆盖完成(用户/文件导出/主路由 app-info)并补齐最小契约测试.
- 2025-12-28: 移除 `app/routes/**` 下 legacy `*/api/*` 路由实现, 仅保留页面路由; `auth.logout` 调整为 `/auth/logout`.
- 2025-12-28: Phase 3 补齐关键 model 的 description/example, 并增加认证/CSRF 使用说明文档入口.
