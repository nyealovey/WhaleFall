# 架构审计报告 (Architecture Audit) - 2025-12-26

> 状态: Draft
> 负责人: WhaleFall Arch/SRE/Security Audit (Codex)
> 创建: 2025-12-26
> 更新: 2025-12-26
> 范围: `app/`, `nginx/`, `docker-compose*.yml`, `Dockerfile.prod`, `docs/architecture/**`, `docs/reference/**`, `docs/operations/**`
> 关联: [documentation-standards](../standards/documentation-standards.md), [halfwidth-character-standards](../standards/halfwidth-character-standards.md), [architecture-review](../architecture/architecture-review.md), [adr-backlog](../architecture/adr/adr-backlog.md), [environment-variables](../reference/config/environment-variables.md), [api-routes-documentation](../reference/api/api-routes-documentation.md), [task-and-scheduler](../standards/backend/task-and-scheduler.md), [configuration-and-secrets](../standards/backend/configuration-and-secrets.md), [api-response-envelope](../standards/backend/api-response-envelope.md), [error-message-schema-unification](../standards/backend/error-message-schema-unification.md), [database-migrations](../standards/backend/database-migrations.md), [write-operation-boundary](../standards/backend/write-operation-boundary.md)

## I. 摘要结论 (先给结论)

- 当前仓库在"文档覆盖面"与"分层边界"上已经有较完整的基线,但生产可运维性仍存在 3 个 P0 风险: (1) Cookie/HTTPS 安全口径与部署拓扑不一致, (2) 进程/端口边界不够严格导致攻击面扩大, (3) Scheduler 可用性与持久化不受健康检查约束, 可能出现"任务不跑但系统显示健康".
- 主要 P1 缺口集中在"可观测性闭环"与"契约治理": request_id/user_id 相关的上下文变量已定义但未落地, 导致日志/错误响应无法关联; 同时, API 鉴权失败的响应形态依赖 `request.is_json`, 对典型 GET AJAX 不可靠, 易退化为 HTML 重定向.
- 本报告刻意不重复已有的性能与前端 UI/UX 结论, 仅在需要补充更具体证据或上升为架构决策时引用: [performance-audit](./2025-12-25_performance-audit-report.md), [frontend-ui-ux-audit](./2025-12-25_frontend-ui-ux-audit-report.md).

## II. 范围与方法

### A. 现有评审覆盖清单 (只列主题)

- `docs/architecture/architecture-review.md`: 评审入口与 ADR 待办索引 (覆盖清单目前为空).
- `docs/architecture/spec.md`: 项目概述, 分层架构, 技术栈, 数据模型, 业务流程, API 设计, 安全/性能/调度/日志/部署设计, 模块规格, 开发规范.
- `docs/architecture/project-structure.md`: 目录结构与模块职责索引, 分层原则与命名约定.
- `docs/architecture/module-dependency-graph.md`: routes/services/repositories/models/tasks 的依赖方向约束.
- `docs/reference/config/environment-variables.md`: 环境变量字段表, 默认值与兼容性说明.
- `docs/reference/api/api-routes-documentation.md`: 路由索引, JSON 封套/CSRF/权限约定, safe_route_call 建议.
- `docs/reference/database/*`: schema baseline, 驱动支持, 权限概览.
- `docs/operations/*`: 部署/热更新 Runbook 与故障排查入口.
- `docs/reports/2025-12-25_performance-audit-report.md`: 关键链路性能瓶颈与止血方案.
- `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`: 桌面端 UI/UX 缺口与契约漂移症状.

### B. 缺口地图 (按 1-9 维度逐条对照)

1) 需求与边界
- 缺口: 缺少"必须不出错"关键链路清单与 SLO/降级策略, 以及 Web(Page)/API/Tasks/External 的边界与数据流责任边界.
- 建议补写小节标题: `Critical Paths & Failure Modes`, `System Boundaries (Web/API/Tasks/External)`.

