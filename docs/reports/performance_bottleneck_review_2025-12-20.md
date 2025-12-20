# 性能评审与瓶颈定位方案（面向“页面打开慢/接口慢/同步慢/后台任务慢”）

> 结论先行（基于代码结构的高概率瓶颈）  
> - **实例详情页**存在“全量账户列表 + 大表格服务端渲染”的典型慢点：后端 TTFB、响应体积、前端 DOM/JS 执行都会被放大。`app/routes/instances/detail.py:111`、`app/templates/instances/detail.html:254`。  
> - **实例容量接口（latest_only）**用“全量拉历史 + Python 去重”实现最新值，数据一多会直接变成全表扫描级别的慢点。`app/routes/instances/detail.py:590`。  
> - **账户同步权限阶段**存在明显 N+1 查询：每个账户至少 1 次、常见 2 次 DB 查询，账户数上千时同步会指数级变慢。`app/services/accounts_sync/permission_manager.py:196`。  
> - **调度任务与 Web 同进程竞争资源**是“偶发尖刺”常见根因：任务跑起来会抢 DB 连接/CPU，导致页面/接口 p95/p99 抖动。`app/scheduler.py:429`、`app/__init__.py:88`。

---

## I. 症状分型与我需要的最小补充信息（对应工作方法 A）

### 页面慢（前端感知慢：TTFB/LCP/JS/资源加载）
请你提供 5 个数据点（越精简越好，优先“最慢 3 个页面”）：
1) **最慢页面 Top3**：URL + 是否必现/偶发 + p50/p95/最大耗时（最好带日期范围）。  
2) **每页一份 Network HAR**（Chrome DevTools 导出即可）：关注文档请求 TTFB、总下载量、请求数、是否有串行 waterfall。  
3) **每页一张 Performance Trace 或 Lighthouse 报告**：LCP、CLS、INP（或交互卡顿点）、Long Task 列表。  
4) **页面关键数据规模**：例如实例详情页的账户数/数据库数，日志页的 24h 日志量级等。  
5) **静态资源命中情况**：首次 vs 二次打开的对比（是否大量 304/重新下载，是否被 Cache-Control 错配影响）。

### 同步慢（同步链路：外部依赖/批处理/事务/锁）
请你提供 5 个数据点（优先“最慢 3 个同步”）：
1) **最慢同步任务 Top3**：任务名/触发方式（手动/定时）+ p50/p95/最大 + 单次同步实例数。  
2) **单次同步分段耗时**：拉取(远端) / 转换(本地) / 写入(DB) / 提交(commit) / 后处理(聚合/缓存失效)。  
3) **远端依赖画像**：DB 类型、网络 RTT、带宽、超时配置、单次拉取行数/对象数。  
4) **写入形态**：逐行写入 vs bulk upsert、每批 batch 大小、事务粒度（每条/每批/全量）。  
5) **并发与资源上限**：调度器线程池大小、同一时间是否有多任务并跑、DB 连接池上限/实际占用、CPU/IO 曲线。

### API 慢（后端慢：业务/DB/IO/响应体）
请你提供 5 个数据点（优先“最慢 5 个 API”）：
1) **最慢 API Top5**：方法+路径+关键 query/body 参数 + p50/p95/最大 + QPS（如果有）。  
2) **响应体大小**：Content-Length（或 gzip 后大小）+ items 数量（列表接口尤其重要）。  
3) **DB 慢查询证据**：`EXPLAIN (ANALYZE, BUFFERS)` 或 `pg_stat_statements` Top SQL（含 mean/p95/调用次数）。  
4) **应用侧证据**：同一请求的 DB 查询次数、DB 总耗时、外部依赖总耗时（如果现在没有，见 II 的最小闭环方案）。  
5) **是否与定时任务/同步并发相关**：慢是否集中在某些时间段（例如整点/凌晨聚合任务）。

### 后台任务慢（非同步类后台任务/聚合/清理）
请你提供 5 个数据点：
1) **最慢后台任务 Top3**：job_id/任务名 + 触发频率 + p50/p95/最大 + 最近一次开始/结束时间。  
2) **任务执行环境**：是否与 Web 同进程、线程池/进程数、是否多实例重复跑。  
3) **任务内部阶段拆分**：读/算/写/commit 的耗时与规模（rows/batch）。  
4) **任务对线上影响**：任务运行窗口 Web p95/p99 是否抖动、DB 连接等待/锁等待是否上升。  
5) **失败重试/补偿策略**：是否会放大（失败后全量重跑、重复写入）。

### 偶发尖刺（p95/p99 突增、偶发超时）
请你提供 5 个数据点：
1) **尖刺时间点**：至少 3 次发生时间（精确到分钟）+ 持续时长。  
2) **尖刺期间的 Top 慢接口/慢任务**：对应路径与耗时。  
3) **系统资源**：CPU/load、IO wait、内存、DB 活跃连接、锁等待、Redis 命中率（若有）。  
4) **部署拓扑**：gunicorn worker 类型/数量、是否 gevent、是否启用 scheduler、是否有独立 worker。  
5) **外部依赖**：远端 DB/网络是否有抖动（RTT/丢包/超时）。

---

