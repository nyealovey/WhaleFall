# WhaleFall 架构评审补充（查漏补缺式，含证据链）

> 更新时间：2025-12-20  
> 目标：补齐 `docs/architecture/ARCHITECTURE_REVIEW.md` 未覆盖/覆盖不深的架构问题，并给出可落地的治理约束与 ADR 待办。  
> 范围：仓库代码 + 配置 + 部署脚本 + 运行时拓扑（不做业务正确性审计）。

## I. 现有评审覆盖清单（只列主题，不展开）

- TL;DR：整体架构定位与主要风险点
- 当前架构总览：运行时组件与典型请求链路
- 后端：分层现状、合理之处、配置收口、API 路径规范、scheduler 耦合、数据访问边界、迁移策略（当时的判断）
- 前端：SSR+渐进增强结构、脚本加载策略、全局命名空间风险、缺少测试
- “数据层 / API 分离”的澄清与改进路线图
- 防御/兼容/回退/适配逻辑（代表性样例）

## II. 缺口地图（按 1~9 维度逐条）

### 1) 需求与边界

- 缺口描述：缺少“核心用例/关键链路/SLO”定义；系统边界（页面/内部 API/对外 API/任务/外部系统）没有写成可执行约束。
- 建议补写的小节标题：
  - `关键链路与SLO（必须不出错的路径）`
  - `系统边界与外部依赖清单（DB/Redis/远端DB/文件/网络）`

### 2) 运行时拓扑与部署

- 缺口描述：缺少“生产进程模型”的事实证据（Gunicorn/worker/并发模型）与扩容策略；缺少优雅关闭、连接池回收、ready/live 的语义定义。
- 建议补写的小节标题：
  - `进程模型与扩容策略（Gunicorn/worker/线程/greenlet）`
  - `健康检查语义（live/ready）与优雅关闭`

### 3) 配置与环境一致性

- 缺口描述：Settings 已收口但“部署脚本/示例/文档”存在漂移；缺少弃用（deprecation）与变更窗口策略。
- 建议补写的小节标题：
  - `配置SSOT与弃用策略（Env var schema + 兼容窗口）`
  - `部署脚本与应用配置的契约（谁是最终事实）`

### 4) API 设计与契约治理

- 缺口描述：缺少 internal vs public API 的正式分区与版本化决策；认证方式（Session/JWT）与 CSRF/CORS 对齐缺少 ADR；DTO/TypedDict 输出稳定性缺少门禁。
- 建议补写的小节标题：
  - `API 分区与版本化（internal vs public）`
  - `错误封套与DTO约束（Producer-owned contract）`

### 5) 数据与一致性

- 缺口描述：事务边界（route/service/repo 谁负责 begin/commit）未形成强约束；分页/排序白名单、慢查询/索引策略缺少统一规范；多数据库适配器缺少 timeout/权限边界的契约化说明。
- 建议补写的小节标题：
  - `事务边界与失败策略（begin/commit/rollback）`
  - `查询与索引规范（分页/排序白名单/慢查询）`
  - `远端DB适配器契约（timeout/隔离/权限）`

### 6) 可靠性与韧性（Resilience）

- 缺口描述：任务体系缺少幂等/去重/补偿/告警的统一规范；外部依赖（远端 DB/Redis）失败时的 timeout/retry/circuit-break/降级缺少一致策略。
- 建议补写的小节标题：
  - `外部依赖失败策略（timeout/retry/circuit-break）`
  - `任务幂等与补偿（at-least-once 语义）`

### 7) 安全（必须落到证据）

- 缺口描述：缺少威胁模型与安全基线（Secrets、日志脱敏、端口暴露、HTTP 安全头、健康检查信息披露、出网能力/SSRF、上传策略）。
- 建议补写的小节标题：
  - `安全基线与威胁模型（Secrets/SSRF/XSS/上传/审计）`
  - `权限与审计日志规范（RBAC 最小权限）`

### 8) 可观测性与可运维性

- 缺口描述：已有结构化日志，但 request_id/trace 贯通缺失；缺少 metrics 与告警阈值；缺少 runbook（DB/Redis/任务/迁移/容量）。
- 建议补写的小节标题：
  - `可观测性三件套（logs/metrics/traces）`
  - `告警与Runbook（DB/Redis/任务/迁移故障）`