2) 运行时拓扑与部署
- 缺口: 进程模型 (gunicorn worker_class/并发/线程) 与 Scheduler 拓扑未形成"可执行约束", 健康检查语义与优雅关闭/资源回收缺少统一口径.
- 建议补写小节标题: `Process Model & Concurrency`, `Scheduler Topology & Single-Instance Rules`, `Readiness/Liveness Semantics`.

3) 配置与环境一致性
- 缺口: Settings 尚未覆盖全部关键运行参数 (如日志队列参数, scheduler 开关等), 且部分 compose/env 变量与代码的 SSOT 不一致 (例如 APP_VERSION).
- 建议补写小节标题: `Settings SSOT Coverage`, `Environment Matrix (dev/staging/prod)`, `Secrets Rotation & Validation Rules`.

4) API 设计与契约治理
- 缺口: "API 请求判定"与"未登录/无权限"的响应形态缺少一致契约; internal result schema 仍存在漂移空间 (error/message 混用) 诱发前端兜底.
- 建议补写小节标题: `API Zones & Versioning`, `AuthN/AuthZ Error Contract`, `Contract Drift Playbook (canonicalization -> remove fallback)`.

5) 数据与一致性
- 缺口: Scheduler jobstore 的持久化与一致性策略未落到部署约束; 外部 DB 同步的幂等/补偿/去重口径未固化为 ADR.
- 建议补写小节标题: `Jobstore Persistence & Backup`, `Idempotency/Compensation for Sync Tasks`, `Rolling Migration Compatibility`.

6) 可靠性与韧性 (Resilience)
- 缺口: 外部依赖失败策略未统一 (timeout/retry/backoff/circuit-break); 日志链路在 DB 不可用时的退路与告警信号缺口明显.
- 建议补写小节标题: `External Dependency Policy`, `Logging Failure Mode & Backpressure`, `Rate Limit & Retry Budget`.

7) 安全
- 缺口: TLS/HTTPS 的边界责任不清晰, Cookie 安全属性与端口暴露策略不匹配; RBAC 权限来源仍为 stub, 缺少审计留痕口径.
- 建议补写小节标题: `Production Security Baseline (TLS/Cookies/Ports)`, `RBAC Source of Truth`, `Audit Log & Data Access Policy`.

8) 可观测性与可运维性
- 缺口: request_id 设计存在但未贯通, 导致"错误响应 -> 日志中心 -> 会话/任务"无法串联; 告警阈值与责任人未形成可执行清单.
- 建议补写小节标题: `Observability Contract (request_id/log fields)`, `Alerts & Runbooks`, `Scheduler Health Signals`.

9) 代码组织与演进成本
- 缺口: 分层约束已有文档, 但缺少对"契约漂移/兜底逻辑"的门禁闭环; 关键链路的最小测试集与回归口径未形成标准化模板.
- 建议补写小节标题: `Architecture Guardrails (lint/gates)`, `Critical Path Test Strategy`, `Compatibility Removal Plan`.

### C. 证据采集与审计方法

- 文档侧: 阅读 `docs/architecture/**`, `docs/reference/**`, `docs/operations/**`, 以及近 1 日的审计报告 (性能, UI/UX).
- 代码侧: 重点抽查入口与横切能力 `app/__init__.py`, `app/settings.py`, `app/scheduler.py`, `app/utils/structlog_config.py`, `app/utils/logging/**`, `app/utils/decorators.py`, 以及生产部署配置 `docker-compose.prod.yml`, `Dockerfile.prod`, `nginx/**`.
- 扫描侧: 使用 `rg -n` 对兼容/兜底/适配关键模式进行静态扫描, 并将"空命中"的证据写入 artifacts, 便于复核 (见 V 节).

### D. 输出口径与分级 (P0/P1/P2)

- P0: 可能导致数据泄露, 数据丢失, 核心任务不跑, 或生产可用性显著下降且不易被发现.
- P1: 会显著降低可观测性/可治理性, 或容易在规模化/多环境下引入事故.
- P2: 主要影响一致性, 可维护性, 或造成长期演进阻力.