## II. 观测最小闭环（建议新增/检查）（对应工作方法 B）

目标：不引入全量 APM，也能在 1~2 天内把“慢”拆成可证明的子问题，并能持续追踪 Top 慢点。

### 1) 日志字段与计时点（请求 + 任务）

#### 请求（HTTP）统一字段（建议在 `before_request/after_request` 或统一包装中落地）
建议每条“慢请求日志”至少包含：
- `request_id`：优先从 `X-Request-ID` 透传，没有则生成（同时回写响应头）。  
- `trace_id`/`span_id`：若未来接入 OpenTelemetry，可预留字段。  
- `method`/`path`/`endpoint`/`route`/`status_code`。  
- `actor_id`（已有 `safe_route_call` 支持），外加 `tenant`/`instance_id` 等业务维度（按接口补充）。  
- **核心耗时拆分（ms）**：  
  - `total_ms`：请求总耗时（t_end - t_start）  
  - `db_ms`：SQLAlchemy 查询累计耗时  
  - `db_queries`：SQL 次数  
  - `external_ms`：外部依赖累计（远端 DB/HTTP）  
  - `render_ms`：模板渲染耗时（仅 HTML 页）  
  - `serialize_ms`：JSON 序列化耗时（仅 API）  
- **负载大小与规模**：`response_bytes`、`rows_returned/items_count`、`page/limit`、关键表行数（若易取）。  

计时点（t0/t1/…）建议：
- t0: 请求进入（before_request）  
- t1: 权限/鉴权结束（如果有）  
- t2: 业务逻辑结束（视图函数返回前）  
- t3: 响应发送前（after_request）  
- DB: 每条 SQL 记录 `query_ms` 并聚合到 `db_ms/db_queries`  

仓库现状提示：`safe_route_call` 只做异常模板，不含耗时。`app/utils/route_safety.py:76`。

#### 任务（APScheduler/后台线程）统一字段
建议每次任务执行输出 2 类日志：
1) **任务级 summary**（必打，全量，不采样）：
   - `job_id/task_name`、`trigger`（手动/定时）、`run_id`、`started_at/completed_at`、`duration_ms`
   - `session_id`（同步会话已有）、`instance_count`、`success_count/fail_count`
   - `db_ms/db_queries`、`external_ms`（同样聚合）
2) **分段 stage**（按阈值/采样）：
   - `stage`：如 `inventory`/`collection`/`persist`/`aggregate`
   - `batch_size`、`batch_index`、`rows_in/rows_out`、`commit_ms`

仓库现状提示：
- 账户同步任务顺序串行处理实例：`app/tasks/accounts_sync_tasks.py:220`。  
- APScheduler 与 Web 同进程：`app/__init__.py:88` + `app/scheduler.py:429`，容易形成“偶发尖刺”。

### 2) 慢阈值与采样策略（建议默认值）

#### HTTP
- **慢请求阈值**：`total_ms >= 500ms` 记录全量；`>= 2s` 额外记录 `debug` 级别细分（可包含 top SQL 摘要）。  
- **采样策略**：  
  - 正常请求：1% 采样（保留长期分位数趋势）  
  - 慢请求：100%  
  - 关键路径（dashboard、instances detail、sync 触发 API）：10% 或按 QPS 调整  

#### 同步/任务
- 任务 summary：100%  
- 分段 stage：默认 100%（任务量通常不大），或对高频任务降到 10%  
- 批处理日志：仅在 `batch_ms >= 2s` 或 `rows >= 阈值` 时记录

### 3) 必要的 DB 慢查询与索引检查手段（SQL/配置）

以 PostgreSQL 为例（dev/staging 建议直接打开，prod 先灰度/采样）：
- `pg_stat_statements`：定位 Top SQL（按 total_time、mean_time、calls）。  
- `log_min_duration_statement`：先设 200ms（staging），prod 可 500ms 起步。  
- 对 Top SQL 执行：`EXPLAIN (ANALYZE, BUFFERS)`，看是否 Seq Scan、排序/哈希聚合溢出、回表、IO 等。  
- 索引审计：对 where/join/order by 的组合列补齐复合索引；对 `ILIKE '%xx%'` 考虑 trigram/全文索引（或改交互避免模糊匹配）。  

### 4) 性能检查维度逐项清单（不跳过，便于对照落地）

1) 前端感知性能（页面打开慢）  
   - 仓库观察：`base.html` 全局加载较多 CSS/JS（`app/templates/base.html:19`、`app/templates/base.html:228`），实例详情账户表格一次性渲染大量 DOM（`app/templates/instances/detail.html:254`）。  
   - 你需要测量：TTFB/FCP/LCP/CLS/INP、请求数/总字节、Long Task、DOM 节点数。  
   - 快速优化方向：按需加载、`defer`、列表虚拟化/分页、减少首屏必需接口数（避免 waterfall）。  

2) 后端请求性能（接口慢/TTFB 高）  
   - 仓库观察：`safe_route_call` 缺少耗时与 DB 统计，难定位慢因（`app/utils/route_safety.py:76`）。  
   - 你需要测量：`total_ms/db_ms/db_queries/external_ms/render_ms/serialize_ms/response_bytes`。  
   - 快速优化方向：先补“可分解耗时”，再做分页/字段裁剪/缓存。  

