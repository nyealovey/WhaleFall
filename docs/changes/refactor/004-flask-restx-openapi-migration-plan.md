# Flask-RESTX OpenAPI API 全量迁移方案

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-26
> 更新: 2025-12-26
> 范围: 后端 JSON API(路径包含 `/api` 的端点), 新增 `app/api/**`, 逐步替换 `app/routes/**` 下既有 API 路由实现
> 关联: `../../reference/api/api-routes-documentation.md`, `../../reference/api/flask-restx-integration.md`, `../../standards/backend/api-response-envelope.md`, `../../standards/backend/error-message-schema-unification.md`, `../../standards/backend/configuration-and-secrets.md`

---

## 1. 动机与范围

### 1.1 动机

- 当前项目已引入 `flask-restx`, 主要用于 `marshal/fields` 的输出序列化白名单, 但尚未启用 `Api/Namespace` 的 OpenAPI 能力.
- API 端点分散在 `app/routes/**` 的多个 Blueprint 内, 缺少可自动生成的契约与统一的对外文档入口.
- 变更时缺少可对比的 API schema, 容易出现"字段漂移/参数漂移/错误口径漂移", 需要前端做额外兜底解析.

### 1.2 范围

本计划的迁移目标是: 覆盖所有 JSON API 端点, 并产出可访问的 API 文档站点与 OpenAPI spec.

- 迁移对象: `docs/reference/api/api-routes-documentation.md` 中标记为 "API 接口" 的路由(路径包含 `/api`).
- 不在范围: 返回 HTML 的页面路由, 以及与 UI 模板渲染强耦合的 handler.

### 1.3 非目标

- 不在本计划内一次性重写业务编排(Service)或数据访问(Repository)层, 仅重构路由层的对外 API 形态与文档能力.
- 不强制一次性把所有端点改成"完美 RESTful 风格"(如把历史遗留的 `POST .../delete` 全部改为 `DELETE`), 该类语义收敛可在后续阶段单独推进.

## 2. 不变约束

- 响应封套不变: 所有 JSON 成功响应继续遵循 `jsonify_unified_success(...)`, 错误响应继续由统一错误处理器生成. 见 `../../standards/backend/api-response-envelope.md`.
- 错误字段口径不变: 禁止新增 `error/message` 互兜底链, 仅使用 canonical 字段. 见 `../../standards/backend/error-message-schema-unification.md`.
- 认证与权限不降级: `flask_login.login_required` 与既有权限装饰器语义保持不变.
- CSRF 口径不降级: 写操作的 CSRF 约束保持一致, 文档中需要明确获取与传递方式.
- 性能基线不退化: RestX 的序列化层不得触发隐式 IO 查询, 预加载策略必须在业务层显式完成.

## 3. 目标架构与目录结构

### 3.1 新增 `app/api/**` 目录

目标是把"对外 API"从"页面路由"中剥离, 形成独立的 API 模块, 并由 RestX 统一生成 OpenAPI.

建议目录结构:

```text
app/
  api/
    __init__.py          # 注册 api blueprint, 创建 Api, 挂载 docs/openapi 路由
    v1/
      __init__.py        # 注册各 Namespace
      namespaces/
        auth.py
        instances.py
        tags.py
      models/
        envelope.py      # success/error envelope 的 RestX Model 定义
        common.py
        instances.py
      resources/
        base.py          # BaseResource, 统一封套与 safe_route_call 适配
```

说明:

- `app/routes/**` 保留页面路由与历史 API(迁移期间), `app/api/**` 为新 API 的唯一入口.
- `v1/` 为版本化的第一版 API, 后续迭代通过新增 `v2/` 演进, 避免破坏性变更直接覆盖.

### 3.2 API 挂载与文档入口

建议采用 Blueprint 方式挂载 RestX:

- API base path: `/api/v1`
- Swagger UI: `/api/v1/docs` (或 `/api/docs`, 由配置决定)
- OpenAPI JSON: `/api/v1/openapi.json` (或兼容 `swagger.json`)

生产环境建议默认关闭"Try it out"或关闭 docs, 仅保留 OpenAPI JSON 给内部系统/CI 使用, 通过配置开关控制(见第 5 节).