## III. 发现清单 (按 P0/P1/P2)

### P0

#### P0-01 Cookie/HTTPS 安全口径与部署拓扑不一致, 存在会话泄露与误配置风险

- 证据:
  - `app/__init__.py:217` 固定 `SESSION_COOKIE_SECURE = False`.
  - `nginx/sites-available/whalefall-prod:1` 仅监听 80, 未看到 443 TLS server block.
  - `docker-compose.prod.yml:111` 暴露端口包含 `80:80`, `443:443`, `5001:5001` (TLS 责任边界不清晰).
- 影响:
  - 一旦存在可达的明文 HTTP 链路 (例如直连 `:5001` 或上游未做 TLS), 会话 Cookie 可能在明文链路中传输, 造成会话劫持风险.
  - 安全与运维口径不一致会导致排障与发布时的"隐性假设"漂移 (例如某环境以为启用 HTTPS, 实际只启用 80).
- 根因:
  - 应用层安全配置硬编码, 未与 Settings/部署拓扑形成可执行约束 (缺少 ADR-001/003/006 的落地闭环).
- 建议:
  - 短期止血 (1-3 天): 在 `Settings` 中引入 `session_cookie_secure` 并按 `force_https` 或 `is_production` 设置, 同时移除硬编码 `SESSION_COOKIE_SECURE=False`; 明确是否需要在 Nginx 侧配置 TLS, 若不在容器内做 TLS, 则删除 443 暴露并在部署文档标注"TLS 由上游负责".
  - 中期重构 (1-2 周): 写入 ADR `TLS termination & cookie policy`, 明确 HSTS/redirect/secure cookie 的责任边界, 并对关键路径加 smoke test (登录后 Set-Cookie 属性).
  - 长期演进: 将安全基线纳入门禁 (扫描 Set-Cookie, 扫描对外暴露端口, 扫描 FORCE_HTTPS 是否生效).
- 验证:
  - 运行 `curl -i` 登录接口, 检查 `Set-Cookie` 是否包含 `Secure; HttpOnly; SameSite=...`.
  - 若启用 HTTPS: 访问 `http://...` 是否强制跳转到 `https://...`, 且不会在 http 响应中写入 session cookie.

#### P0-02 生产 compose 暴露 Gunicorn 端口 (5001) 导致攻击面扩大, 并弱化反向代理的控制面

- 证据:
  - `docker-compose.prod.yml:114` 暴露 `5001:5001`.
  - `nginx/sites-available/whalefall-prod:23` Nginx 反代到 `127.0.0.1:5001` (说明该端口本意应为内网/容器内).
  - `app/utils/proxy_fix_middleware.py:18` 注释明确提示"误把 Gunicorn 端口对外开放"会带来风险.
- 影响:
  - 任何绕过 Nginx 的直连访问都会绕过 Nginx 的缓存/限流/超时/错误页等控制面, 增加 DoS 与误配置风险.
  - 与 P0-01 叠加时, 可能出现"直连 HTTP + 不安全 cookie"的组合风险.
- 根因:
  - 部署拓扑缺少"最小暴露面"硬约束, compose 模板未按安全默认值收敛.
- 建议:
  - 短期止血 (0.5-1 天): 从生产 compose 移除 `5001:5001`, 仅对外暴露 80 (以及在明确 TLS 配置存在时才暴露 443); 需要调试时使用 `docker exec` 或受控的临时端口转发.
  - 中期重构 (1-3 天): 写入 ADR `Ingress/Ports boundary`, 并在 `docs/operations/deployment/*` 明确端口策略与回滚方式.
  - 长期演进: 增加门禁脚本扫描 compose 中的端口暴露, 防止回归.
- 验证:
  - 在部署机上验证外部无法访问 `host:5001`, 仅能通过 `host:80` 访问应用.

#### P0-03 Scheduler 可用性与持久化不受健康检查约束, 可能出现"任务不跑但系统显示健康"

