# 性能评审与排障方案（以定位瓶颈为目标）- 2025-12-25

> 状态：Draft
> 负责人：WhaleFall Perf/SRE Audit
> 创建：2025-12-25
> 更新：2025-12-25
> 范围：`app/`（routes/services/tasks/models/utils/templates/static）、`nginx/`；重点链路：页面加载、列表页 API、同步/聚合、后台任务、日志检索
> 关联：`../standards/documentation-standards.md`；`../standards/backend/task-and-scheduler.md`；`../standards/backend/configuration-and-secrets.md`；`../standards/backend/api-response-envelope.md`；`../standards/backend/error-message-schema-unification.md`；`../standards/ui/README.md`

## I. 摘要结论（先给结论）

- **最可能的“第一瓶颈”在“请求链路里做了本应后台化/异步化的大工作”**：容量同步与聚合等操作在请求线程内执行（并返回大 payload），非常容易把 TTFB 拉到秒级甚至超时，并阻塞 gunicorn worker，形成“页面慢 / 接口慢 / 偶发尖刺”的共振（见 `app/routes/databases/capacity_sync.py:53`、`app/routes/capacity/aggregations.py:345`、`app/routes/accounts/sync.py:189`）。
- **最确定的“首屏感知慢”来自静态资源策略**：`base.html` 直接引用的图标资源体积异常（`favicon.png` 与 Apple touch icon 各约 1.6MB），且每页还会额外请求一次 `/admin/api/app-info` 形成 waterfall；这些会显著拖慢首次访问/弱网访问的 LCP/TTFB（见 `app/templates/base.html:13`、`app/templates/base.html:16` 与 `app/templates/base.html:305`；静态资源体积证据见 `docs/reports/artifacts/2025-12-25_performance-audit_static-assets.txt`）。
- **多个“列表页”存在可直接删除的同步 DB 工作**：账户台账与凭据管理页面在服务端执行分页查询/水合，但模板并不消费这批数据（页面实际依赖 Grid.js 再发 API 拉取），导致白白增加一次 DB 压力与 TTFB（见 `app/routes/accounts/ledgers.py:335` + `app/templates/accounts/ledgers.html:80`；`app/routes/credentials.py:411` + `app/templates/credentials/list.html:49`）。
- **排障结论优先级**：先止血 P0（异步化重任务 + 删掉无效 DB 查询 + 修正静态资源体积/请求数），再补齐 P1（日志检索 `%LIKE%`、大表清理策略、容量汇总 SQL 形态与批处理、观测闭环），最后做 P2（压缩、缓存治理与持续追踪）。

## II. 范围与方法

### 范围

- 前端感知性能：`app/templates/**`、`app/static/**`、`nginx/sites-available/**`
- 后端请求性能：`app/routes/**`、`app/services/**`、`app/repositories/**`
- 同步/后台任务性能：`app/tasks/**`、`app/scheduler.py`、`app/services/*sync*`、`app/services/aggregation/**`
- 数据库访问：SQLAlchemy Query 形态、分页/排序/过滤、批写入、清理任务
- 防御/兼容/回退/适配逻辑：重点扫描 `or` / `||` / `??` 兜底对性能与可观测性的影响

### A. 症状分型（以及我需要你补充的最小信息）

> 目标：把“慢”拆成可测量的子问题，并能把一次排障闭环跑通。

#### 页面慢（前端感知慢：TTFB/LCP/JS/资源加载）

请补充（每个慢页面至少 1 份，Top 3 即可）：
1) 最慢页面 URL（含 query）+ 是否需要登录 + 是否必现/偶发
2) Chrome DevTools Performance 录制（含 LCP/Long Task）或 Lighthouse 报告（移动/桌面分别）
3) Network HAR（Disable cache & Preserve log），并标注：TTFB、HTML 下载、关键资源（JS/CSS/图片）与总请求数
4) 客户端环境：设备/CPU、网络（有线/4G/弱网）、浏览器版本、是否走 CDN/反代
5) 首屏关键渲染依赖：是否必须等多个 API 返回才能渲染（waterfall 依赖图）

#### API 慢（接口慢/TTFB 高）

请补充（每个慢 API 至少 1 条样本，Top 5 即可）：
1) 路由（method + path）+ 典型参数（尤其是筛选/排序/分页）+ 返回 status
2) p50/p95/p99/最大耗时（最好 24h/7d 维度），以及是否与某个任务窗口重叠
3) 响应体大小（bytes）、items 数量、是否包含大字段（traceback/context/details/databases 等）
4) DB 侧证据：慢查询日志片段或 pg_stat_statements Top N（含 mean/max、rows、calls）
5) 单请求内 DB 查询次数/耗时拆分（若暂无，先按下文“观测最小闭环”加埋点）

#### 同步慢（同步/导入/聚合：外部依赖 + 批处理 + 事务/锁）

请补充（每个慢同步任务至少 1 次完整耗时拆分）：
1) 慢的同步动作名（按钮/接口/任务）：例如“同步容量/同步账户/当前周期聚合”
2) 单次耗时拆分：拉取(远端) / 转换(本地 CPU) / 写入(本地 DB) / 提交 / 后处理(聚合)
3) 数据规模：实例数、每实例数据库数、账户数、聚合涉及表的行数级别（估算即可）
4) 外部依赖拓扑：远端 DB 到应用的 RTT/带宽、连接超时配置、是否跨可用区/跨公网
5) 失败重试/重复触发情况：是否存在重复同步（多实例调度/多次点击）导致“看起来慢”

### B. 建立“性能观测最小闭环”（不要求全量 APM，先能定位）

#### 建议新增/检查的日志字段（请求/任务统一 schema）