### 9) 代码组织与演进成本

- 缺口描述：分层虽清晰但缺少依赖方向强约束；关键路径测试缺口会阻碍重构；前端 vendor 依赖缺少供应链治理与回滚规范。
- 建议补写的小节标题：
  - `分层与依赖方向约束（route/service/repo）`
  - `测试策略（关键转换/回归点）`
  - `前端依赖治理与回滚策略`

## III. 新增架构问题清单（按 P0→P2 分组）

### P0

#### P0-1. 生产敏感配置以明文形式存在于版本库模板文件中，且文档引导直接复制使用

- 证据：`env.production:22`、`env.production:29`、`env.production:34`、`env.production:35`、`env.production:39`、`env.production:40`  
  证据：`docs/deployment/PRODUCTION_DEPLOYMENT.md:48`
- 影响：  
  - 最坏情况：仓库泄露等价于生产 DB/Redis/会话签名密钥泄露，导致数据脱库、会话/JWT 伪造、远端凭据被解密。  
  - 最可能发生方式：按部署文档复制默认值上线；或仓库被多人共享/外部曝光。
- 根因：把“可提交模板文件”当作“真实配置载体”，缺少 secret scanning 与模板占位符门禁。
- 建议：  
  - 短期止血（1~3 天）：将 `env.production` 改为纯占位符模板；对已部署环境立刻轮换 DB/Redis/SECRET/JWT/凭据加密密钥；增加 gitleaks/trufflehog 门禁阻断明文密钥提交。  
  - 中期重构（1~2 周）：引入统一 secrets 注入（Docker secrets/K8s Secret/Vault 任一），`.env` 仅用于本机开发；补密钥轮换 Runbook。  
  - 长期演进（可选）：凭据不落库/不落盘（外部 secret manager），应用仅持短期 token 或动态凭据。
- 验证：在 CI 跑 secret scan 0 命中；新建空环境按文档部署不再使用默认弱口令；旧 JWT/session 在轮换后失效。

#### P0-2. 凭据加/解密密钥缺失时会生成临时密钥并写入日志，造成密钥泄露与多进程不一致风险

- 证据：`app/utils/password_crypto_utils.py:50`、`app/utils/password_crypto_utils.py:56`、`app/utils/password_crypto_utils.py:60`
- 影响：  
  - 最坏情况：日志泄露即主密钥泄露，库中存储的远端 DB 密码可被解密；重启后无法解密历史凭据导致业务不可用。  
  - 最可能发生方式：环境变量缺失/误配；多 worker 下每进程生成不同密钥导致“部分实例能解密、部分不能”的间歇性故障。
- 根因：把“开发便利回退”放进安全边界且缺少密钥生命周期/轮换方案。
- 建议：  
  - 短期止血（1~3 天）：禁止输出密钥到日志；除本机开发外缺失密钥应 fail-fast；补日志脱敏/敏感键过滤。  
  - 中期重构（1~2 周）：实现多 key（KEY_VERSION）兼容解密与轮换迁移脚本。  
  - 长期演进（可选）：凭据迁移到外部 secret manager。
- 验证：缺失密钥时启动行为符合预期（非 dev 直接失败）；多 worker 下解密一致；日志中不再出现任何密钥材料。

#### P0-3. 生产 Compose/校验脚本与实际配置契约不一致，导致“部署卡死/启动失败”的高概率路径

- 证据：`docker-compose.prod.yml:50`（redis requirepass）+ `docker-compose.prod.yml:58`（redis healthcheck 未鉴权）  
  证据：`scripts/validate_env.sh:105`（DATABASE_URL 仅允许 postgresql://，但 compose 使用 postgresql+psycopg）  
  证据：`docker-compose.prod.yml:95`
- 影响：  
  - 最坏情况：redis 永远 unhealthy，`whalefall` 被 `depends_on` 卡住；或 `make deploy/start` 因校验失败直接退出。  
  - 最可能发生方式：严格按 `Makefile.prod` 执行部署链路。