- 证据:
  - `app/__init__.py:122` Scheduler 初始化异常被 catch 并继续启动.
  - `Dockerfile.prod:143` 与 `docker-compose.prod.yml:125` 健康检查均调用 `/health/api/basic`.
  - `app/routes/health.py:36` `/health/api/basic` 恒返回 `status: healthy`, 且不检查 DB/Redis/Scheduler.
  - `app/scheduler.py:128` jobstore 使用本地 `userdata/scheduler.db`, 锁使用本地 `userdata/scheduler.lock`.
  - `docker-compose.prod.yml:105` 生产 compose 注释掉了 `/app/userdata` 持久化卷, 与 scheduler.db/日志文件的落点相冲突.
  - `nginx/supervisor/whalefall-prod.conf:34` 注释声明"调度器已集成在 Flask 应用中, 不需要单独启动".
- 影响:
  - 任务体系是 WhaleFall 的核心价值链路 (同步, 聚合, 清理). 一旦 scheduler 初始化失败或 jobstore 损坏, 系统可能长期不再产出新数据, 但健康检查仍为 green, 难以及时发现.
  - jobstore 与日志落在容器临时文件系统时, 任何重建/迁移都会丢失调度配置与本地日志, 影响回溯与审计.
- 根因:
  - 健康检查语义未区分 live/ready, 且未覆盖 scheduler 关键依赖.
  - Scheduler 使用本地文件锁 + SQLite jobstore, 与 scale-out 和持久化需求天然冲突, 但缺少 ADR 约束其适用边界.
- 建议:
  - 短期止血 (1-3 天):
    - 引入 `/health/live` (仅进程存活) 与 `/health/ready` (依赖可用 + scheduler 状态) 并将容器健康检查切到 ready.
    - 明确 `ENABLE_SCHEDULER` 在 Web 进程与 Scheduler 进程的分工策略, 并在部署脚本中固化 (Web 默认关闭 scheduler, 另起 scheduler 进程时再开启).
    - 若仍使用 SQLite jobstore: 必须持久化 `userdata/` 或至少持久化 `scheduler.db`.
  - 中期重构 (1-2 周): 将 APScheduler jobstore 迁移到 Postgres (或其它集中式存储), 取消本地文件锁, 用 DB 级 leader election/唯一实例策略替代.
  - 长期演进: 为 scheduler 增加指标与告警 (jobs_count, last_job_run_at, scheduler_running, missed_jobs), 并配套 Runbook 演练.
- 验证:
  - 人工禁用 scheduler (`ENABLE_SCHEDULER=false`) 后, `/health/ready` 应返回非 200 或在 data 中明确标记不可用, 并触发告警.
  - 重建容器后验证 scheduler 配置是否保留 (jobstore 持久化 or DB jobstore).

### P1

#### P1-01 request_id/user_id 关联链路未落地, 导致日志与错误响应无法串联

- 证据:
  - `app/utils/logging/context_vars.py:5` 定义 `request_id_var`, `user_id_var`.
  - `app/utils/structlog_config.py:158` 日志处理器读取 `request_id_var.get()` 与 `user_id_var.get()`.
  - `app/utils/logging/handlers.py:241` 写入 UnifiedLog.context 时读取 `request_id_var.get()` 且依赖 `g.url/g.method/...`.
  - `docs/reports/artifacts/2025-12-26_architecture-audit-request-context-var-set.txt` 显示 repo 内无 `(request_id_var|user_id_var).set` 命中.
  - `app/static/js/modules/ui/danger-confirm.js:34` 前端兼容读取 `request_id || requestId`.
- 影响:
  - 线上排障无法做到"一次错误 -> 一个认为可信的 request_id -> 一条后端日志 -> 一次 DB 访问/任务会话", 会显著拉长 MTTR.
  - 前端组件已经在消费 request_id, 但后端产出为空会导致 UI 能力打折 (例如错误详情联动日志中心).
- 根因:
  - 缺少 before_request/after_request 的统一上下文注入 (request_id, actor_id, url, method, ip, user_agent).