- `request_id`（同时回写响应头 `X-Request-Id`，并贯穿任务/外部调用）
- `user_id`/`actor_id`、`route`/`endpoint`、`method`、`status_code`
- `duration_ms`（总耗时）
- `db_query_count`、`db_time_ms`、`db_rows`（可选：Top SQL hash）
- `external_time_ms`（按 `dependency` 维度：mysql/sqlserver/oracle/postgresql/redis/http 等）
- `payload_bytes`（响应体大小）、`items_count`
- `cache_hit`/`cache_key`（对 dashboard/选项类接口/统计类接口）
- 同步任务专用：`session_id`、`instance_id`、`stage`（inventory/collection/persist/aggregation）、`batch_size`、`batch_index`、`retry_count`

#### 建议计时点（t0/t1/…）

- Web 请求：t0=收到请求 → t1=鉴权/权限校验 → t2=service 开始 → t3=DB(总) → t4=外部依赖(总) → t5=序列化 → t6=响应返回
- 同步任务：t0=启动 → t1=远端连接 → t2=inventory 拉取 → t3=inventory 落库 → t4=capacity/permission 拉取 → t5=批写入(upsert) → t6=聚合/后处理 → t7=完成

#### 慢阈值与采样策略（先能定位）

- 请求慢日志：`duration_ms >= 500` 全量记录；`200~500ms` 10% 采样；其余 1% 采样
- DB 慢查询：优先启用（Postgres）`pg_stat_statements` + `log_min_duration_statement`（例如 200ms）；必要时加 `auto_explain`（只对慢查询）
- 任务慢日志：单实例阶段 `>= 30s` 全量；单次任务 `>= 5min` 全量；其余 5% 采样

### C. 按优先级排查（p95/p99 最大影响路径），并画出调用链

> 说明：由于未提供线上 p95/p99 数据，本节先以“代码结构上最可能放大延迟”的路径为优先级候选；拿到真实 Top N 后用同一模板替换为真实排名。

1) **首屏/页面打开慢（所有页面共用）**
   - 浏览器 → `GET <page>` → Flask `render_template` → HTML 返回（含 `base.html` 全局资源引用）→ 浏览器拉取 `/static/**` → 浏览器额外请求 `GET /admin/api/app-info`（见 `app/templates/base.html:305`）

2) **账户台账页面慢**
   - 浏览器 → `GET /accounts/ledgers` → `app/routes/accounts/ledgers.py:list_accounts` 执行分页查询+统计（但模板不消费列表数据）→ HTML 返回
   - 浏览器加载 Grid.js → `GET /accounts/api/ledgers` → `app/routes/accounts/ledgers.py:list_accounts_data` → `AccountsLedgerListService` → `AccountsLedgerRepository` → DB（见 `app/routes/accounts/ledgers.py:335`、`app/routes/accounts/ledgers.py:463`、`app/repositories/ledgers/accounts_ledger_repository.py:79`）

3) **凭据管理页面慢**
   - 浏览器 → `GET /credentials/` → `app/routes/credentials.py:index` 执行分页查询/水合（但模板不消费列表数据）→ HTML 返回
   - 浏览器加载 Grid.js → `GET /credentials/api/credentials` → `app/routes/credentials.py:list_credentials` → DB（见 `app/routes/credentials.py:411`、`app/routes/credentials.py:560`、`app/templates/credentials/list.html:49`）

4) **同步容量（用户点击）慢**
   - 浏览器 → `POST /databases/api/instances/<id>/sync-capacity` → `CapacitySyncCoordinator` 远端连接/拉取/写入 → 同步触发聚合 → 返回包含 `databases` 明细的大 JSON（见 `app/routes/databases/capacity_sync.py:53`、`app/routes/databases/capacity_sync.py:169`）

5) **当前周期聚合（用户点击）慢**
   - 浏览器 → `POST /capacity/api/aggregations/current` → `AggregationService.aggregate_current_period(...)`（同步执行）→ 返回结果（见 `app/routes/capacity/aggregations.py:302`、`app/routes/capacity/aggregations.py:345`）

### D. “瓶颈假设 → 证据 → 修复”表格（每个慢点至少 3 个假设，按概率排序）

> 读法：先用“最短验证方法”把假设证伪/证实；证实后再做“最小修复方案”；最后用“回归验证”固化。