- 根因：部署脚本/文档/compose 三套“真相”漂移，缺少 SSOT 与门禁。
- 建议：  
  - 短期止血（1~3 天）：修复 redis healthcheck（带 auth）；修复 validate_env 的 DATABASE_URL 校验以兼容 `postgresql+psycopg`；补一条一键 smoke test（起 compose → curl health → 迁移）。  
  - 中期重构（1~2 周）：让部署校验复用 `app/settings.py` 的校验逻辑或由文档表格生成校验规则。  
  - 长期演进（可选）：pydantic-settings + schema 驱动文档/校验/示例生成。
- 验证：全新环境按 `Makefile.prod` 能启动到 healthy；校验脚本在真实 DATABASE_URL 下不再误报。

#### P0-4. 会话安全与入口暴露不满足生产基线：SESSION_COOKIE_SECURE 固定为 False 且后端端口对外映射

- 证据：`app/__init__.py:179`  
  证据：`docker-compose.prod.yml:111`、`docker-compose.prod.yml:114`
- 影响：  
  - 最坏情况：HTTPS 场景下 cookie 不带 Secure，存在降级/中间人风险；5001 直连绕过入口层安全策略与治理能力。  
  - 最可能发生方式：生产/内网混用、旁路访问 5001。
- 根因：安全策略未与环境/拓扑绑定，compose 缺少最小化暴露原则。
- 建议：  
  - 短期止血（1~3 天）：SESSION_COOKIE_SECURE 与生产/force_https 绑定；生产 compose 移除 5001 对外映射（只保留 80/443）；明确 TLS 终止点。  
  - 中期重构（1~2 周）：补齐 ProxyFix/信任链与安全头基线；形成“入口边界”ADR。  
  - 长期演进（可选）：统一接入层（Ingress/LB），应用仅监听内网端口。
- 验证：`Set-Cookie` 符合预期（Secure/HttpOnly/SameSite）；外部无法直连 5001。

#### P0-5. 日志导出接口权限过宽，结合日志内容可能造成敏感信息外泄

- 证据：`app/routes/files.py:540`、`app/routes/files.py:541`、`app/routes/files.py:547`  
  证据：`app/routes/files.py:259`、`app/routes/files.py:260`、`app/routes/files.py:261`
- 影响：  
  - 最坏情况：任意登录用户可批量导出 traceback/context，形成敏感信息泄露与横向移动线索。  
  - 最可能发生方式：普通 user 账号被授予登录权限后可直接下载日志。
- 根因：日志访问未纳入 RBAC/审计，缺少最小披露与脱敏策略。
- 建议：  
  - 短期止血（1~3 天）：对 `/files/api/log-export` 增加 `@admin_required` 或专用权限（如 `logs.export`）；对 limit 设置硬上限并默认要求时间范围；对 context 做敏感键过滤。  
  - 中期重构（1~2 周）：区分审计日志与诊断日志；导出行为写入审计日志。  
  - 长期演进（可选）：日志下沉集中平台并做授权查询/脱敏。
- 验证：非管理员访问导出接口应 403；导出结果不包含敏感字段；导出动作可追踪。

### P1

#### P1-1. request_id 设计存在但未落地，结构化日志无法做到请求级关联

- 证据：`app/utils/logging/context_vars.py:5`  
  证据：`app/utils/structlog_config.py:148`  
  证据：`app/__init__.py:156`（唯一 before_request 未设置 request_id）  
  证据：`app/constants/http_headers.py:76`
- 影响：  
  - 最坏情况：线上故障无法从一次请求串起 route→service→外部依赖调用链，定位成本暴涨。  
  - 最可能发生方式：偶发失败/慢请求只能靠时间窗口猜测。
- 根因：观测字段模型已具备，但缺少 before_request/after_request 的贯通中间件。
- 建议：  
  - 短期止血（1~3 天）：新增 middleware：读取或生成 `X-Request-ID`，写入 ContextVar 与 g.*，响应头回写 `X-Request-ID`。  
  - 中期重构（1~2 周）：引入 trace_id/span_id（OpenTelemetry 或轻量实现），把任务执行与外部 DB 调用纳入关联键。  
  - 长期演进（可选）：完整可观测性栈（metrics+tracing+log correlation）。
- 验证：任意 API 调用日志中都包含相同 request_id；前端报错可回传 request_id 复现定位。