- 建议:
  - 短期止血 (1-2 天): 在 `create_app` 注册 before_request: 生成/接收 `X-Request-Id`, 写入 `request_id_var`, 同时写入 `g.url/g.method/...`; 在 teardown 或 after_request reset context var.
  - 中期重构 (1 周): 统一把 request_id 回写到响应头, 并在错误封套的 `context.request_id` 中保证非空.
  - 长期演进: 将 request_id 贯通到 scheduler/task (job_id + request_id), 建立"会话中心"与"日志中心"联动.
- 验证:
  - 任意请求响应头包含 `X-Request-Id`, 且同一 request_id 能在 UnifiedLog 查询到对应日志.
  - 触发一次错误, 错误响应中的 `context.request_id` 非空且可定位到日志.

#### P1-02 日志链路对 DB 可用性耦合较强, 且存在 renderer 配置与参数 SSOT 缺口

- 证据:
  - `app/utils/structlog_config.py:81` processors 同时包含 `ConsoleRenderer` 与 `JSONRenderer`.
  - `app/utils/structlog_config.py:126` 日志队列参数读取 `LOG_QUEUE_SIZE/LOG_BATCH_SIZE/LOG_FLUSH_INTERVAL`, 但 `Settings.to_flask_config` 未提供这些配置键 (参见 `app/settings.py:549` 的 payload).
  - `app/utils/logging/queue_worker.py:102` 队列满时丢弃日志, 且失败写 DB 时仅 `queue_logger.exception(...)` (stdout/file 是否可见取决于 logging 配置).
- 影响:
  - DB 异常时, 最需要日志的时刻反而可能丢日志或不可见, 形成"黑盒"排障.
  - renderer 链可能输出非预期格式, 降低日志可解析性.
  - 参数不在 Settings 中, 运维无法通过 env 调整队列与 flush 行为.
- 根因:
  - 日志系统设计以 DB 持久化为主, 但缺少"失败退路"与"可配置口径"的架构约束.
- 建议:
  - 短期止血 (1-2 天): renderer 二选一 (tty 用 console, 非 tty 用 JSON), 并在 DB 写失败时至少保底输出到 stdout/file.
  - 中期重构 (1 周): 把日志队列参数纳入 Settings + env reference, 增加 dropped_count/flush_error_count 指标.
  - 长期演进: 将 stdout 作为主日志面, DB 日志作为可选索引或采样存储, 降低耦合.
- 验证:
  - 人工让 DB 不可用, 触发错误后仍可从 stdout/file 获得结构化日志与 request_id.
  - 压测触发队列接近满载时, dropped_count 可被观测并告警.

#### P1-03 鉴权失败的响应形态依赖 `request.is_json`, 对典型 GET `/api/*` 不可靠

- 证据:
  - `app/utils/decorators.py:210` `permission_required` 仅在 `request.is_json` 时抛出 JSON 错误, 否则 redirect.
  - `app/routes/partition.py:44` `/partition/api/info` 等 GET API 使用 `flask_login.login_required` + `view_required` (未见统一的 unauthorized_handler).
- 影响:
  - 未登录访问 API 时可能返回 302 + HTML, 前端 fetch 侧会出现 JSON parse 失败或"未知错误", 进而诱发更多兜底逻辑与不可治理的契约漂移.
  - 监控侧无法用 401/403 直接统计鉴权类错误.
- 根因:
  - "API 请求"判定缺少稳定标准 (path/Accept/X-Requested-With), 权限装饰器与 Flask-Login 未形成统一对外契约.
- 建议:
  - 短期止血 (1-3 天): 实现 `wants_json_response()` 并以 path 是否包含 `/api/` 为主判定, 同时覆盖 Accept/X-Requested-With; 在未登录/无权限时返回统一错误封套 + 401/403.
  - 中期重构: 给 Flask-Login 配置 `unauthorized_handler` 与 `needs_refresh_handler`, 统一 JSON/API 的未授权返回.
  - 长期演进: 写 ADR `API auth strategy` (session vs JWT, CSRF/CORS 边界).