| 慢点 | 概率排序的瓶颈假设 | 现有证据（代码/配置） | 需要采集的证据 | 最短验证方法 | 最小修复方案 | 回归验证 |
|---|---|---|---|---|---|---|
| 页面打开慢（全站） | H1：favicon/Apple touch icon 体积异常导致首屏资源下载被拖慢 | `app/templates/base.html:13`、`app/templates/base.html:16`；静态体积见 artifacts（favicon + touch icon 各约 1.6MB） | HAR：首屏资源 waterfall、LCP 资源是谁、缓存命中情况 | DevTools Network：Disable cache 看首次加载总下载量与关键资源 | 生成真正的 favicon/Touch icon（多尺寸、强压缩），替换大图；必要时改用 `.ico` | Lighthouse：LCP、总下载量下降；真实用户 p75 LCP 下降 |
| 页面打开慢（全站） | H2：`base.html` 全局脚本过多/阻塞导致 TTI/INP 差 | `app/templates/base.html:241`（全局加载 dayjs 多插件、tom-select 等） | Performance：Long Task、脚本执行耗时；Coverage：未使用 JS/CSS 比例 | DevTools Performance + Coverage | 按页面拆分依赖；`defer`/按需加载；去掉“全站必载”的非关键库 | INP/Long Task 数量下降；首屏可交互时间下降 |
| 页面打开慢（全站） | H3：每页额外请求 `/admin/api/app-info` 形成 waterfall | `app/templates/base.html:305` | HAR：该请求的 TTFB 与是否阻塞 UI；服务端耗时 | Network/Performance 标注该请求的关键路径 | 把 app_name/version 直接注入模板（或缓存 + ETag），减少每页一跳 | 首屏请求数减少 1；TTFB/LCP 更稳定 |
| 账户台账页面慢（TTFB） | H1：服务端执行了模板不消费的分页查询/分类查询 | `app/routes/accounts/ledgers.py:335`；模板仅渲染 Grid 容器 `app/templates/accounts/ledgers.html:80` | 请求耗时拆分：路由耗时、DB 次数与耗时 | 对该路由加临时计时日志（t0/t_db/t_render） | HTML 路由仅渲染 filter options；列表/统计走异步 API | `/accounts/ledgers` TTFB 显著下降；DB QPS 下降 |
| 账户台账页面慢（TTFB） | H2：`_calculate_account_stats` 多次 `count()` 造成额外 DB 压力 | `app/routes/accounts/ledgers.py:232`（多次 count） | pg_stat_statements：该路由触发的 count 频次与耗时 | 对比“移除 stats”前后路由耗时 | 把 stats 挪到专用 summary API 并缓存；或一次 SQL 聚合 | p95/p99 TTFB 下降；DB CPU 下降 |
| 账户台账页面慢（API） | H3：搜索/筛选使用 `%contains%`，缺少合适索引导致慢查询 | `app/repositories/ledgers/accounts_ledger_repository.py:79`（contains/search） | 慢查询计划、rows scanned、索引命中 | EXPLAIN ANALYZE（代表性 search） | 增加索引/改为前缀匹配/引入全文检索（按字段） | p95/p99 API 降低；rows scanned 降低 |
| 凭据管理页面慢（TTFB） | H1：服务端执行分页查询/水合但模板不展示列表 | `app/routes/credentials.py:411`；模板仅渲染 Grid 容器 `app/templates/credentials/list.html:49` | 路由耗时拆分、DB 次数与耗时 | 加临时计时日志/对比 | HTML 路由只准备 filter options；列表统一走 `/api/credentials` | `/credentials/` TTFB 显著下降 |
| 凭据管理页面慢（DB/API） | H2：筛选（含 tags）+ `group_by/count` 使查询更重 | `app/routes/credentials.py:260`（outerjoin + group_by） | EXPLAIN：索引命中、rows scanned；tags 过滤是否放大 | 对比无 tags/有 tags 的查询耗时 | 为 join/filter 补索引；必要时 tags 筛选改“两段式”（先查 credential_id 再 in） | p95/p99 API 降低；rows scanned 降低 |
| 凭据管理页面慢（治理） | H3：HTML 路由与列表 API 重复做同类计算（筛选项/统计/水合） | `app/routes/credentials.py:411` vs `app/routes/credentials.py:560` | 访问日志：HTML 与 API 调用次数与分布 | 对比“HTML 路由瘦身”前后 DB QPS | filter options 缓存 + HTML 路由瘦身 | DB QPS 下降；TTFB 更稳定 |
| 同步容量慢（用户点击） | H1：请求线程内做“远端拉取+本地写入+聚合”，阻塞 worker | `app/routes/databases/capacity_sync.py:53`、`:169`（同步执行） | 该接口 p95/p99；以及 worker 并发/队列堆积 | 压测/并发点击；观察 worker 响应与超时 | 改为“创建会话→入队/调度→返回 session_id”；前端轮询会话中心 | 同步动作不再阻塞请求；系统整体 p95 降低 |
| 同步容量慢（用户点击） | H2：返回 payload 含 `databases` 明细与 `inventory`，在数据库数多时巨大 | `app/routes/databases/capacity_sync.py:155`（返回 databases_data） | 响应体 bytes（按实例数据库数分布） | 记录 `payload_bytes`；对比数据库数多的实例 | 返回只包含 summary（count/total_size/session_id）；明细落库/分页查询 | 响应体显著缩小；TTFB 与网络时间下降 |
| 同步容量慢（本地 DB） | H3：汇总更新拉全量 `.all()` 再 sum，写入可能需要分批 | `app/services/database_sync/persistence.py:225`、`:42` | DB 执行时间、锁等待、内存峰值 | 对比“SQL 聚合/批 upsert”前后 | 用 SQL 聚合计算 total/database_count；upsert 分批（chunk 500~2000） | 任务耗时稳定下降；内存峰值下降 |
| 当前周期聚合慢（用户点击） | H1：聚合在请求线程同步执行，扫描数据量大 | `app/routes/capacity/aggregations.py:345` | 该接口 p95/p99；聚合涉及表行数/索引 | 压测 + EXPLAIN 代表性聚合 SQL | 改为异步任务（会话中心追踪）；必要时拆分 scope | 请求不再超时；聚合总耗时可控 |
| 当前周期聚合慢（写放大） | H2：进度回调写入同步记录过频导致 DB 写放大 | `app/routes/capacity/aggregations.py:342`（progress_callbacks） | 写入频率/写耗时/事务次数 | 统计单次聚合写入次数与耗时占比 | 对进度写入做节流（按批次/阈值写入）；合并事务 | DB 写放大降低；任务更稳定 |
| 当前周期聚合慢（资源争抢） | H3：与容量采集/清理等任务重叠导致锁与资源争抢 | `app/routes/databases/capacity_sync.py:143` + `app/scheduler.py:36` | 任务时间轴与锁等待（对齐 p95 尖刺） | 对齐任务窗口与请求延迟曲线 | 任务错峰/互斥（single-flight）；聚合与采集拆分执行 | p95 尖刺减少；锁等待下降 |
| 日志检索慢（API） | H1：`%LIKE%` + `cast(context as text)` 无法走索引导致全表/大范围扫描 | `app/repositories/history_logs_repository.py:38`、`app/repositories/history_logs_repository.py:42`、`app/repositories/history_logs_repository.py:43` | 慢查询 SQL、执行计划、rows scanned | pg_stat_statements Top SQL + EXPLAIN | 引入全文/三元组索引；限制搜索窗口；对 JSON 用 GIN/抽取字段 | p95/p99 降低；rows scanned 降低 |
| 日志检索慢（分页） | H2：`paginate()` 触发 `count()`，在大表/复杂过滤下昂贵 | `app/repositories/history_logs_repository.py:49`（paginate） | count SQL 耗时占比 | 对比“仅取 items”与“带 count”耗时 | 改为 keyset pagination；或延迟/近似 total | p95 降低；DB CPU 降低 |
| 日志检索慢（payload） | H3：列表返回 traceback/context 导致 payload 大且序列化慢 | `app/routes/history/restx_models.py:14`、`app/routes/history/restx_models.py:15`（traceback/context） | payload_bytes、序列化耗时占比 | 记录 payload_bytes 与响应耗时相关性 | 列表只返回概要字段；详情接口返回大字段 | payload_bytes 下降；响应更快 |
| 后台清理尖刺 | H1：大表 `DELETE` 一次性提交导致锁/IO/VACUUM 压力 | `app/tasks/log_cleanup_tasks.py:42` | 清理任务运行时 DB lock/IO、请求 p95 尖刺 | 对齐时间轴：任务开始/结束与请求延迟 | 分批删除（按 id/时间窗口）；或对日志表分区后 drop partition | 清理窗口内请求延迟更平滑；DB lock 降低 |
| 后台清理尖刺（膨胀） | H2：大批量 DELETE 触发表膨胀与 autovacuum 压力 | `app/tasks/log_cleanup_tasks.py:43` | bloat/autovacuum 指标、WAL/IO 峰值 | 观察清理后 vacuum 时间与查询抖动 | 分区/归档优先；批删 + 明确 vacuum 策略 | IO 峰值降低；查询更稳定 |
| 后台清理尖刺（连接池） | H3：任务与在线业务共用连接池导致请求排队 | `app/settings.py:544`、`app/settings.py:545`（max_overflow/pool_size） | pool checkout wait、连接占用 | 任务期间采集连接池等待 | 独立 worker/专用连接池/限流 | pool wait 下降；请求 p95 更平滑 |