3) 数据库性能（慢查询/同步慢）  
   - 仓库观察：latest_only 容量查询存在全量拉取历史（`app/routes/instances/detail.py:607`）；权限同步存在 N+1（`app/services/accounts_sync/permission_manager.py:242`）；日志搜索存在 `%term%`（`app/routes/history/logs.py:191`）。  
   - 你需要测量：Top SQL、执行计划、索引命中、锁等待。  
   - 快速优化方向：复合索引、窗口函数/DISTINCT ON、全文/GIN/trigram、减少 `.all()` 全量拉。  

4) 同步/后台任务性能（同步慢重点）  
   - 仓库观察：账户同步串行实例（`app/tasks/accounts_sync_tasks.py:220`），权限阶段 N+1；任务在 APScheduler 线程池内执行。  
   - 你需要测量：分段耗时、批次行数、commit_ms、外部依赖 RTT/超时。  
   - 快速优化方向：批处理/并发策略（按实例并行、按批 commit）、去 N+1、设置超时与限流。  

5) 缓存与加速策略（页面/接口/同步）  
   - 仓库观察：仪表盘有 `dashboard_cache`（`app/routes/dashboard.py:158`），但默认 `CACHE_TYPE=simple`（多进程下缓存不共享），且实例详情/容量接口缺少缓存。  
   - 你需要测量：缓存命中率（hit/miss）、缓存键基数、失效频率；确认是否多 worker 导致命中率偏低。  
   - 快速优化方向：  
     - 只读/低变化接口（字典、选项、汇总）优先缓存到 Redis（带 TTL）。  
     - 写路径触发失效（按 instance_id/scope）。  
     - 防止击穿：热点 key 加短期互斥/软过期。  

6) 可观测性与复现（性能排障关键）  
   - 仓库观察：结构化日志体系已存在，但缺少耗时拆分与 request_id 统一。  
   - 你需要落地：II 的“最小闭环”，并建立“慢阈值 + 采样策略”。  

7) 防御/兼容/回退对性能影响  
   - 仓库观察：权限同步存在“双查询回退”，容量 latest_only 存在“全量历史回退”，base 存在“每页额外请求 app-info”。详见 IV。  

---

## III. 慢点清单（按 P0/P1/P2）（对应工作方法 C + D）

> 说明：由于你尚未提供真实 p50/p95/最大，本节的“现象数据”以 **待补充** 标记；但“证据（代码定位）”基于仓库现状，属于高概率瓶颈。

### P0-1. 实例详情页（账户 Tab）打开慢：全量账户渲染 + 超大 DOM
- 标题：`GET /instances/<instance_id>` 页面 TTFB + LCP 慢（账户多时更明显）
- 证据：  
  - 路由一次性加载全部账户并组装大字典列表：`app/routes/instances/detail.py:111`（`get_accounts_by_instance` + `for sync_account in sync_accounts`）。  
  - 查询未分页，直接 `.all()`：`app/services/accounts_sync/account_query_service.py:28`。  
  - 模板对 `accounts` 全量循环渲染表格行：`app/templates/instances/detail.html:254`（`{% for account in accounts %}`）。  
  - 现象数据：待补充（建议补：文档请求 TTFB、HTML response bytes、账户数）。
- 调用链（必画）：  
  - 浏览器 → `GET /instances/<id>` → `instances_detail.detail()` → `get_accounts_by_instance()` → DB: `account_permission JOIN instance_accounts` → Python 构造 `accounts[]` → Jinja 渲染 `instances/detail.html`（N 行）→ 返回 HTML（大体积）→ 浏览器解析/布局/绘制（大 DOM，Long Task 风险）。
- 瓶颈假设（按概率排序，至少 3 条）：  
  1) **响应体积/DOM 规模过大**：账户多时 HTML 与 DOM 线性膨胀，导致 TTFB、下载、解析、渲染全慢。  
  2) **DB 查询 + 反序列化过重**：一次性拉取所有账户权限 JSON 字段，DB/网络/ORM 反序列化耗时大。  
  3) **后端 Python/Jinja 组装与渲染耗时**：循环构造 dict + 模板渲染占用 CPU。  
  4) **前端交互脚本对大表格做事件绑定/DOM 操作**（若有），引发 INP/长任务。  
  5) **与后台任务并发导致资源争抢**：同步/聚合跑起来时请求抖动（偶发尖刺）。
- 需要的证据（如何采集）：  
  - HAR：TTFB、HTML 大小、是否 gzip、静态资源命中率。  
  - 服务端：`total_ms/render_ms/db_ms/db_queries/response_bytes/accounts_count`（见 II）。  
  - DB：该查询的 `EXPLAIN (ANALYZE, BUFFERS)` + 实际返回行数。  
  - 前端：Performance Trace（DOM 节点数、Long Task、LCP 元素是谁）。  
- “瓶颈假设 → 证据 → 修复”表格（最短路径优先）：