- 验证:
  - 未登录 `curl -i /partition/api/info` 返回 401 JSON 封套而非 302.
  - 前端在登录失效时能稳定引导到登录页, 而非出现随机 toast.

#### P1-04 per-request 修改 `app.config` 存在并发污染风险, 与 Settings/ProxyFix 的职责重叠

- 证据:
  - `app/__init__.py:194` 在 `before_request` 中修改 `app.config["PREFERRED_URL_SCHEME"]`.
- 影响:
  - 在 gevent/多线程并发下, 全局 config 可能被单个请求修改后影响其它请求的 URL 生成与跳转, 引发难以复现的线上问题.
- 根因:
  - 把 per-request 状态写入全局 config, 未使用 request environ 或 ProxyFix 的标准做法.
- 建议:
  - 短期止血: 移除该 before_request 修改, 改为依赖 `TrustedProxyFix`/`ProxyFix` 解析 `wsgi.url_scheme`.
  - 中期重构: 用 ADR 固化"scheme 判定"责任边界, 并加测试覆盖 (HTTP/HTTPS, 代理/直连).
- 验证:
  - 并发请求下 `url_for(..., _external=True)` 不会出现 scheme 串扰.

#### P1-05 外部数据库适配器超时策略不统一, Oracle 连接缺少显式 timeout

- 证据:
  - `app/services/connection_adapters/adapters/oracle_adapter.py:89` `oracledb.connect(...)` 未传入 timeout 相关参数.
- 影响:
  - 外部 DB 不可达时可能出现长时间 hang, 占用线程/greenlet, 进而影响 API 与 scheduler 稳定性.
- 根因:
  - 超时与重试策略未集中到 Settings, 适配器各自为政.
- 建议:
  - 短期止血: 为 Oracle 连接补齐 connect/statement timeout (按驱动能力), 并把 timeout 参数纳入 Settings.
  - 中期重构: 统一 external dependency policy (timeout/retry/backoff/circuit-break), 并记录到 ADR.
- 验证:
  - 通过不可达 host 的集成测试, 所有适配器在可控时间内失败并返回统一错误.

#### P1-06 内部 result schema 漂移与大 payload 进入日志, 会放大契约治理与存储成本

- 证据:
  - `app/routes/connections.py:311` batch-test 结果项有的使用 `error`, 有的使用 `message`, 结构不统一.
  - `app/routes/databases/capacity_sync.py:220` 失败时日志记录 `result=result`, 其内部可能包含 `databases`/`inventory` 等大结构.
  - `app/utils/logging/handlers.py:266` 会把任意 event_dict 的字段写入日志 context (缺少 size budget).
- 影响:
  - 前端被迫使用 `error || message` 一类兜底, 使契约长期不可治理.
  - 大结构写入日志表会直接抬升存储与查询成本, 并放大"日志中心慢"的问题.
- 根因:
  - 缺少 internal result schema 的 canonicalization 边界与门禁, 日志 schema 未定义大小约束.
- 建议:
  - 短期止血: 先在批量连接测试等高频接口收敛 per-item schema (status/message/error_code/error_id), 并禁止把大列表写进日志 context (改为计数 + 引用 id).
  - 中期重构: 增加 drift guard (后端 result schema, 前端 `error || message` 命中), 并给 UnifiedLog.context 定义字段白名单与 size budget.
  - 长期演进: 建立"兼容窗口"与"兜底命中统计"机制, 让兜底可被观测并可删除.
- 验证:
  - 前端相关页面删除 `error || message` 兜底后仍可稳定工作.
  - UnifiedLog 表增长率下降, 日志查询 p95 降低.

### P2

#### P2-01 版本号来源不唯一, 健康检查返回硬编码版本导致可观测性漂移

- 证据:
  - `docker-compose.prod.yml:103` 注入 `APP_VERSION`, 但 `app/settings.py:146` 版本来自常量 `APP_VERSION`.
  - `app/routes/health.py:49` `/health/api/basic` 返回 `"version": "1.0.7"`, `app/routes/health.py:101` detailed 返回 `"1.1.2"`.