## 4. OpenAPI 契约组织策略

### 4.1 复用既有 `fields` 定义

现状: 仓库已有大量 `*_restx_models.py` 的 `flask_restx.fields` 字段白名单定义, 已被路由通过 `marshal(...)` 使用.

迁移策略:

- 短期(迁移期)允许复用这些 `fields` dict, 在 Namespace 内通过 `ns.model("Name", fields_dict)` 注册为 OpenAPI 可识别的 Model.
- 中期逐步补齐字段描述(description), required, example 等信息, 提升文档可读性.
- 长期把 RestX Model 的定义统一收敛到 `app/api/v1/models/**`, 避免 routes 与 api 两处各自维护.

### 4.2 统一封套的文档建模

由于项目强制使用 JSON envelope, OpenAPI 需要显式表达封套结构:

- `SuccessEnvelope[T]`: `success/error/message/timestamp/data/meta`
- `ErrorEnvelope`: 对齐 `enhanced_error_handler` 输出字段

建议在 `app/api/v1/models/envelope.py` 提供可复用的 Model 构建器, 以 `T` 为 data model 的嵌套, 例如:

- `make_success_envelope_model(name, data_model)`
- `make_error_envelope_model()`

并在每个 Resource method 上通过 `@ns.response(..., model=...)` 固化成功与失败响应 schema.

### 4.3 输入参数与校验

- Query 参数: 使用 `@ns.param(...)` 明确 `page/page_size/sort/order` 等参数与取值范围.
- Body 参数: 使用 `@ns.expect(model, validate=True)` 表达 body schema, 并在业务层复用现有 `DataValidator` 做更严格的语义校验.
- 迁移期禁止把校验逻辑分散成两套(一套在 RestX, 一套在业务), RestX 仅用于"文档 + 基础类型校验", 业务校验仍以既有标准为准.

## 5. 兼容, 适配, 回退策略

### 5.1 URL 策略(推荐)

推荐使用"新旧并行"的迁移方式, 以降低前端与外部调用方的切换风险:

- 新 API: `/api/v1/**` (RestX Resource)
- 旧 API: 保留现有 `*/api/*` 路由实现, 直至前端与测试完成切换

切换窗口建议以"版本"或"时间"为界, 在公告/变更记录中明确.

### 5.2 兼容与去兼容(deprecation)

- 新旧并行期间, 旧 API 标记为 Deprecated:
  - 文档层面: 在 OpenAPI 中对旧路径加 `deprecated: true` 注记(若旧路径也纳入 spec).
  - 响应层面: 可选在 `meta` 中增加 `deprecated` 信息, 便于前端观测与日志统计.
- 如必须发生字段演进:
  - 优先"新增字段"保持向前兼容.
  - 如必须重命名, 允许在边界层做短期字段别名兼容(例如 `data.get("new") or data.get("old")`), 但必须写入清理计划并设定删除时间点.

### 5.3 回退策略

- 配置级回退: 新增 settings 开关控制是否注册 `app/api/**` 的 blueprint, 生产环境默认可关闭 docs.
- 代码级回退: 每个阶段按"可独立 revert"的 PR 粒度推进, 避免跨域大爆改导致无法回退.

配置项必须走 `app/settings.py` 统一解析与校验, 见 `../../standards/backend/configuration-and-secrets.md`.

## 6. 分阶段计划(每阶段验收口径)

### Phase 0: 基础设施与最小闭环

交付:

- 新增 `app/api/**` 目录与 `/api/v1` blueprint.
- RestX `Api` 基础配置(title, version, docs path, spec path).
- 统一错误处理与 envelope 文档 Model.
- 提供 OpenAPI 导出能力(命令或脚本), 用于 CI/本地生成 spec.

验收:

- 本地可访问 Swagger UI, 且可下载 OpenAPI JSON.
- 不影响现有 `app/routes/**` 的页面与 API 行为.

### Phase 1: 选择 1-2 个低风险域迁移验证

建议优先:

- `/health/api/*` 或只读类接口, 作为 RestX Resource 的样板.

验收:

- 新端点的 envelope 与错误口径与旧端点一致.
- 增加最小 HTTP 契约测试(至少覆盖 200/4xx), 并在 CI 命令中可跑.