| 假设(概率) | 证据(代码/现象) | 最短验证方法 | 最小修复方案 |
|---|---|---|---|
| 全量渲染导致 HTML/DOM 过大（高） | `detail.py` 全量 accounts + `detail.html` 全量循环 | 看 HTML response bytes、DOM 节点数、LCP/Long Task | 账户列表改为 **API 分页 + 前端虚拟列表/分页表格**，初次只渲染摘要 |
| 全量 `.all()` 拉取权限 JSON（高） | `account_query_service.py:33` | DB 执行计划 + rows + db_ms | 列表接口只取必要列（`with_entities`/DTO），权限详情改按需 `GET /permissions` |
| Jinja/Python 循环组装耗时（中） | `detail.py:120` 构造大 dict | 在视图内部加 `t_build_ms/t_render_ms` | 减少字段/减少循环；把统计下沉到 SQL（count/sum） |
| 同步任务并发争抢（中） | 同进程调度 + 大任务 | 对比任务运行时请求 p95/p99 | 将 scheduler/任务迁到独立 worker；限制并发/连接池隔离 |

- 修复建议：  
  - 短期止血（0.5~1.5 天）：  
    - 账户 Tab 默认只展示 **前 50/100**（或只展示摘要），其余“点击加载更多”。  
    - 列表不返回 `database_roles/database_permissions/server_permissions` 等大字段，详情弹窗再拉。  
  - 中期重构（1~3 天）：  
    - 账户列表改成 Grid.js/服务端分页（已有类似模式：`/instances/api/instances`），并做 **keyset pagination** 预留。  
    - 账号摘要（active/deleted/superuser）改 SQL 聚合，避免 Python 遍历。  
  - 长期治理（持续）：  
    - 建立“页面级 payload 上限”（例如 HTML < 300KB、JSON 列表 < 1MB）与自动告警。  
- 验证（如何证明变快）：  
  - 指标：TTFB/LCP/INP + `response_bytes` + `db_ms/db_queries`。  
  - 方法：同一实例（固定账户数）对比改动前后；首次与二次加载分别对比（缓存命中差异）。

### P0-2. 实例容量接口（latest_only）慢：全量拉历史 + Python 去重
- 标题：`GET /instances/api/databases/<id>/sizes?latest_only=true&include_inactive=true` p95 高
- 证据：  
  - `latest_only` 分支先按库名排序+日期倒序 **全量 `.all()`**：`app/routes/instances/detail.py:607`。  
  - 再用 Python `seen` 去重取“每库最新一条”：`app/routes/instances/detail.py:618`。  
  - 前端默认调用该接口（latest_only=true 且 include_inactive=true）：`app/static/js/modules/views/instances/detail.js:818`。  
  - 现象数据：待补充（建议补：该接口 p95、返回的 databases 数、历史天数）。
- 调用链：  
  - 浏览器 → 实例详情页加载后 `loadDatabaseSizes()` → `GET /instances/api/databases/<id>/sizes?...` → `_fetch_latest_database_sizes()` → DB: `database_size_stat OUTER JOIN instance_databases` **拉全量历史** → Python 去重/补齐 inactive → 返回 JSON → JS 排序/渲染。
- 瓶颈假设（按概率排序）：  
  1) **latest_only 实现导致扫描所有历史**：历史越久越慢，数据量与耗时近似线性增长。  
  2) **缺少支持排序/分组的复合索引**：`(instance_id, database_name, collected_date desc)` 不匹配会导致排序/回表重。  
  3) **include_inactive=true 触发额外查询与补齐逻辑**：inactive 表量大时二次扫描。  
  4) **返回列表过大 + 前端排序/渲染开销**：databases 数千时 INP/LCP 会受影响。  
- 需要的证据：  
  - DB：`EXPLAIN (ANALYZE, BUFFERS)` + 实际 rows（history 行数/每库天数）。  
  - 应用：记录 `rows_fetched`、`unique_db_count`、`db_ms`、`python_dedupe_ms`。  
  - 前端：该接口 response bytes + JS Long Task（排序/渲染）。
- “瓶颈假设 → 证据 → 修复”表格：

| 假设(概率) | 证据(代码/现象) | 最短验证方法 | 最小修复方案 |
|---|---|---|---|
| latest_only 扫描全量历史（高） | `detail.py:607` `.all()` + Python 去重 | 统计 rows_fetched 与耗时关系 | 用 SQL 获取“每库最新”：Postgres `DISTINCT ON` 或窗口函数 `row_number()` |
| 排序/过滤缺少复合索引（中-高） | order by name/date | `EXPLAIN` 看 Sort/Seq Scan | 增加复合索引 `(instance_id, database_name, collected_date DESC)` |
| include_inactive 补齐造成二次扫描（中） | `detail.py:630` 额外 query | 记录 inactive_count 与耗时 | 仅在 UI 需要时再拉 inactive；或一次 SQL 返回 active/inactive 状态 |

- 修复建议：  
  - 短期止血：  
    - 前端先改为 `include_inactive=false` 默认（或“显示已删除数据库”开关后再拉）。  
    - latest_only 接口加硬上限（例如最多返回 500/1000 个库），其余分页。  
  - 中期重构：  
    - latest_only 改 SQL：  
      - Postgres：`SELECT DISTINCT ON (database_name) ... ORDER BY database_name, collected_date DESC`  
      - 或：窗口函数 `row_number() over (partition by database_name order by collected_date desc)` 取 `rn=1`  
    - 同时把 `total_size_mb/active_count` 等聚合下沉到 SQL，减少 Python 循环。  
  - 长期治理：  
    - 为“最新容量”建立物化视图/汇总表（按 instance_id + database_name 一行），同步任务落库时顺便更新。  