#### P1-2. 健康检查语义与安全边界不清：状态码恒 200、详细信息对外暴露且执行成本偏高

- 证据：`app/routes/health.py:59`（detailed 无鉴权）  
  证据：`app/routes/health.py:164`（unhealthy 仍返回 success response/200）  
  证据：`app/routes/health.py:285`（CPU 检查 interval=1，至少阻塞 1s）
- 影响：  
  - 最坏情况：LB/K8s 误判 ready，流量打进依赖已挂实例；同时对外泄露系统资源状态；健康检查本身拖慢实例。  
  - 最可能发生方式：DB/Redis 部分故障时仍返回 200；监控只看状态码。
- 根因：把“编排探针接口”和“诊断接口”混用，未定义访问控制与 SLA。
- 建议：  
  - 短期止血（1~3 天）：拆分 `live`（不查依赖）、`ready`（查 DB/Redis，不健康返回 503）、`detailed`（管理员权限+缓存+超时）；版本号用 `APP_VERSION` 而非硬编码。  
  - 中期重构（1~2 周）：引入依赖探测指标（DB ping latency、Redis ping latency）与 scheduler 健康信号。  
  - 长期演进（可选）：统一健康/指标端点并接入 Grafana/Prometheus。
- 验证：断开 DB/Redis 时 ready 返回 503；detailed 未授权访问被拒绝；默认健康检查耗时 <100ms。

#### P1-3. 文档/脚本/Compose 的“部署真相”漂移，导致 Runbook 不可用

- 证据：`docs/deployment/PRODUCTION_DEPLOYMENT.md:63`（DATABASE_URL=postgresql:// 示例）  
  证据：`docs/deployment/PRODUCTION_DEPLOYMENT.md:64`（使用 REDIS_URL，但当前实际为 CACHE_REDIS_URL）  
  证据：`docker-compose.prod.yml:95`、`docker-compose.prod.yml:97`  
  证据：`scripts/validate_env.sh:105`
- 影响：  
  - 最坏情况：故障时按文档操作导致二次事故；新环境无法按说明部署。  
  - 最可能发生方式：你半年后回看文档按图操作直接踩坑。
- 根因：缺少“文档即代码”的校验流程，配置变更未同步文档/脚本。
- 建议：  
  - 短期止血（1~3 天）：以 `docs/deployment/ENVIRONMENT_VARIABLES.md` 为 SSOT，同步修正 `PRODUCTION_DEPLOYMENT.md` 的变量名与组件拓扑示例。  
  - 中期重构（1~2 周）：增加“文档漂移检测”门禁（settings schema ↔ 文档表格）。  
  - 长期演进（可选）：从 settings schema 自动生成示例 env 与部署校验器。
- 验证：全新机器严格按文档可完成部署；CI 可检测变量名漂移。

#### P1-4. Scheduler 强依赖本地文件系统与 import 期副作用，与“无持久卷”组合会导致任务状态丢失

- 证据：`app/scheduler.py:16`（平台强依赖 fcntl）  
  证据：`app/scheduler.py:129`（jobstore 使用本地 sqlite）  
  证据：`app/scheduler.py:313`（import 即创建全局 scheduler）  
  证据：`docker-compose.prod.yml:105`（userdata 持久卷已移除）
- 影响：  
  - 最坏情况：容器重建后任务状态丢失（暂停/自定义配置被抹平）；受限文件系统下 import 失败导致服务不可用。  
  - 最可能发生方式：升级/重启后“任务配置回到默认”，但站点表面正常（隐性漏跑）。
- 根因：把调度状态放在本地 sqlite+目录副作用，且未将 jobstore 可靠性与部署拓扑绑定。
- 建议：  
  - 短期止血（1~3 天）：恢复 userdata 持久卷或把 jobstore 迁到 Postgres；把 scheduler 初始化改为显式（避免 import 副作用）。  
  - 中期重构（1~2 周）：web/scheduler 解耦为独立进程，并加入幂等/去重与告警。  
  - 长期演进（可选）：升级为专业任务队列（Celery/RQ/Arq）。
- 验证：容器重建后任务配置仍保留；只读环境下 import 不再失败；scheduler 状态可观测。

#### P1-5. 认证模式混杂（Session + JWT）且存在契约 bug，增加攻击面与维护成本