### E. 最小可执行修复路线图（0.5~3 天/条）

- 已整理在 **IV. 建议与后续行动**（最多 10 条行动项，包含收益/风险/验证方式）。

### 性能检查维度（逐项，不跳过）

1) 前端感知性能（页面打开慢）
   - 已覆盖：静态资源体积与请求形态（P0-01）；需要你补充 HAR/LCP/Long Task 证据（见 II.A）。
2) 后端请求性能（接口慢/TTFB 高）
   - 已覆盖：同步重任务在请求内执行（P0-04/P0-05/P0-06）、列表页无效 DB 查询（P0-02/P0-03）；建议补齐 request timing/DB timing（II.B）。
3) 数据库性能（慢查询/同步慢）
   - 已覆盖：日志检索 `%LIKE%`（P1-01）、容量汇总全量 `.all()`（P1-03）；下一步用 EXPLAIN/pg_stat_statements 验证并补索引/改查询形态（II.B）。
4) 同步/后台任务性能（同步慢重点）
   - 已覆盖：同步容量/聚合/账户同步的执行方式与数据返回形态（P0-04/P0-05/P0-06），以及清理任务的锁/IO 风险（P1-02）；建议按阶段拆分耗时并记录 batch 统计（II.B）。
5) 缓存与加速策略（页面/接口/同步）
   - 已覆盖：建议对 filter options、stats、dashboard 等低频变化接口做短 TTL 缓存；并把缓存命中率纳入观测闭环（II.B）。
6) 可观测性与复现（性能排障关键）
   - 已覆盖：request_id/计时点/慢阈值与采样策略（II.B），并指出当前 request_id 未落地（P1-05）。
7) 防御/兼容/回退/适配逻辑对性能的影响（重点关注兜底）
   - 已覆盖：在 III 末尾给出“兜底路径清单”（含 `or/||`）与“命中率→收敛→移除”的治理建议。

## III. 发现清单（按 P0/P1/P2）

### P0

#### P0-01 静态资源体积与请求形态导致首屏慢（尤其首次访问/弱网）

- 证据（含现象数据）：
  - `app/templates/base.html:13`、`app/templates/base.html:16` 引用 `img/favicon.png`、`img/apple-touch-icon*.png`
  - `base.html` 引用的静态资源（未压缩体积）合计约 **5.55MB**，其中 **图片约 4.8MB**（主要由 favicon 与 Apple touch icon 贡献）；详见 `docs/reports/artifacts/2025-12-25_performance-audit_static-assets.txt`
  - `app/templates/base.html:305` 每页额外请求 `GET /admin/api/app-info`
- 瓶颈假设（按概率）：
  1) 图标体积异常 → 网络下载主导首屏
  2) 全局脚本加载与执行 → TTI/INP 变差
  3) `/admin/api/app-info` 增加 waterfall 与后端压力
- 需要的证据：
  - 真实慢页面 HAR（Disable cache），标注 LCP 对应资源与 waterfall
  - 首屏 `TTFB/LCP/INP`（Lighthouse/Performance 录制）
- 修复建议：
  - 用标准 favicon 方案替换大图（多尺寸 + 强压缩）；必要时使用 `.ico`；Apple touch icon 生成合理尺寸（通常 180x180）并压缩
  - 将 `base.html` 的全局依赖做“按页面加载”（至少把高频低用的库移出全站必载）
  - 把 app_name/version 直接注入模板或做强缓存（ETag/长缓存），避免每页 `GET /admin/api/app-info`
- 验证：
  - Lighthouse：Total Bytes、Requests、LCP 下降
  - 线上：首屏 p75 LCP、p95 TTFB 改善；静态资源命中率提升