- 验证：  
  - 指标：接口 `p95`、`rows_fetched`（应从“历史总行数”降到“数据库数”级别）、DB Sort 是否消失。  
  - 前端：渲染时间、INP/Long Task 下降。

### P0-3. 账户同步（权限阶段）慢：N+1 查询 + 双路径回退
- 标题：`sync_accounts`/权限阶段耗时随账户数暴涨
- 证据：  
  - 权限同步循环每个账户调用 `_find_permission_record`：`app/services/accounts_sync/permission_manager.py:196`。  
  - `_find_permission_record` 内部至少 1 次 `.first()`，缺关联时再来 1 次（双路径回退）：`app/services/accounts_sync/permission_manager.py:240`。  
  - 现象数据：待补充（建议补：单实例账户数、权限阶段耗时、DB queries 数）。
- 调用链：  
  - APScheduler/手动触发 → `app/tasks/accounts_sync_tasks.py:157` → `AccountSyncCoordinator.sync_all()` → `AccountPermissionManager.synchronize()` → for 每个 active account：查询权限记录 + diff + 写入变更日志 → commit。
- 瓶颈假设（按概率排序）：  
  1) **N+1 查询是主因**：账户数 N=5000 时，查询次数 5000~10000+，DB 时间爆炸。  
  2) **变更日志写入量巨大**：大量账号更新会插入大量 `account_change_log`，事务与索引维护变慢。  
  3) **diff/JSON 比较 CPU 重**：权限结构复杂时 Python diff 成为 CPU 热点。  
  4) **单事务过大**：commit 时 WAL/锁/索引更新集中爆发，影响 DB 与线上请求。  
- 需要的证据：  
  - 任务日志增加：`db_queries/db_ms/updated_count/created_count/log_rows/diff_ms/commit_ms`。  
  - DB：Top SQL（按 calls/total_time），确认是否大量重复 `SELECT ... WHERE instance_account_id=...`。  
  - 采样 1 次：`py-spy top`（或 cProfile）看 CPU 热点是否在 diff/JSON。  
- “瓶颈假设 → 证据 → 修复”表格：

| 假设(概率) | 证据(代码/现象) | 最短验证方法 | 最小修复方案 |
|---|---|---|---|
| N+1 查询（高） | `permission_manager.py:242` 在循环内 `.first()` | 记录 db_queries；pg_stat_statements 看同形 SQL calls | **预加载**：一次 query 拉出该 instance 的全部 AccountPermission，map 后 O(1) 查找 |
| 双路径回退导致 2N 查询（中-高） | `permission_manager.py:245` 第二次 `.first()` | 统计 fallback 命中率 | 数据修复：确保 `instance_account_id` 始终绑定；并用 bulk 回填一次性修正 |
| 变更日志写入量大（中） | 每次变更 `db.session.add(log)` | 统计 log_rows 与 commit_ms | 变更日志改 bulk insert；或仅记录摘要/采样；或异步写入 |

- 修复建议：  
  - 短期止血：  
    - 在权限阶段开头一次性拉取：  
      - `AccountPermission` by `instance_id` 或 `instance_account_id in (...)`  
      - 构建 `by_instance_account_id` / `by_username` 两个 map，替代 `_find_permission_record` 的 per-row 查询。  
    - 变更日志量大时：先只记录“变更计数摘要”，详细 diff 走按需开关或采样。  
  - 中期重构：  
    - 为权限快照引入 `permissions_fingerprint`（hash）字段：先比 hash，不同才做深 diff。  
    - 将权限同步拆批（batch），每批 commit，避免超大事务。  
  - 长期治理：  
    - 同步任务迁移到独立 worker（Celery/RQ），与 Web 资源隔离；并对单实例设置并发上限。  
- 验证：  
  - 同账户规模下：`db_queries` 从 O(N) 降到 O(1~几次)；权限阶段耗时应显著下降。  
  - 对线上：任务运行期间接口 p95/p99 不再明显抖动。

### P0-4. 偶发尖刺：同步/聚合任务与 Web 同进程争抢资源
- 标题：某些时间段页面/接口 p95/p99 突然抖动
- 证据：  
  - `create_app()` 默认启动 APScheduler：`app/__init__.py:88`。  
  - APScheduler 任务在同进程线程池执行：`app/scheduler.py:78`（ThreadPoolExecutor）+ `init_scheduler`。  
  - 账户同步任务本身串行且重：`app/tasks/accounts_sync_tasks.py:220`。  
  - 现象数据：待补充（建议补：抖动时间段与 scheduler job 执行时间对齐情况）。
- 调用链：  
  - Web 请求与 APScheduler job 并发 → 共享 CPU、DB 连接池、缓存后端 → Web latency spikes。