- 证据：`app/routes/auth.py:383`（返回字段包含 user.email）  
  证据：`app/models/user.py:35`~`app/models/user.py:41`（User 模型未定义 email 字段）
- 影响：  
  - 最坏情况：对外 API 一旦被依赖就出现 500 与契约漂移；同时需要维护两套安全模型（cookie+CSRF 与 bearer token）。  
  - 最可能发生方式：前端/第三方调用 `/auth/api/me` 触发运行时错误。
- 根因：缺少 internal vs public API 的正式 ADR；JWT 路径缺少 DTO/测试护栏。
- 建议：  
  - 短期止血（1~3 天）：明确 JWT 是否启用；启用则修复 schema 并把 JWT API 迁到 `/api/v1/auth/*`；不启用则移除或 feature-flag。  
  - 中期重构（1~2 周）：为对外 API 引入 OpenAPI + DTO（pydantic/TypedDict）+ 集成测试。  
  - 长期演进（可选）：对外 API 服务化，与页面 API 解耦。
- 验证：`/auth/api/me` 字段集合稳定；新增字段必须伴随迁移与文档更新；集成测试覆盖。

#### P1-6. 容器日志策略与持久化策略冲突：关键日志写文件但 userdata 未持久化且不走 stdout

- 证据：`nginx/supervisor/whalefall-prod.conf:26`、`nginx/supervisor/whalefall-prod.conf:29`（stdout/stderr 写入 userdata）  
  证据：`nginx/gunicorn/gunicorn-prod.conf.py:28`、`nginx/gunicorn/gunicorn-prod.conf.py:29`（gunicorn access/error log 写文件）  
  证据：`docker-compose.prod.yml:105`（userdata 持久卷已移除）
- 影响：  
  - 最坏情况：事故后容器重启即丢关键日志；磁盘写满导致服务不可用；`docker logs` 无法排障。  
  - 最可能发生方式：运行一段时间后，排障只能依赖 DB 中的 unified_logs（且不含 nginx/gunicorn 访问日志）。
- 根因：传统文件日志与容器最佳实践（stdout）混用，且存储未持久化。
- 建议：  
  - 短期止血（1~3 天）：要么切到 stdout/stderr，要么恢复持久卷并加 logrotate；明确 unified_logs 的保留策略。  
  - 中期重构（1~2 周）：统一日志通道（JSON stdout + 集中采集），DB 仅存关键审计/摘要。  
  - 长期演进（可选）：补告警（错误率/任务失败率/磁盘水位）与 runbook。
- 验证：`docker logs` 可看到访问/错误日志；容器重建后日志仍可追溯；磁盘水位受控。

### P2

#### P2-1. HTTP 安全响应头缺失（CSP/HSTS/XFO/XCTO 等），形成默认不安全基线

- 证据：`nginx/sites-available/whalefall-prod:23`（仅 proxy 配置，无安全头）  
  证据：`app/constants/http_headers.py:80`、`app/constants/http_headers.py:81`（常量存在但未落地）
- 影响：  
  - 最坏情况：Clickjacking/XSS 风险放大（管理后台尤其敏感）。  
  - 最可能发生方式：第三方库或模板某处引入可控 HTML 时缺少 CSP 缓冲层。
- 根因：安全头未纳入部署基线，入口层（Nginx）未承担安全策略。
- 建议：  
  - 短期止血：先在 Nginx 加 `X-Frame-Options`、`X-Content-Type-Options`、`Referrer-Policy`；TLS 落地后启 HSTS；CSP 先 report-only 后 enforce。  
  - 中期重构：形成安全头基线 ADR，并与静态资源策略联动。  
  - 长期演进：配合前端依赖治理与模板审计。
- 验证：安全头扫描达标；CSP report 收敛后再 enforce。

#### P2-2. 版本信息与配置 SSOT 漂移：多个端点/模板硬编码版本号

- 证据：`app/routes/main.py:23`  
  证据：`app/routes/health.py:50`、`app/routes/health.py:102`  
  证据：`app/templates/base.html:221`  
  对比：`app/settings.py:142`（APP_VERSION 来自 env）