#### P0-02 账户台账页面存在“无效 DB 查询”（模板不消费）导致 TTFB 变慢

- 证据（含现象数据）：
  - `app/routes/accounts/ledgers.py:335`、`app/routes/accounts/ledgers.py:342` 在 HTML 路径执行 `_build_paginated_accounts(...)` 与 `_calculate_account_stats()`（同步 DB 查询/统计）
  - `app/templates/accounts/ledgers.html:80` 页面实际仅渲染 Grid 容器 `#accounts-grid`，列表数据由 JS 通过 API 拉取
- 瓶颈假设（按概率）：
  1) 页面打开时多执行一次“分页查询+分类查询+统计 count”，白白增加 TTFB
  2) `_fetch_account_classifications` 走 `assignment.classification` 可能触发 N+1（见 `app/routes/accounts/ledgers.py:262`）
  3) `count()` 多次执行导致 DB 压力放大（见 `app/routes/accounts/ledgers.py:232`）
- 需要的证据：
  - `/accounts/ledgers` 路由耗时拆分（总耗时、DB 次数、DB 时间）
  - 与 `/accounts/api/ledgers` 的耗时对比（看是否“TTFB 慢但 API 正常”）
- 修复建议：
  - HTML 路由仅准备筛选项（instances/tag/classification options），删除分页查询与 stats 计算；stats 改走 API + 缓存
  - 若保留服务端 stats：合并 count 为单条聚合 SQL 或缓存 30~300s
- 验证：
  - `/accounts/ledgers` TTFB、p95 显著下降（通常可直接减少 1~N 次 DB 查询）
  - DB：该路由相关 SQL 调用次数下降

#### P0-03 凭据管理页面存在“无效 DB 查询/水合”（模板不消费）导致 TTFB 变慢

- 证据（含现象数据）：
  - `app/routes/credentials.py:411`、`app/routes/credentials.py:412` HTML 路径执行分页查询/水合（`paginate` + `_hydrate_credentials`）
  - `app/templates/credentials/list.html:49` 页面仅渲染 Grid 容器 `#credentials-grid`，未使用服务端传入的 `credentials`
- 瓶颈假设（按概率）：
  1) 无效分页查询/水合增加 TTFB 与 DB 压力
  2) 过滤选项构建包含 `get_active_tag_options()` 等，可能可缓存（见 `app/routes/credentials.py:375`）
  3) 真实列表 API 与 HTML 路径重复计算筛选项
- 需要的证据：
  - `/credentials/` 路由耗时拆分（总耗时、DB 次数、DB 时间）
- 修复建议：
  - HTML 路由仅渲染页面骨架与 filter options；列表完全走 `/api/credentials`
  - filter options 做短 TTL 缓存（30~300s），并提供“刷新缓存”入口（已有 cache 模块）
- 验证：
  - `/credentials/` p95/p99 TTFB 下降；DB QPS 下降

#### P0-04 同步容量接口在请求链路内执行重任务且返回大 payload，极易成为“同步慢/接口慢”源头

- 证据（含现象数据）：
  - 同步执行：`app/routes/databases/capacity_sync.py:53`（inventory + capacity 拉取 + 保存 + 触发聚合）
  - 触发聚合：`app/routes/databases/capacity_sync.py:143`
  - 返回明细：`app/routes/databases/capacity_sync.py:155`（返回 `databases` 明细 + `inventory`）
- 瓶颈假设（按概率）：
  1) 远端 DB 拉取慢（网络/权限/系统表扫描）导致整体慢
  2) 本地写入与汇总更新慢（批 upsert + `.all()` 聚合）
  3) 返回 payload 太大导致序列化/网络时间占比高
- 需要的证据：
  - 分段耗时：inventory 拉取/落库、capacity 拉取、upsert、聚合、响应序列化
  - payload bytes 与 database_count 分布（数据库数多的实例最容易爆）
- 修复建议：
  - 设计为异步：创建 `SyncSession` + `SyncInstanceRecord` 后立即返回 `session_id`；前端跳转“会话中心”追踪
  - 接口响应只返回 summary（count/total_size/session_id），明细通过分页 API 查看
  - 写入分批（chunk）；汇总用 SQL 聚合替代 `.all()` 拉全量
- 验证：
  - 该 POST 接口耗时从“分钟级/秒级”下降到“100~300ms 内返回 session_id”
  - 同期页面/接口 p95/p99 尖刺显著减少

#### P0-05 当前周期聚合接口同步执行聚合，容易超时并拖慢全站

- 证据（含现象数据）：
  - `app/routes/capacity/aggregations.py:345` 在请求线程内调用 `AggregationService.aggregate_current_period(...)`
- 瓶颈假设（按概率）：
  1) 聚合扫描数据量大（取决于 period/scope），同步执行导致超时
  2) 聚合过程中频繁写入会话进度（DB 写放大）
  3) 与其他任务（容量采集/清理）重叠导致锁与资源争抢
- 需要的证据：
  - 聚合 SQL 的执行计划与时间；聚合前后 DB locks/CPU
- 修复建议：
  - 改为异步任务：创建会话→入队→返回 session_id；页面只展示“已提交”
  - 对 scope 做并行/分片（实例级、数据库级拆分），避免单次扫全量
- 验证：
  - 请求不再出现超时；聚合的总耗时可控且可观测

#### P0-06 手动单实例账户同步接口可能返回超大 details 且成功判定存在兜底误判风险

- 证据（含现象数据）：
  - `app/services/accounts_sync/accounts_sync_service.py:198` 将 `summary` 写入 `result["details"]`（details 可能包含大量权限/库级信息）
  - `app/routes/accounts/sync.py:113` 使用 `pop("success", True)` 兜底，缺失字段可能被判定为成功