- 瓶颈假设（按概率排序）：  
  1) **DB 连接池被任务抢占**：Web 请求等待连接 → TTFB 上升。  
  2) **CPU 抢占**：任务 diff/渲染/序列化占 CPU → INP/请求耗时上升。  
  3) **DB 锁/长事务**：任务写入导致锁竞争 → 查询排队。  
- “瓶颈假设 → 证据 → 修复”表格：

| 假设(概率) | 证据(代码/现象) | 最短验证方法 | 最小修复方案 |
|---|---|---|---|
| 任务抢占 DB 连接（高） | scheduler 与 Web 同进程 + 重任务（见 P0-3） | 对齐任务窗口：Web 慢请求 + DB 活跃连接/等待连接数 | 拆分 worker；或给任务独立连接池/降低并发 |
| 任务 CPU 抢占（中-高） | 权限 diff/大循环/序列化等 CPU 热点 | 对齐任务窗口：CPU 利用率 + py-spy top | 限制任务并发；优化 diff；分批处理/分批提交 |
| 长事务/锁竞争（中） | 同步/聚合写入引发锁等待 | pg_locks/等待事件 + 慢查询 blocked | 缩短事务（batch commit）；避免大范围更新；调整索引/写入策略 |
- 需要的证据：  
  - 任务开始/结束日志 + Web 慢请求日志按时间对齐。  
  - DB：活跃连接数、waiting、锁等待。  
  - 机器：CPU、load、IO wait。  
- 修复建议：  
  - 短期止血：降低任务并发（线程池/单任务 max_instances）、给任务设置 off-peak 窗口、限制单次处理规模。  
  - 中期重构：把 scheduler/worker 从 Web 进程拆出来（独立容器/进程），DB 连接池隔离。  
  - 长期治理：接入任务队列（Celery/RQ）+ 可观测（队列长度、task latency、重试）。
- 验证：  
  - 对比任务运行窗口内外的 Web p95/p99；目标是“任务跑不影响在线请求”。

### P1-1. 日志中心检索慢：`LIKE '%term%'` + JSON cast
- 标题：`GET /history/logs/api/logs`（或类似）搜索慢
- 证据：  
  - 搜索对 message/context 做 `%term%`：`app/routes/history/logs.py:191`，对大表容易触发 Seq Scan。  
  - 默认限制 24h（有帮助）：`app/routes/history/logs.py:156`。  
  - 现象数据：待补充（建议补：24h 日志量、search_term 使用频率、p95）。
- 调用链：浏览器 → logs 页面 → API → DB 查询（LIKE + cast JSON）→ paginate。
- 瓶颈假设（按概率排序）：  
  1) **`LIKE '%term%'` + JSON cast 导致 Seq Scan**：日志量大时检索退化为全表扫描。  
  2) **时间窗口过大**：当 `hours`/start/end 放大到多天，扫描与排序成本飙升。  
  3) **payload 过大**：列表直接返回 `traceback/context` 等大字段，导致传输与序列化变慢。  
  4) **排序/分页形态不友好**：高 offset 深分页会越来越慢（若出现）。  
- 需要的证据（如何采集）：  
  - DB：Top SQL + `EXPLAIN (ANALYZE, BUFFERS)`（重点看 Seq Scan/Filter/Sort）。  
  - 应用：接口 `total_ms/db_ms/db_queries/response_bytes`，以及搜索条件（term 长度/是否空）。  
  - 数据规模：24h/7d 日志行数，context/traceback 平均大小。  
- “瓶颈假设 → 证据 → 修复”表格：

| 假设(概率) | 证据(代码/现象) | 最短验证方法 | 最小修复方案 |
|---|---|---|---|
| `%term%` 导致 Seq Scan（高） | `app/routes/history/logs.py:191` | `EXPLAIN` 看 Seq Scan/Sort | trigram(GIN) 或全文检索(tsvector)；或改交互为前缀/精确匹配 |
| 时间窗过大（中） | hours 可到 90 天 | 固定 term，对比 24h vs 7d/30d p95 | 强制默认更小窗口；大窗口要求 module/level 等强筛选 |
| payload 过大（中） | 列表返回 traceback/context | 看 `response_bytes/serialize_ms` | 列表默认不返回 traceback/context，全量详情按需拉取 |

- 修复建议：  
  - 短期止血：限制默认时间窗、限制返回字段（列表不带 traceback/context 全量）、对 search_term 强制最小长度。  
  - 中期重构：引入 trigram/全文索引，支持高效检索；module 筛选优先等值/枚举；深分页改 keyset。  
  - 长期治理：日志分区（按天/月）、冷热分层存储、建立“检索 SLA”与告警。  
- 验证：同一 search_term 与时间窗下对比：`EXPLAIN` 从 Seq Scan → Index Scan；接口 p95 达标。

### P1-2. 会话中心列表慢：先取 1000 再内存过滤/排序
- 标题：`GET /history/sessions/api/sessions` 在会话量增大后变慢
- 证据：  
  - `get_recent_sessions(1000)` 后在 Python 过滤/排序/分页：`app/routes/history/sessions.py:83`。  