### Phase 2: 核心业务域迁移

优先级建议:

1. instances
2. tags
3. credentials
4. accounts

验收:

- 旧端点与新端点数据一致性通过测试验证(允许输出字段有计划内差异, 但必须在变更文档中显式列出).
- 前端调用切换到 `/api/v1/**` 后, 关键页面可用.

### Phase 3: 全量覆盖与文档完善

交付:

- 覆盖所有 `/api` 端点到 RestX(见第 10 节清单).
- 补齐关键 model 的 description/example.
- 完善 API 文档站点入口, 增加"认证/CSRF 使用说明"页.

验收:

- 第 10 节清单内每个 path+method 均在 OpenAPI spec 中可见, 且 envelope/错误口径对齐.
- `docs/reference/api/api-routes-documentation.md` 更新为以 `app/api/**` 为真源, 或明确新旧并行期的索引口径.

### Phase 4: 下线旧 API 与清理

交付:

- 移除旧的 `*/api/*` 路由, 或将其改为明确的 410/301(按产品策略).
- 移除迁移期的兼容分支与 feature flag.

验收:

- 依赖旧 API 的前端代码与文档引用全部清理完毕.

## 7. 风险与回滚

主要风险:

- 路由冲突: 新旧端点路径冲突导致注册失败或行为覆盖.
- 认证与 CSRF: Swagger UI 交互调用不携带 cookie/CSRF 导致误判为 API 不可用.
- schema 漂移: RestX Model 与实际响应不一致, 文档失真.

回滚原则:

- 每阶段以"可 revert"为最小单元, 不合并跨阶段的大 PR.
- 若出现线上风险, 先通过配置关闭 `app/api` blueprint 或 docs, 再定位问题.

## 8. 验证与门禁

建议每个阶段至少跑以下命令:

- `make format`
- `make typecheck`
- `./scripts/ci/ruff-report.sh style`
- `pytest -m unit`

并增加 OpenAPI 相关门禁(建议):

- 生成 OpenAPI JSON 并做 schema 校验(例如基础字段存在, paths 非空).
- 如选择提交生成产物, 需要提供 drift guard, 防止 spec 与代码不一致.

## 9. 清理计划

- 完成 Phase 4 后删除:
  - 旧 `*/api/*` handler 与重复的序列化定义
  - 迁移期字段别名兼容(`or` 兜底)与临时适配层
  - 仅用于迁移的 feature flag 与脚本
- 最终收敛:
  - `app/routes/**` 仅承载页面路由
  - `app/api/**` 为对外 JSON API 的唯一入口与唯一文档真源

## 10. Phase 3: `/api` 端点全量清单(迁移范围)

> 口径: 路径包含 `/api` 的 JSON API 端点.
> 清单来源: `docs/reference/api/api-routes-documentation.md` 的 "API 接口" 路由索引.
> 去重规则: 以 `METHOD + Path` 去重(总计: 131).
> 如需 handler/源文件追踪, 请以路由索引文档为准.

### API 清单(按模块)

#### 1. 认证模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/auth/api/change-password` | POST | 修改密码API |
| `/auth/api/csrf-token` | GET | 获取CSRF令牌 |
| `/auth/api/login` | POST | 用户登录API |
| `/auth/api/logout` | POST | 用户登出 |
| `/auth/api/me` | GET | 获取当前用户信息 |
| `/auth/api/refresh` | POST | 刷新JWT token |

#### 2. 账户管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/accounts/api/ledgers` | GET | Grid.js 账户列表API |
| `/accounts/api/ledgers/<int:account_id>/permissions` | GET | 获取账户权限详情 |

#### 3. 账户统计模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/accounts/api/statistics` | GET | 账户统计API |
| `/accounts/api/statistics/classifications` | GET | 按分类统计 |
| `/accounts/api/statistics/db-types` | GET | 按数据库类型统计 |
| `/accounts/api/statistics/summary` | GET | 账户统计汇总 |

#### 4. 账户分类模块

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