- 瓶颈假设（按概率）：
  1) 返回 details 导致 payload 过大（序列化/网络时间显著）
  2) 同步执行在请求线程内，远端权限拉取慢时会阻塞 worker
  3) success/status 兜底导致“失败显示成功”，用户重复点击放大压力
- 需要的证据：
  - 该接口响应体 bytes、耗时拆分（远端/本地/序列化）
  - success 兜底命中率（缺失字段比例）
- 修复建议：
  - 返回只包含统计字段（synced/added/modified/removed）与 `session_id`，details 落库/另页查看
  - success/status 由统一响应封套强约束（缺失即失败），并记录兜底命中率
- 验证：
  - 接口响应体显著缩小；重复点击减少；会话中心可追踪

### P1

#### P1-01 日志检索接口存在“难以走索引”的 `%LIKE%` 查询形态 + 返回 payload 过大

- 证据（含现象数据）：
  - `app/repositories/history_logs_repository.py:38` 模块筛选 `like("%...%")`
  - `app/repositories/history_logs_repository.py:42`、`app/repositories/history_logs_repository.py:43` 搜索 `message like("%...%") OR cast(context as text) like("%...%")`
  - `app/routes/history/restx_models.py:14`、`app/routes/history/restx_models.py:15` 列表返回 `traceback` 与 `context`
- 瓶颈假设（按概率）：
  1) `%LIKE%` 导致无法命中 B-Tree 索引，数据量大时必慢
  2) `cast(JSON as text)` 会放大 IO 与 CPU
  3) 列表返回大字段导致响应体大、序列化慢
- 需要的证据：
  - 慢查询 SQL、执行计划、rows scanned；以及日志表规模（行数/每天增量）
- 修复建议：
  - 先限制默认时间窗口/强制至少带时间过滤（已有默认 24h，可进一步收敛）
  - 针对 message：引入全文检索/三元组索引（Postgres `pg_trgm`）或将搜索改为前缀匹配
  - 列表接口只返回概要字段（不含 traceback/context），详情走 `/api/detail/<id>`
- 验证：
  - 搜索 p95/p99 降低；rows scanned 降低；payload bytes 降低

#### P1-02 清理任务对大表使用“一把梭 DELETE”可能引发锁与 IO 尖刺

- 证据（含现象数据）：
  - `app/tasks/log_cleanup_tasks.py:42` 对 `unified_logs` 直接 `DELETE`（30 天前全量）
  - `app/tasks/log_cleanup_tasks.py:47`、`:48` 同样对会话与记录表执行全量 `DELETE`
- 瓶颈假设（按概率）：
  1) 一次性 DELETE 造成长事务/锁/膨胀，触发 VACUUM 压力
  2) 清理窗口与高峰请求重叠导致 p95/p99 尖刺
  3) 删除量过大导致写放大（WAL/IO）影响其他查询
- 需要的证据：
  - 清理任务开始/结束时间轴与请求延迟尖刺对齐；DB 锁等待、WAL/IO 指标
- 修复建议：
  - 分批删除（按时间分段或按 id 游标）；或对日志表做分区后 drop partition（更“常数时间”）
  - 清理任务移到低峰窗口，并确保仅在专用 worker/单实例执行
- 验证：
  - 清理窗口内 p95 不再显著抬升；DB lock/IO 峰值降低

#### P1-03 容量写入/汇总存在可优化的“全量加载/单次巨型 upsert”形态

- 证据（含现象数据）：
  - `app/services/database_sync/persistence.py:42` 将容量数据 `list(data)` 全量加载并一次性 upsert
  - `app/services/database_sync/persistence.py:225` 汇总更新 `.all()` 拉全量再 sum
- 瓶颈假设（按概率）：
  1) 单实例数据库数多时，单次 upsert SQL 过大（解析/规划/网络/内存）
  2) `.all()` 拉全量导致内存与 Python CPU 浪费（本可 SQL 聚合）
  3) 多次 commit/事务切分导致额外开销与锁放大
- 需要的证据：
  - 单实例 database_count 分布；upsert 单次 records 数；DB 执行耗时
- 修复建议：
  - upsert 分批（chunk）+ 统一事务；汇总用 SQL `SUM/COUNT` 替代 `.all()`
  - 对热点查询加索引校验（instance_id + collected_date + is_active）
- 验证：
  - 单次容量同步耗时下降且更稳定；内存峰值下降

#### P1-04 任务在 web 进程内用线程执行（手动触发/调度）可能导致资源争抢与偶发尖刺

- 证据（含现象数据）：
  - 手动全量账户同步：`app/routes/accounts/sync.py:47` 使用 `threading.Thread` 执行任务
  - 手动运行调度任务：`app/routes/scheduler.py:410` 使用 `threading.Thread` 执行 job
  - 调度器通过文件锁控制“单进程运行”：`app/scheduler.py:1` 与 `app/scheduler.py:350`
- 瓶颈假设（按概率）：
  1) 任务与在线请求共享同一进程资源（CPU/连接池/网络），造成 p95 尖刺
  2) 多实例部署时文件锁只在单机生效，存在重复跑任务风险（导致“看起来慢”）
  3) 线程任务生命周期不可观测（worker 重启/回收导致丢任务或半执行）
- 需要的证据：
  - 任务开始/结束与请求 p95 尖刺对齐；进程/线程数、连接池占用、CPU 使用率
- 修复建议：
  - 明确拆分“web 服务”与“scheduler/worker”进程（通过 `ENABLE_SCHEDULER`），避免同进程抢资源
  - 手动触发任务统一走“创建会话→入队/调度→返回 session_id”，不要靠线程回调
- 验证：
  - 任务运行期间请求 p95/p99 更平滑；任务重复执行概率降低