- 影响：  
  - 最坏情况：线上排障无法确认真实版本；灰度/回滚时信息误导。  
  - 最可能发生方式：发布后忘记更新某处硬编码。
- 根因：缺少“版本号单一来源（build metadata）”的硬约束与自动注入。
- 建议：  
  - 短期止血：统一使用 `current_app.config["APP_VERSION"]`（或 Settings 注入）渲染与返回；构建时注入 git sha。  
  - 中期重构：把版本发布流程写入规范并做 CI 校验。  
  - 长期演进：提供 `/meta` 端点输出 build/schema/依赖信息。
- 验证：任一页面/health/app-info 返回同一版本；构建产物与环境注入一致。

#### P2-3. 前端 vendor 依赖手动内置，缺少供应链/回滚治理（版本清单/校验和/更新策略）

- 证据：`app/templates/base.html:229`、`app/templates/base.html:252`、`app/templates/base.html:267`
- 影响：  
  - 最坏情况：第三方漏洞无法快速定位与批量升级；手工替换引入“版本不一致/回滚困难”。  
  - 最可能发生方式：线上出现难复现 bug，定位发现是 vendor 文件被改但无版本记录。
- 根因：缺少依赖清单（版本/来源/校验和）与升级流程；无构建链路也缺少静态供应链治理。
- 建议：  
  - 短期止血：维护 vendor manifest（库名/版本/来源/sha256/引入点），新增 vendor 必须更新清单。  
  - 中期重构：逐步迁到 npm+锁文件+打包（Vite/rollup）减少手动 vendor。  
  - 长期演进：开启 SRI（若改 CDN）或构建产物签名。
- 验证：vendor 更新可追溯、可回滚；漏洞库可在清单中快速定位并升级。

## 最小可执行路线图（≤6 项，每项 1~3 天）

1. Secrets 基线：修正 `env.production` 为占位符模板并加 secret scanning 门禁；对既有环境执行密钥轮换 Runbook。  
2. 部署契约对齐：修复 redis healthcheck、DATABASE_URL 校验与 smoke test，使 `Makefile.prod` 链路可用。  
3. 凭据加密密钥策略：禁止密钥落日志；非 dev 缺失密钥 fail-fast；设计轮换兼容窗口。  
4. 日志导出权限：为 `/files/api/log-export` 增加权限与脱敏策略，并对导出行为做审计。  
5. request_id 贯通：新增 before_request/after_request 中间件，把 request_id 写入日志并回传响应头。  
6. 健康检查治理：拆分 live/ready/detailed，detailed 加权限与缓存，ready 不健康返回 503 并接入容器健康检查。

## 缺失的 ADR/规范待办（建议落到 `docs/architecture/adr/`）

> ADR 工作流参考：`docs/architecture/adr/README.md`  
> 待办清单：`docs/architecture/adr/ADR_BACKLOG.md`

- ADR-001：部署拓扑与进程模型（Gunicorn worker/并发、Nginx 同/分容器、扩容策略）  
- ADR-002：Scheduler 拓扑（是否独立进程、jobstore 选型、幂等/去重/补偿、告警信号）  
- ADR-003：Secrets 管理与轮换（哪些必须固定、如何注入、轮换步骤、禁止提交策略）  
- ADR-004：API 分区与版本化（internal vs public、认证方式、CSRF/CORS 对齐）  
- ADR-005：错误封套与兼容窗口（message/error 漂移治理、前端兜底移除计划与命中率监控）  
- ADR-006：健康检查语义（live/ready）与 SLO（依赖判定、超时、返回码）  
- ADR-007：日志策略（stdout/DB/文件、脱敏、保留、导出权限、审计）  
- ADR-008：外部依赖失败策略（timeout/retry/circuit-break、缓存降级、限流）  
- ADR-009：数据迁移策略（Alembic 规则、滚动发布兼容、回滚策略、schema 版本）  
- ADR-010：前端供应链治理（vendor manifest/校验和/升级与回滚；是否引入构建工具）

## 附录：防御/兼容/回退/适配逻辑（扫描命中）

> 说明：本附录聚焦 `or` / `||` / `get('new') or get('old')` / `fallback` 等“兼容与回退”信号。第三方库（`app/static/vendor/*`）不纳入扫描结论。