- 调用链：浏览器 → 会话中心页面 → `GET /history/sessions/api/sessions` → `get_recent_sessions(1000)` → Python 过滤/排序 → Python 切片分页 → JSON 序列化返回。
- 瓶颈假设（按概率排序）：  
  1) **Python 过滤/排序/分页放大**：数据量增长后 CPU/内存线性上升。  
  2) **DB 明明更擅长过滤/排序/分页**：但当前把工作搬到应用层，导致整体更慢。  
  3) **列表 DTO 过大**：`to_dict()` 字段多，序列化与传输浪费。  
- 需要的证据（如何采集）：  
  - 应用：`total_ms/db_ms/serialize_ms/response_bytes` 与 sessions_total 的关系。  
  - DB：`get_recent_sessions` 的 SQL 执行计划与 rows。  
  - 前端：是否频繁刷新/轮询导致 QPS 放大。  
- “瓶颈假设 → 证据 → 修复”表格：

| 假设(概率) | 证据(代码/现象) | 最短验证方法 | 最小修复方案 |
|---|---|---|---|
| Python 过滤/排序占用 CPU（中） | `sessions.py:85` list filter/sort | 对比 sessions_total 与 `total_ms` | 过滤/排序/分页下沉 DB（limit/offset 或 keyset） |
| 取 1000 条固定窗口（中） | `get_recent_sessions(1000)` | 记录 db_ms 与 rows | 根据 page/limit 精确查询；只取必要列 |
| 序列化成本（低-中） | `to_dict()` 全量字段 | 记录 serialize_ms/bytes | 列表 DTO 精简字段；详情接口再拉全量 |

- 修复建议：  
  - 短期止血：降低默认取数；限制可选排序字段；列表字段精简；必要时加缓存（最近 1~5 分钟）。  
  - 中期重构：把筛选/排序/分页下沉到 DB；必要时加索引（`sync_category/status/started_at`）。  
  - 长期治理：会话表分区/归档；“最近窗口”在线检索，历史走离线报表。  
- 验证：随着会话量增长，接口 p95 保持稳定；CPU/内存不随 N 线性上升。

### P2-1. 全站基础资源加载偏重：base.html 全局注入多 CSS/JS
- 标题：首屏请求数/解析执行偏多，影响 FCP/LCP/INP
- 证据：  
  - base 全局 CSS：`app/templates/base.html:19` 到 `:39`（含页面专属 `privileges.css` 也全站加载）。  
  - base 全局 JS：`app/templates/base.html:228` 到 `:270`（多 vendor + 工具库）。  
  - 每页额外请求 `/admin/api/app-info`：`app/templates/base.html:289`（虽不阻塞首屏，但增加后端与网络噪声）。  
- 调用链：浏览器加载任意页面 → `base.html` 注入全局 CSS/JS → 浏览器下载/解析/执行 → 页面脚本再初始化（部分页面会额外发起 API 请求）。  
- 瓶颈假设（按概率排序）：  
  1) **请求数偏多**：冷启动/弱网下排队，导致 FCP/LCP 变差。  
  2) **JS 解析/执行成本偏高**：全站注入导致每页都付出主线程成本，影响 INP。  
  3) **关键/非关键资源未分层**：非关键资源过早加载占用带宽与主线程。  
  4) **缓存策略与版本化不匹配**：nginx prod `immutable` 若无文件名版本，会造成更新与缓存冲突。  
- 需要的证据（如何采集）：  
  - HAR：请求数、首屏关键资源耗时、是否阻塞渲染、是否大量 304。  
  - Trace：Long Task、脚本执行时间分布、LCP 元素与对应资源。  
  - 线上：静态资源命中率（cache hit）、版本发布后是否出现“旧资源仍被使用”。  
- “瓶颈假设 → 证据 → 修复”表格：

| 假设(概率) | 证据(代码/现象) | 最短验证方法 | 最小修复方案 |
|---|---|---|---|
| 请求数偏多（中-高） | base 全站引入多资源 | HAR 看请求数/关键路径 | 合并/打包；页面按需引入；移除不必要全局依赖 |
| 主线程被 JS 占用（中） | 多 vendor + 工具脚本 | Performance Trace 看 Long Task | 非关键脚本 `defer`；拆分并按页面加载；避免首屏执行重逻辑 |
| 缓存与版本化冲突（中） | nginx prod `immutable` | 对比新旧版本资源命中 | 静态资源加入版本 hash（文件名或 query param），再配合 immutable |

- 修复建议：  
  - 短期止血：移除每页 `/admin/api/app-info`（服务端注入）；把可延后脚本 `defer`；页面不需要的 CSS/JS 不要全站加载。  
  - 中期重构：打包与拆分（vendor/common/page chunk），并引入版本化策略（hash/manifest）。  
  - 长期治理：接入 Web Vitals 上报（LCP/INP/CLS/TTFB），建立前端性能预算与回归门禁。  
- 验证：Lighthouse/Trace 对比（请求数、JS 执行、Long Task、LCP/INP）；二次打开应基本命中缓存且无额外 API 噪声。

---

## IV. 防御/回退路径的性能风险清单（对应工作方法 7）

> 目标：找出“为了兼容/兜底导致重复工作”的路径，并给出“命中率埋点→收敛→移除”的路线。