#### P1-05 性能排障观测缺口：缺少 request_id/DB 耗时等最小闭环字段

- 证据（含现象数据）：
  - `app/utils/logging/context_vars.py:3` 定义了 `request_id_var`，但仓库内未发现 `request_id_var.set` 的调用（可用 `rg` 复核）
  - `app/utils/structlog_config.py:149` 读取 `request_id_var.get()` 写入日志字段
  - `app/__init__.py:191` 仅注册了协议探测钩子，无请求级 timing/trace 逻辑
- 瓶颈假设（按概率）：
  1) 无 request_id 导致“页面慢/接口慢/任务慢”无法串起来
  2) 无 DB 时间/次数导致无法区分“业务慢 vs DB 慢 vs 外部慢”
  3) 无采样策略导致日志要么不足以定位、要么过量影响性能
- 修复建议：
  - 增加 request middleware：生成 request_id、记录 t0/t1/t2…、注入响应头、慢日志采样
  - 增加 SQLAlchemy hooks 统计 `db_time_ms/db_query_count`
- 验证：
  - 任何一次慢请求都能在日志里定位到具体 route + request_id + db/external 占比

### P2

#### P2-01 Nginx 未启用 gzip/brotli（文本类资源可进一步降低传输时间）

- 证据：
  - `nginx/sites-available/whalefall-prod:1` 未配置 gzip/brotli（仅配置了静态缓存与 proxy buffering）
- 修复建议：
  - 启用 gzip（最小集合：`text/css`、`application/javascript`、`application/json`、`text/html`），并确保不压缩已压缩图片
- 验证：
  - 首次加载 transferred bytes 下降；弱网下 LCP/TTFB 更好

#### P2-02 `safe_route_call` 默认 commit（读接口可评估是否需要）

- 证据：
  - `app/utils/route_safety.py:146` 对所有成功路径执行 `db.session.commit()`
- 风险与建议：
  - 读接口频繁 commit 通常问题不大，但在高并发下仍有额外开销；可评估读接口改为 `rollback/remove_session`，写接口显式 commit（需统一改造，属于中长期治理）

### 防御/回退路径的性能风险清单（重点：or / || / ?? 兜底）

> 目标：为“兜底路径”加命中率统计，逐步收敛并删除；避免兜底导致重复查询/重复请求/误判成功，进而放大性能问题。

1) 位置：`app/utils/pagination_utils.py:74`  
   类型：兼容  
   描述：分页参数兼容 `page_size -> limit -> pageSize`，属于历史字段兜底。  
   建议：对 legacy_key 命中率做统计与告警；前端/调用方统一后移除 `pageSize/limit` 支持。

2) 位置：`app/routes/accounts/sync.py:113`  
   类型：防御/兼容  
   描述：`pop("success", True)` 缺失 success 字段时默认成功，可能导致失败被误判并重复触发（放大同步压力）。  
   建议：success 缺失即失败；记录“success 缺失”计数；收敛为统一响应封套字段。

3) 位置：`app/routes/capacity/aggregations.py:57`  
   类型：防御/回退  
   描述：`status = (result.get("status") or "completed").lower()`，缺失 status 时默认 completed。  
   建议：缺失 status 视为 failed；将聚合任务结果 schema 固化，并对缺失字段计数。

4) 位置：`app/routes/databases/capacity_sync.py:229`  
   类型：防御  
   描述：`(result or {}).get("message") or "实例容量同步失败"` 兜底错误消息，可能掩盖真实失败原因，增加重复触发。  
   建议：标准化错误结构（error_code + message + request_id），并在 UI 明确“去会话中心看详情”。

5) 位置：`app/services/database_sync/coordinator.py:182`  
   类型：兼容/适配  
   描述：`synchronize_database_inventory` 为旧调用名保留的委托。  
   建议：对旧入口调用计数；迁移任务/路由后删除旧别名，减少维护面与歧义。

6) 位置：`app/services/account_classification/classifiers/sqlserver_classifier.py:81`  
   类型：数据结构兼容  
   描述：规则字段 `database_privileges` 作为 `database_permissions` 的 legacy alias。  
   建议：在规则写入/管理端迁移字段并禁止新增旧字段；统计旧字段命中率并分阶段移除。

7) 位置：`app/services/accounts_sync/adapters/sqlserver_adapter.py:625`  
   类型：回退/适配  
   描述：SQL Server 权限同步先走 SID 路径，若结果为空则回退到“按用户名查询”，可能导致 **双倍远端查询成本**。  
   建议：记录 fallback 命中率与耗时占比；优先修复 SID 映射失败原因；必要时对 username 回退路径做缓存/限流。

8) 位置：`app/utils/data_validator.py:498`  
   类型：回退  
   描述：数据库类型动态配置读取失败时回退到静态白名单（保证可用性但可能隐藏配置问题）。  
   建议：把回退视为告警事件（计数 + 告警）；确保生产环境不应长期走回退路径。

9) 位置：`app/settings.py:179`  
   类型：兼容  
   描述：JWT refresh 过期时间环境变量兼容 `JWT_REFRESH_TOKEN_EXPIRES` 与 `JWT_REFRESH_TOKEN_EXPIRES_SECONDS`。  
   建议：统一环境变量命名；在非生产环境提示弃用并统计旧变量使用。

10) 位置：`app/config.py:1`  
    类型：兼容/回退  
    描述：保留 `app.config` 作为兼容入口，避免旧代码导入报错。  
    建议：全仓库搜索 `app.config` 引用并迁移；迁移完成后删除兼容层。

11) 位置：`app/static/js/core/http-u.js:221`  
    类型：兼容（契约漂移兜底）  
    描述：前端错误消息解析 `body.message || body.error || ...`，说明后端错误结构仍可能漂移。  
    建议：统一后端错误封套字段；前端统计 `message/error` 兜底命中率并逐步删兜底。