- 位置：`app/settings.py:152`  
  类型：回退/防御  
  描述：开发环境缺失 SECRET_KEY 时随机生成。  
  建议：保留 dev 体验但避免依赖“重启仍有效”；生产必须固定并通过 secret 注入。

- 位置：`app/settings.py:159`  
  类型：回退/防御  
  描述：开发环境缺失 JWT_SECRET_KEY 时随机生成。  
  建议：同上；并明确 JWT 是否启用的策略。

- 位置：`app/settings.py:177`  
  类型：兼容  
  描述：JWT 刷新 token 过期变量名兼容（新旧 env var 二选一）。  
  建议：给旧变量设弃用窗口并统计命中率，到期移除兜底。

- 位置：`app/settings.py:192`  
  类型：回退/兼容  
  描述：非 production 缺失 DATABASE_URL 时回退 SQLite。  
  建议：明确哪些环境允许回退；对 staging 建议禁止回退以贴近生产。

- 位置：`app/settings.py:220`  
  类型：回退/防御  
  描述：非 production 且 CACHE_TYPE=redis 缺 URL 时回退默认 redis://localhost。  
  建议：同样建议对 staging 禁止；并暴露“是否在用回退 URL”的指标/日志字段。

- 位置：`wsgi.py:13`  
  类型：兼容/回退  
  描述：gevent 为可选依赖，未安装则跳过 monkey patch。  
  建议：把 worker_class 与依赖绑定到部署 ADR，避免运行时“静默不同”。

- 位置：`app/__init__.py:118`  
  类型：防御/优雅降级  
  描述：scheduler 初始化失败不阻断 web 启动。  
  建议：生产建议 web/scheduler 解耦；否则要有显式告警（任务未运行属于 P0 信号）。

- 位置：`app/scheduler.py:84`  
  类型：适配/回退  
  描述：任务函数字符串路径 lazy import，避免循环依赖。  
  建议：提供集中注册与启动时校验（避免运行时才发现缺失函数）。

- 位置：`app/scheduler.py:404`  
  类型：防御  
  描述：ENABLE_SCHEDULER 可禁用调度器，默认 true。  
  建议：生产建议默认 false（由 scheduler worker 显式开启），减少误启动面。

- 位置：`app/utils/password_crypto_utils.py:51`  
  类型：回退（高风险）  
  描述：缺失 PASSWORD_ENCRYPTION_KEY 时生成临时密钥。  
  建议：除本机开发外应 fail-fast；严禁把密钥写入日志（见 P0-2）。

- 位置：`app/utils/rate_limiter.py:117`  
  类型：回退/防御  
  描述：缓存不可用时降级到内存限流。  
  建议：降级应伴随告警与指标；评估多实例下内存限流失效风险。

- 位置：`app/utils/logging/handlers.py:160`  
  类型：防御/回退  
  描述：日志 module 字段缺失时回退 logger 名称，再回退 "app"。  
  建议：推动业务日志显式填 module/action，并用 lint/门禁约束。

- 位置：`app/views/instance_forms.py:38`  
  类型：兼容  
  描述：view_args 支持 resource_id 或 instance_id 两种参数名。  
  建议：路由参数命名收敛，完成迁移后移除兜底并统计命中率。

- 位置：`app/routes/files.py:501`  
  类型：防御  
  描述：导出台账时 instance/capacity/sync_status 缺失则回退空对象。  
  建议：服务层输出结构固化为 TypedDict/DTO；缺字段要计数告警（结构漂移信号）。

- 位置：`app/tasks/accounts_sync_tasks.py:90`  
  类型：防御  
  描述：sync summary 读取 inventory/collection 时回退空对象。  
  建议：推进 SyncStagesSummary 强约束；生产统计兜底命中率并治理数据漂移。

- 位置：`app/static/js/core/http-u.js:221`  
  类型：兼容/回退  
  描述：错误消息解析兼容 message/error 字段。  
  建议：后端错误封套统一后，分阶段移除互兜底并统计旧字段命中率。

- 位置：`app/static/js/common/csrf-utils.js:69`  
  类型：兼容  
  描述：CSRF token 兼容 data.csrf_token 与 data.data.csrf_token 两种形态。  
  建议：后端固定一种响应结构并声明；命中另一种形态时打点告警。