1) 位置：`app/services/accounts_sync/permission_manager.py:240`  
   - 类型：回退（数据修复兼容）  
   - 描述：先按 `instance_account_id` 查不到则回退按 `(instance_id, db_type, username)` 再查，导致 **每账户最多 2 次 DB 查询**，在循环内形成 2N 放大。  
   - 建议：  
     - 加埋点：`permission_record_lookup_fallback_hit`（hit 次数/总数/instance）  
     - 先离线修复数据：补齐缺失的 `instance_account_id`  
     - 代码收敛：同步阶段只走一次预加载 map，彻底移除 per-row 查询与回退。

2) 位置：`app/routes/instances/detail.py:590`  
   - 类型：兼容/兜底（latest_only 实现方式）  
   - 描述：为拿“最新容量”回退到“全量历史拉取 + Python 去重”，数据越大越慢。  
   - 建议：用 DB 原生能力（`DISTINCT ON`/窗口函数）替代；并记录 `rows_fetched` 防止回归。

3) 位置：`app/templates/base.html:274`  
   - 类型：适配/兜底（动态拉 app-info）  
   - 描述：每页额外一次请求，失败走 console error；会放大“接口噪声”和慢请求排查成本。  
   - 建议：改为服务端注入（无需请求）；若保留则增加缓存与失败率统计。

---

## V. 最小可执行修复路线图（最多 10 条）（对应工作方法 E）

> 每条行动项都包含：预计收益（影响范围）+ 风险 + 验证方式。建议按顺序落地（先把 p95/p99 最大路径打穿）。

1) 为 HTTP/任务引入“最小闭环观测”（II 的字段与计时点）  
   - 预计收益：1~2 天内把“慢”精确拆分（db vs external vs render），避免盲修；影响全站排障效率。  
   - 风险：低（主要是日志量与字段治理）。  
   - 验证：能输出 Top 慢接口/慢任务榜单（p95/p99、db_ms、db_queries、response_bytes）。

2) P0：实例详情页账户列表“去全量渲染”（后端分页 + 前端按需加载）  
   - 预计收益：实例详情 TTFB/LCP 大幅下降（账户多时效果最明显）。  
   - 风险：中（前端交互与接口契约要调整）。  
   - 验证：同实例对比：HTML bytes 降到目标阈值；LCP/INP 改善；后端 render_ms 明显下降。

3) P0：容量 latest_only 改为 DB 取最新（DISTINCT ON/窗口函数）  
   - 预计收益：容量接口耗时从“历史总行数级别”降为“数据库数级别”；同步/页面容量区块显著提速。  
   - 风险：中（SQL 兼容与索引迁移）。  
   - 验证：rows_fetched 明显下降；`EXPLAIN` 不再出现大 Sort/Seq Scan；接口 p95 显著下降。

4) P0：权限同步去 N+1（预加载 AccountPermission + map 查找）  
   - 预计收益：同步任务耗时大幅下降；同时减少 DB 压力，降低线上尖刺。  
   - 风险：中（需要谨慎处理“缺 instance_account_id 的历史数据”）。  
   - 验证：db_queries 从 O(N) 降为 O(1~少量)；权限阶段耗时与账户数线性系数显著下降。

5) 将 scheduler/重任务从 Web 进程隔离（至少 staging/prod）  
   - 预计收益：消除“偶发尖刺”主因；提升线上稳定性。  
   - 风险：中-高（部署形态调整）。  
   - 验证：任务运行窗口 Web p95/p99 不再显著抖动；DB 连接等待显著下降。

6) 为大列表接口建立 payload 上限与分页基线（含 response_bytes 监控）  
   - 预计收益：防止“接口慢 = 数据返回太多”反复出现；长期治理收益高。  
   - 风险：中（可能影响依赖方/前端）。  
   - 验证：Top API 的平均 response_bytes 下降；前端解析与渲染时间下降。

7) 日志检索优化（全文/GIN/trigram + 时间窗收敛）  
   - 预计收益：日志中心搜索稳定可用；减少 DB 扫描。  
   - 风险：中（索引构建成本、迁移窗口）。  
   - 验证：search_term 场景 `EXPLAIN` 从 Seq Scan → Index Scan；p95 降到目标阈值。

8) 容量汇总/实例总量计算下沉到 SQL（避免 `.all()` 拉全量）  
   - 预计收益：降低内存与 DB 传输；为大实例场景做兜底。  
   - 风险：低-中。  
   - 验证：`update_instance_total_size` 类路径 rows/耗时下降，CPU 使用降低。

9) 前端首屏治理：base.html 按需加载、减少全局依赖、关键资源 `defer`/拆分  
   - 预计收益：FCP/LCP/INP 进一步改善（尤其弱网/冷缓存）。  
   - 风险：中（全局脚本依赖梳理）。  
   - 验证：Lighthouse/Trace 对比：请求数、JS 执行、Long Task 减少。

10) 建立“Top 慢点持续追踪”机制（周报/看板）  
   - 预计收益：性能不再回退；能持续压 p95/p99。  
   - 风险：低。  
   - 验证：每周输出 Top10 慢接口/慢任务（含变化趋势），并能定位到 db/external/render 的占比。