12) 位置：`app/static/js/modules/ui/danger-confirm.js:34`  
    类型：兼容（字段别名）  
    描述：`request_id || requestId` 双字段兜底，说明字段命名未统一。  
    建议：后端统一输出 `request_id`；前端统计 `requestId` 命中率，达到 0 后移除别名。

## IV. 建议与后续行动

### 最小可执行修复路线图（最多 10 条）

1) **修正 favicon/Apple touch icon 体积与格式**（0.5~1 天）  
   - 预计收益：首屏下载量显著下降，弱网 LCP/TTFB 改善（影响所有页面）。  
   - 风险：图标更新需注意缓存（`immutable`）与浏览器图标策略。  
   - 验证：Lighthouse（Total Bytes/Requests/LCP）；`/static/img/*icon*` 的 transferred bytes。

2) **移除 `base.html` 的每页 `/admin/api/app-info` 请求或做强缓存**（0.5~1 天）  
   - 预计收益：首屏请求数减少 1，减少 waterfall；后端压力降低。  
   - 风险：app_name 动态展示逻辑需确认是否必须实时变更。  
   - 验证：HAR 中请求数减少；页面标题/导航展示正确。

3) **账户台账 `/accounts/ledgers` HTML 路由删除无效分页查询与 stats 计算**（0.5~1 天）  
   - 预计收益：该页面 TTFB 下降、DB 压力下降。  
   - 风险：确认模板确实不依赖 `accounts/stats`（当前模板未引用）。  
   - 验证：对比修改前后 `/accounts/ledgers` 的 DB query count 与耗时。

4) **凭据管理 `/credentials/` HTML 路由删除无效分页查询/水合**（0.5~1 天）  
   - 预计收益：该页面 TTFB 与 DB 压力下降。  
   - 风险：确认 JSON 模式仍保留（`request.is_json` 路径）。  
   - 验证：对比修改前后 `/credentials/` 的耗时与 DB 次数。

5) **同步容量 `/databases/api/instances/<id>/sync-capacity` 改为异步会话任务 + 小响应**（1~3 天）  
   - 预计收益：同步动作不再阻塞请求线程，显著降低超时与全站尖刺；响应体显著缩小。  
   - 风险：需要前端改为“提交任务→去会话中心看进度”；需要任务幂等与重复触发保护。  
   - 验证：该接口返回时间 <300ms；会话中心可追踪；任务执行耗时可观测。

6) **当前周期聚合 `/capacity/api/aggregations/current` 改为异步会话任务**（1~2 天）  
   - 预计收益：避免同步聚合拖慢全站，减少超时。  
   - 风险：任务排队与并发控制要做好（避免重复跑）。  
   - 验证：接口快速返回 session_id；聚合结果在会话中心可追踪。

7) **手动单实例账户同步返回体瘦身（移除 details）并统一 success/status schema**（1~2 天）  
   - 预计收益：降低 payload 与阻塞时间；减少误判成功导致的重复点击压力。  
   - 风险：部分页面可能依赖 details 展示（需确认并迁移到“详情页/会话中心”）。  
   - 验证：响应体 bytes 下降；用户流程仍可看到结果。

8) **日志检索优化：减少大字段返回 + 改造搜索索引策略**（1~3 天）  
   - 预计收益：日志中心 p95/p99 降低，DB 压力降低。  
   - 风险：需要 DB 侧变更（索引/扩展）与查询语义调整。  
   - 验证：pg_stat_statements 该类 SQL mean/max 下降；搜索响应体 bytes 下降。

9) **清理任务改为分批/分区策略，避免锁与 IO 尖刺**（1~3 天）  
   - 预计收益：降低清理窗口对线上请求的影响。  
   - 风险：数据保留策略与分区策略需与运维确认；需要回滚预案。  
   - 验证：清理窗口内请求 p95 更平滑；DB 锁等待下降。

10) **补齐“性能观测最小闭环”**（1~3 天，分阶段落地）  
   - 预计收益：后续任何慢点都可用同一套字段快速定位（长期收益最高）。  
   - 风险：埋点/日志过量会反向影响性能，需要采样与阈值。  
   - 验证：慢请求日志包含 `request_id + duration_ms + db_time_ms + external_time_ms + payload_bytes`；可用 request_id 串起请求与任务。

## V. 证据与数据来源

### 代码与配置定位（抽样）

- 静态资源引用与额外请求：`app/templates/base.html:13`、`app/templates/base.html:16`、`app/templates/base.html:305`
- 账户台账无效分页查询：`app/routes/accounts/ledgers.py:335`、`app/routes/accounts/ledgers.py:342`、`app/templates/accounts/ledgers.html:80`
- 凭据管理无效分页查询：`app/routes/credentials.py:411`、`app/routes/credentials.py:412`、`app/templates/credentials/list.html:49`
- 同步容量接口：`app/routes/databases/capacity_sync.py:53`、`app/routes/databases/capacity_sync.py:169`
- 当前周期聚合接口：`app/routes/capacity/aggregations.py:302`、`app/routes/capacity/aggregations.py:345`
- 日志检索 LIKE 形态与大字段返回：`app/repositories/history_logs_repository.py:38`、`app/repositories/history_logs_repository.py:42`、`app/routes/history/restx_models.py:14`
- 清理任务：`app/tasks/log_cleanup_tasks.py:42`
- 容量持久化全量加载：`app/services/database_sync/persistence.py:42`、`app/services/database_sync/persistence.py:225`
- Nginx 静态缓存/未启用 gzip：`nginx/sites-available/whalefall-prod:15`

### 原始数据/产物（Artifacts）

- 静态资源体积与 `base.html` 引用汇总：`docs/reports/artifacts/2025-12-25_performance-audit_static-assets.txt`