- 影响:
  - 回滚与问题定位无法信任版本字段, 降低排障效率.
- 根因:
  - 版本 SSOT 未固化 (build-time vs runtime env vs code constant).
- 建议:
  - 短期止血: health API 统一返回 `current_app.config["APP_VERSION"]`, 并移除硬编码版本.
  - 中期重构: 写 ADR `versioning strategy` (代码常量 vs CI 注入), 并在 release 流程中固化.
- 验证:
  - 任意环境 `curl /health/api/basic` 的版本字段与应用实际版本一致且单一来源.

#### P2-02 routes 侧存在事务边界的局部漂移, 增加理解与门禁成本

- 证据:
  - `app/routes/instances/batch.py:142` 在 `safe_route_call` 外层捕获异常并手动 `db.session.rollback()`.
  - `docs/standards/backend/write-operation-boundary.md` 明确 routes 不应直接操作 `db.session`.
- 影响:
  - 代码风格与事务边界口径不一致, 未来引入门禁时会产生噪音或误报.
- 根因:
  - 个别路径为了自定义错误响应绕开了统一错误处理器.
- 建议:
  - 短期止血: 用 `safe_route_call` + 全局错误处理统一返回错误封套, 移除 route 侧手工 rollback.
  - 中期重构: 运行写边界门禁脚本作为 CI gate, 逐步清理存量例外.
- 验证:
  - 运行 `./scripts/ci/db-session-write-boundary-guard.sh` (如可用) 确认 routes 不再直接触碰 `db.session`.

### 附加: 防御/兼容/回退/适配扫描 (重点关注 or/||/get(... ) 兜底)

- 位置: `app/settings.py:179`
  - 类型: 兼容
  - 描述: JWT refresh 过期配置兼容旧变量名, `JWT_REFRESH_TOKEN_EXPIRES` 或 `JWT_REFRESH_TOKEN_EXPIRES_SECONDS`.
  - 建议: 设定兼容窗口, 在 env reference 标注 deprecate 时间, 并增加兜底命中统计后删除别名.

- 位置: `app/settings.py:106`
  - 类型: 回退
  - 描述: 主库连接串缺失时回退到本地 SQLite (`_resolve_sqlite_fallback_url`).
  - 建议: 明确该回退仅用于 dev, staging/prod 应直接 fail-fast, 并在部署 Runbook 中加校验.

- 位置: `app/settings.py:112`
  - 类型: 适配
  - 描述: macOS Oracle Instant Client 环境变量补全, 通过 `DYLD_LIBRARY_PATH` 做一次性注入.
  - 建议: 将平台适配逻辑集中到 adapter 层或启动脚本, 并在文档中标注适用 OS 与风险.

- 位置: `app/utils/password_crypto_utils.py:50`
  - 类型: 回退
  - 描述: 缺失 `PASSWORD_ENCRYPTION_KEY` 时生成临时密钥, 以保证流程可运行.
  - 建议: 在所有非 dev 环境强制要求固定密钥, 并对"临时密钥"启动增加显式告警信号.

- 位置: `app/scheduler.py:404`
  - 类型: 防御
  - 描述: scheduler 开关缺失时默认启用 (`ENABLE_SCHEDULER` 默认为 `true`), 并在 gunicorn/reloader 场景做进程判定.
  - 建议: 把该开关纳入 Settings SSOT, 并在部署拓扑 ADR 中明确 Web/Scheduler 分工默认值.

- 位置: `app/routes/databases/capacity_sync.py:229`
  - 类型: 防御
  - 描述: 失败时对错误信息做兜底 `(result or {}).get("message") or "实例容量同步失败"`.
  - 建议: 收敛 result schema, 保证 canonical `message` 字段稳定存在, 避免多层兜底扩散.