#### 5. 账户同步模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/accounts/sync/api/instances/<int:instance_id>/sync` | POST | 同步指定实例的账户信息,统一返回 JSON |
| `/accounts/sync/api/sync-all` | POST | 触发后台批量同步所有实例的账户信息 |

#### 6. 容量聚合模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/capacity/api/aggregations/current` | POST | 手动触发当前周期数据聚合 |

#### 7. 数据库容量同步模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/databases/api/instances/<int:instance_id>/sync-capacity` | POST | 同步指定实例的容量信息 |

#### 8. 数据库台账模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/databases/api/ledgers` | GET | 获取数据库台账列表数据 |
| `/databases/api/ledgers/<int:database_id>/capacity-trend` | GET | 获取单个数据库的容量走势 |

#### 9. 通用数据模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/common/api/databases-options` | GET | 获取指定实例的数据库下拉选项(通用) |
| `/common/api/dbtypes-options` | GET | 获取数据库类型选项(通用) |
| `/common/api/instances-options` | GET | 获取实例下拉选项(通用) |

#### 10. 连接管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/connections/api/batch-test` | POST | 批量测试连接 |
| `/connections/api/status/<int:instance_id>` | GET | 获取实例连接状态 |
| `/connections/api/test` | POST | 测试数据库连接API |
| `/connections/api/validate-params` | POST | 验证连接参数 |

#### 11. 凭据管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/credentials/api/<int:credential_id>/edit` | POST | 编辑凭据API |
| `/credentials/api/create` | POST | 创建凭据API |
| `/credentials/api/credentials` | GET | 获取凭据列表API |
| `/credentials/api/credentials` | POST | RESTful 创建凭据API,供前端 CredentialsService 使用 |
| `/credentials/api/credentials/<int:credential_id>` | GET | 获取凭据详情API |
| `/credentials/api/credentials/<int:credential_id>` | PUT | RESTful 更新凭据API |
| `/credentials/api/credentials/<int:credential_id>/delete` | POST | 删除凭据 |

#### 12. 仪表板模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/dashboard/api/activities` | GET | 获取最近活动API (已废弃) |
| `/dashboard/api/charts` | GET | 获取仪表板图表数据 |
| `/dashboard/api/overview` | GET | 获取系统概览API |
| `/dashboard/api/status` | GET | 获取系统状态API |

#### 13. 数据库聚合页面模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/capacity/api/databases` | GET | 获取数据库统计聚合数据(数据库统计层面) |
| `/capacity/api/databases/summary` | GET | 获取数据库统计聚合汇总信息 |

#### 14. 实例详情扩展模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/api/<int:instance_id>/accounts/<int:account_id>/change-history` | GET | 获取账户变更历史 |
| `/instances/api/<int:instance_id>/accounts/<int:account_id>/permissions` | GET | 获取账户权限详情 |
| `/instances/api/<int:instance_id>/edit` | POST | 编辑实例API |
| `/instances/api/databases/<int:instance_id>/sizes` | GET | 获取指定实例的数据库大小数据(最新或历史) |

#### 15. 实例聚合模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/capacity/api/instances` | GET | 获取实例聚合数据(实例统计层面) |
| `/capacity/api/instances/summary` | GET | 获取实例聚合汇总信息(实例统计层面) |

#### 16. 实例管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/api/<int:instance_id>` | GET | 获取实例详情API |
| `/instances/api/<int:instance_id>/accounts` | GET | 获取实例账户数据API |
| `/instances/api/<int:instance_id>/delete` | POST | 删除实例 |
| `/instances/api/<int:instance_id>/restore` | POST | 恢复实例 |
| `/instances/api/create` | POST | 创建实例API |
| `/instances/api/instances` | GET | Grid.js 实例列表API |

#### 17. 实例批量操作模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/batch/api/create` | POST | 批量创建实例 |
| `/instances/batch/api/delete` | POST | 批量删除实例 |

#### 18. 实例统计模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/api/statistics` | GET | 获取实例统计API |

#### 19. 健康检查模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/health/api/basic` | GET | 基础健康检查 |
| `/health/api/cache` | GET | 缓存服务健康检查 |
| `/health/api/detailed` | GET | 详细健康检查 |
| `/health/api/health` | GET | 健康检查(供外部监控使用) |