- 位置: `app/services/connection_adapters/adapters/oracle_adapter.py:64`
  - 类型: 适配
  - 描述: Oracle 客户端库路径通过 `ORACLE_CLIENT_LIB_DIR`/`ORACLE_HOME`/内置路径候选链路兜底.
  - 建议: 增加命中统计 (命中哪个路径), 并在容器镜像/部署文档中固化唯一推荐路径.

- 位置: `app/static/js/modules/ui/danger-confirm.js:34`
  - 类型: 兼容
  - 描述: request_id 字段兼容 snake_case 与 camelCase, `request_id || requestId`.
  - 建议: 后端统一输出 `request_id`, 前端记录兜底命中率, 达到阈值后移除兼容分支.

- 位置: `app/static/js/modules/views/instances/detail.js:280`
  - 类型: 防御
  - 描述: 成功判定使用 `data?.success || Boolean(data?.message)` 容易把失败消息误判为成功.
  - 建议: 前端只以 `success === true` 为准, 后端保证 success 字段稳定; 用告警统计误判兜底的命中率并清理.

- 位置: `app/static/js/modules/views/instances/detail.js:281`
  - 类型: 兼容
  - 描述: 成功消息多路径兜底 `data.message || data.data.result.message || "账户同步成功"`.
  - 建议: 统一后端 envelope 的 message 语义, 让前端只读取单一来源.

## IV. 建议与后续行动

### 最小可执行路线图 (最多 6 项, 每项 1-3 天)

1) 收敛生产入口与 Cookie 安全基线: 修正 `SESSION_COOKIE_SECURE`, 明确 TLS 责任边界, 并从生产 compose 移除 `5001:5001` 与无效 `443:443` 暴露 (P0-01/P0-02).
2) 引入 live/ready 健康检查并升级容器 healthcheck: `/health/live` 仅进程存活, `/health/ready` 覆盖 DB/Redis/Scheduler, 并把 Dockerfile/compose healthcheck 切到 ready (P0-03).
3) 贯通 request_id: before_request 生成 request_id, 写入日志与错误封套, 回写响应头, 同时补齐 `g.url/g.method/ip/user_agent` (P1-01).
4) 加固日志链路: renderer 二选一, DB 写失败时 stdout/file 保底, 并把 LOG_QUEUE_* 纳入 Settings + env reference, 加入 dropped_count 观测 (P1-02).
5) 统一鉴权失败响应契约: 实现 `wants_json_response()` 并在 decorators/Flask-Login unauthorized_handler 统一返回 JSON 错误封套, 覆盖典型 GET `/api/*` (P1-03).
6) 外部依赖超时策略收敛: 统一 external DB adapter timeout 配置, 补齐 Oracle timeout, 并把策略写入 ADR (P1-05).

## V. 证据与数据来源

- 代码与配置:
  - `app/__init__.py:64`
  - `app/settings.py:106`
  - `app/scheduler.py:397`
  - `app/routes/health.py:36`
  - `app/utils/structlog_config.py:67`
  - `app/utils/logging/handlers.py:224`
  - `app/utils/logging/queue_worker.py:60`
  - `app/utils/decorators.py:182`
  - `docker-compose.prod.yml:72`
  - `Dockerfile.prod:139`
  - `nginx/sites-available/whalefall-prod:1`
  - `nginx/gunicorn/gunicorn-prod.conf.py:12`
  - `nginx/supervisor/whalefall-prod.conf:19`

- 文档:
  - `docs/architecture/spec.md`
  - `docs/architecture/project-structure.md`
  - `docs/architecture/module-dependency-graph.md`
  - `docs/architecture/adr/adr-backlog.md`
  - `docs/reference/config/environment-variables.md`
  - `docs/reference/api/api-routes-documentation.md`
  - `docs/operations/deployment/deployment-guide.md`

- 扫描 artifacts:
  - `docs/reports/artifacts/2025-12-26_architecture-audit-request-context-var-set.txt`
  - `docs/reports/artifacts/2025-12-26_architecture-audit-flask-g-context-assignments.txt`