#### 20. 缓存管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/cache/api/classification/clear` | POST | 清除分类相关缓存 |
| `/cache/api/classification/clear/<db_type>` | POST | 清除特定数据库类型的缓存 |
| `/cache/api/classification/stats` | GET | 获取分类缓存统计信息 |
| `/cache/api/clear/all` | POST | 清除所有缓存 |
| `/cache/api/clear/instance` | POST | 清除实例缓存 |
| `/cache/api/clear/user` | POST | 清除用户缓存 |
| `/cache/api/stats` | GET | 获取缓存统计信息 |

#### 21. 日志模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/history/logs/api/detail/<int:log_id>` | GET | 获取日志详情API |
| `/history/logs/api/list` | GET | Grid.js 日志列表API |
| `/history/logs/api/modules` | GET | 获取日志模块列表API |
| `/history/logs/api/search` | GET | 搜索日志API |
| `/history/logs/api/statistics` | GET | 获取日志统计信息API |

#### 22. 分区管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/partition/api/aggregations/core-metrics` | GET | 获取核心聚合指标数据 |
| `/partition/api/cleanup` | POST | 清理旧分区 |
| `/partition/api/create` | POST | 创建分区任务 |
| `/partition/api/info` | GET | 获取分区信息API |
| `/partition/api/partitions` | GET | 分页返回分区列表,供 Grid.js 使用 |
| `/partition/api/statistics` | GET | 获取分区统计信息 |
| `/partition/api/status` | GET | 获取分区管理状态 |

#### 23. 定时任务模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/scheduler/api/jobs` | GET | 获取所有定时任务 |
| `/scheduler/api/jobs/<job_id>` | GET | 获取指定任务详情 |
| `/scheduler/api/jobs/<job_id>` | PUT | 更新定时任务 |
| `/scheduler/api/jobs/<job_id>/pause` | POST | 暂停任务 |
| `/scheduler/api/jobs/<job_id>/resume` | POST | 恢复任务 |
| `/scheduler/api/jobs/<job_id>/run` | POST | 立即执行任务 |
| `/scheduler/api/jobs/reload` | POST | 重新加载所有任务配置 |

#### 24. 同步会话模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/history/sessions/api/sessions` | GET | 获取同步会话列表API |
| `/history/sessions/api/sessions/<session_id>` | GET | 获取同步会话详情API |
| `/history/sessions/api/sessions/<session_id>/cancel` | POST | 取消同步会话API |
| `/history/sessions/api/sessions/<session_id>/error-logs` | GET | 获取同步会话错误日志API |

#### 25. 标签管理模块

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

#### 26. 标签批量操作模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/tags/bulk/api/assign` | POST | 批量分配标签给实例 |
| `/tags/bulk/api/instance-tags` | POST | 获取实例的已关联标签API |
| `/tags/bulk/api/instances` | GET | 获取所有实例列表API |
| `/tags/bulk/api/remove` | POST | 批量移除实例的标签 |
| `/tags/bulk/api/remove-all` | POST | 批量移除实例的所有标签 |
| `/tags/bulk/api/tags` | GET | 获取所有标签列表API(包括非活跃标签) |

#### 27. 用户管理模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/users/api/users` | GET | 获取用户列表API |
| `/users/api/users` | POST | 创建用户API |
| `/users/api/users/<int:user_id>` | DELETE | 删除用户API |
| `/users/api/users/<int:user_id>` | GET | 获取单个用户信息API |
| `/users/api/users/<int:user_id>` | PUT | 更新用户API |
| `/users/api/users/stats` | GET | 获取用户统计信息API |

#### 28. 文件导入导出模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/files/api/account-export` | GET | 导出账户数据为 CSV |
| `/files/api/database-ledger-export` | GET | 导出数据库台账列表为 CSV |
| `/files/api/instance-export` | GET | 导出实例数据为 CSV |
| `/files/api/log-export` | GET | 导出日志API |
| `/files/api/template-download` | GET | 下载实例批量导入模板 |

#### 29. 主路由模块

| 路径 | 方法 | 描述 |
|------|------|------|
| `/admin/api/app-info` | GET | 获取应用信息(供前端展示应用名称等) |
