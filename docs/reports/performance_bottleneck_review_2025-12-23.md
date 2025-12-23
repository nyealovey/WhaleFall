# 性能评审与瓶颈定位方案（面向“页面打开慢/接口慢/同步慢/后台任务慢”）（2025-12-23）

> 说明（重要）：你尚未提供真实的 p50/p95/最大耗时与数据规模，本报告的“现象数据”将以 **待补充** 标记；但“证据（代码定位）”全部基于当前仓库实现，属于高概率瓶颈点，可直接用于设计排障与改造路线。

## 结论先行（基于代码结构的高概率瓶颈 Top5）

1) **权限同步存在 N+1（且带回退导致 2N 放大）**：每个账户在权限阶段会执行 1~2 次 `.first()` 查询，账户数上千时同步会显著变慢。  
   - 证据：`app/services/accounts_sync/permission_manager.py:223`、`app/services/accounts_sync/permission_manager.py:240`。

2) **Scheduler 与 Web 同进程启动，任务与请求争抢 DB/CPU，容易形成 p95/p99 尖刺**：WSGI 默认 `init_scheduler_on_start=True`，scheduler 虽有文件锁，但仍跑在某个 worker 内。  
   - 证据：`wsgi.py:25`、`app/__init__.py:118`、`app/scheduler.py:397`、`app/scheduler.py:429`。

3) **导出类接口使用 `query.all()` 全量拉取 + 内存拼接 CSV/JSON，且存在潜在 N+1**：数据一大就会拉爆响应时间与内存。  
   - 证据：`app/routes/files.py:340`、`app/routes/files.py:401`、`app/routes/files.py:548`、`app/routes/files.py:195`、`app/routes/files.py:428`。

4) **全站 base 模板默认加载大量通用 JS + 每页额外请求 app-info**：影响冷启动/弱网的首屏与交互就绪时间，并给慢请求排查引入噪声。  
   - 证据：`app/templates/base.html:237`、`app/templates/base.html:302`、`app/routes/main.py:15`。

5) **多处 `ILIKE '%term%'` 模糊搜索在数据量上来后趋向 Seq Scan**：实例列表、标签列表、账户列表等核心路径都包含该模式，需要索引或交互策略配合。  
   - 证据：`app/routes/instances/manage.py:135`、`app/routes/tags/manage.py:352`、`app/routes/instances/manage.py:780`、`app/routes/instances/detail.py:674`。

---

## I. 症状分型与我需要的最小补充信息

### 页面慢（前端感知慢：TTFB/LCP/JS/资源加载）
请你提供 5 个数据点（优先“最慢 3 个页面”）：
1) 最慢页面 Top3：URL + 是否必现/偶发 + p50/p95/最大（最好带时间范围）。  
2) 每页一份 Network HAR：关注文档请求 TTFB、总下载量、请求数、是否有 waterfall。  
3) 每页一份 Performance Trace 或 Lighthouse 报告：LCP/CLS/INP（或 Long Task 列表）。  
4) 页面关键数据规模：例如实例数、实例详情账户数、日志 24h 量级等。  
5) 冷缓存 vs 热缓存对比：二次打开的静态资源命中情况（304/强缓存/是否重复下载）。

### 同步慢（同步链路：外部依赖/批处理/事务/锁）
请你提供 5 个数据点（优先“最慢 3 个同步任务”）：
1) 最慢同步 Top3：任务名（或 job_id）+ 触发方式（手动/定时）+ p50/p95/最大 + 单次涉及实例数。  
2) 单次同步分段耗时：拉取(远端) / 转换(本地) / 写入(DB) / 提交(commit) / 后处理(聚合/缓存失效)。  
3) 远端依赖画像：DB 类型、网络 RTT、带宽、超时配置、单次拉取行数/对象数。  
4) 写入形态：逐行写入 vs bulk upsert、batch 大小、事务粒度（每条/每批/全量）。  
5) 并发与资源上限：是否与 scheduler/其他任务并跑、DB 连接池上限/实际占用、CPU/IO 曲线。

### API 慢（后端慢：业务/DB/IO/响应体）
请你提供 5 个数据点（优先“最慢 5 个 API”）：
1) 最慢 API Top5：方法+路径+关键 query/body 参数 + p50/p95/最大 + QPS（若有）。  
2) 响应体大小：Content-Length（或 gzip 后）+ items 数量（列表接口尤其重要）。  
3) DB 慢查询证据：`EXPLAIN (ANALYZE, BUFFERS)` 或 `pg_stat_statements` Top SQL（含 mean/p95/调用次数）。  
4) 应用侧证据：同一请求的 DB 查询次数、DB 总耗时、外部依赖总耗时（若现在没有，见 II 的最小闭环方案）。  
5) 并发相关性：慢是否集中在某些时间段（整点/凌晨任务/批处理窗口）。

---

## II. 观测最小闭环（建议新增/检查）

目标：不引入全量 APM，也能在 0.5~2 天内把“慢”拆成可证明的子问题，并能持续追踪 Top 慢接口/慢任务。

### 1) 日志字段与计时点（请求 + 任务）

#### HTTP 请求（建议落地位置）
- 优先落地在统一入口：`before_request/after_request`（当前仅有协议探测钩子：`app/__init__.py:156`）。  
- 对已使用 `safe_route_call` 的路由，可把“业务段计时”落在 wrapper 内（注意其在成功路径会 `db.session.commit()`：`app/utils/route_safety.py:146`）。

建议每条慢请求日志包含（结构化字段）：
- 身份与定位：`request_id`（透传 `X-Request-ID`，否则生成并回写响应头）、`method`、`path`、`endpoint`、`status_code`、`actor_id`（如可得）。  
- 核心耗时拆分（ms）：`total_ms`、`db_ms`、`db_queries`、`external_ms`、`render_ms`（HTML 页）、`serialize_ms`（JSON）。  
- 负载与规模：`response_bytes`、`items_count/rows_returned`、`page/limit`、关键业务维度（如 `instance_id/session_id`）。

计时点建议（最小可用）：
- t0：请求进入（before_request）  
- t1：视图返回前（建议 wrapper 或视图末尾）  
- t2：响应发送前（after_request）  
- DB：通过 SQLAlchemy event 聚合 `db_ms` 与 `db_queries`（建议按 request_id 聚合；慢请求可附 Top SQL 摘要的 hash/前缀）。  

#### 任务（APScheduler/后台线程）
建议每次任务至少输出两类日志：
1) summary（全量，必打）：`task_name/job_id/run_id`、`started_at/completed_at`、`duration_ms`、`instance_count`、`success_count/fail_count`、`db_ms/db_queries`、`external_ms`。  
2) stage（按阈值或全量）：`stage`（inventory/collection/persist/aggregate）、`batch_size`、`rows_in/rows_out`、`commit_ms`。

仓库现状提示（适合做“阶段拆分”的任务）：
- 账户同步串行遍历实例：`app/tasks/accounts_sync_tasks.py:180`、`app/tasks/accounts_sync_tasks.py:220`。  
- 容量采集串行遍历实例：`app/tasks/capacity_collection_tasks.py:458`、`app/tasks/capacity_collection_tasks.py:473`。

### 2) 慢阈值与采样策略（建议默认值）

#### HTTP
- 慢请求阈值：`total_ms >= 500ms` 全量记录；`>= 2s` 额外记录细分字段（例如 Top SQL hash、response_bytes、items_count）。  
- 采样策略：正常请求 1%（保趋势），慢请求 100%，关键路径（实例列表/详情、同步触发、导出）10%。

#### 任务
- summary：100%  
- stage：默认 100%（任务量通常不大）；若高频任务可降为 10%。  
- 批处理日志：仅在 `batch_ms >= 2s` 或 `rows >= 阈值` 时记录。

### 3) 必要的 DB 慢查询与索引检查手段（SQL/配置）

以 PostgreSQL 为例（staging 建议直接打开，prod 建议先灰度/采样）：
- `pg_stat_statements`：定位 Top SQL（按 total_time、mean_time、calls）。  
- `log_min_duration_statement`：staging 200ms 起，prod 可 500ms 起（配合采样/滚动）。  
- 对 Top SQL 执行：`EXPLAIN (ANALYZE, BUFFERS)`，重点看 Seq Scan、Sort/Hash 溢出、回表、锁等待。  
- 对 `ILIKE '%xx%'`：优先考虑 trigram/GiST/GIN（或调整交互为前缀匹配/分词检索）。  

---

## III. 慢点清单（按 P0/P1/P2）

> 说明：本节“现象数据”若你未提供，会标注为 **待补充**；建议先按 II 加观测后再决定最终优先级。

### P0

#### P0-1：同步慢（权限阶段）— 权限记录查找 N+1（且回退导致 2N 放大）
- 标题：`sync_accounts` 权限阶段随账户数线性放大，DB 查询次数过高
- 证据：
  - 每个远程账户都会调用 `_find_permission_record`：`app/services/accounts_sync/permission_manager.py:223`。
  - `_find_permission_record` 内部先 `.first()`，失败后再回退查询再 `.first()`，每账户 1~2 次查询：`app/services/accounts_sync/permission_manager.py:242`、`app/services/accounts_sync/permission_manager.py:245`。
  - 同步任务本身按实例串行执行（长尾更明显）：`app/tasks/accounts_sync_tasks.py:180`、`app/tasks/accounts_sync_tasks.py:220`。
  - 现象数据：待补充（建议补：同步总耗时、权限阶段耗时、账户数、db_queries/db_ms）。
- 瓶颈假设（按概率排序 3~5 条）：
  1) N+1 查询是主因：权限阶段 db_queries 与账户数成正比（甚至 2N）。  
  2) 回退路径命中率偏高（历史数据缺 `instance_account_id`），导致 2N 更常见。  
  3) 权限 JSON 字段 diff/归一化较重，CPU 与序列化开销叠加。  
  4) 与 scheduler/其他任务并发时，连接池争用导致 `pool_timeout` 等待放大（`app/settings.py:29`、`app/settings.py:478`）。  
- 需要的证据（如何采集）：
  - 任务内埋点：记录 `accounts_total`、`permission_lookup_queries`、`permission_stage_ms`、`db_queries/db_ms`、`fallback_hit`（见 IV）。  
  - DB 侧：抓取权限表相关 Top SQL（`pg_stat_statements`）并看 calls 与 mean_time。  
  - 对照实验：同一实例在账户数翻倍时，任务耗时是否近似翻倍（或更差）。  
- 修复建议：
  - 短期止血（0.5~2 天）：
    - 预加载映射：按实例一次性拉取 `AccountPermission`（按 `instance_account_id IN (...)` 或 `username IN (...)`），构建 map，循环内只做 O(1) 查找，避免 `.first()`。  
    - 加埋点统计回退命中率：`permission_record_lookup_fallback_hit`（见 IV），评估数据修复优先级。  
  - 中期重构（1~2 周）：
    - 把“查找 + 新建/更新 + 关联修复”改成批处理：分批 upsert/flush，减少 ORM 往返。  
    - 离线修复历史数据：补齐缺失的 `instance_account_id`（使回退路径趋近 0）。  
  - 长期治理（可选）：
    - 将权限同步阶段的核心 SQL 固化为可 explain 的查询，并引入“db_queries 上限告警”（例如每 1000 账户不超过 X 次 SQL）。  
- 验证：
  - 指标：`db_queries` 从 O(N) 降到 O(1~少量)，`permission_stage_ms` 随 N 增长的系数显著下降。  
  - 方法：同一实例、固定远端数据，改造前后对比任务总耗时与 DB calls；并对比高峰期 p95/p99 是否改善。

#### P0-2：偶发尖刺（p95/p99 抖动）— Scheduler 与 Web 同进程竞争资源
- 标题：任务运行窗口 Web 请求 p95/p99 抖动，表现为“页面偶发打开慢/接口偶发超时”
- 证据：
  - WSGI 入口默认启动 scheduler：`wsgi.py:25`。  
  - `create_app` 在启动时初始化 scheduler：`app/__init__.py:118`。  
  - scheduler 允许启动并在当前进程 `scheduler.start()`：`app/scheduler.py:397`、`app/scheduler.py:458`。  
  - 连接池上限默认不大（易被任务吃满）：`app/settings.py:29`、`app/settings.py:485`、`app/settings.py:486`。  
  - 现象数据：待补充（建议补：尖刺时间点、当时运行的任务、DB 活跃连接/等待、Web p95/p99）。
- 瓶颈假设（按概率排序 3~5 条）：
  1) 任务与请求共享同一进程/同一连接池，造成连接等待与 CPU 争用。  
  2) 任务在某个 worker 内运行，阻塞该 worker 的处理能力（尤其是 CPU 密集/大量 ORM 操作）。  
  3) 任务与请求同时访问热点表，产生锁等待或 buffer/IO 抢占。  
  4) 任务执行时日志量暴涨（或异常重试），进一步放大延迟与 IO。  
- 需要的证据（如何采集）：
  - 在 Web 慢请求日志中附上 `scheduler_running`/`job_id`（若可得）与 `db_pool_wait_ms`（若可观测）。  
  - 任务 summary 日志输出 `duration_ms/db_ms/db_queries`，并记录开始/结束时间用于与请求尖刺对齐。  
  - DB 侧抓：尖刺窗口的 active connections、锁等待、top sql。  
- 修复建议：
  - 短期止血（0.5~1 天）：
    - 生产/准生产先将 Web 进程禁用 scheduler：设置 `ENABLE_SCHEDULER=false`（`app/scheduler.py:404`），并在独立进程/容器跑 scheduler。  
    - 限制任务并发（线程池/实例级并行数）并为长任务加超时与分段 commit。  
  - 中期重构（1~2 周）：
    - 拆分部署形态：Web（只服务请求）+ Worker/Scheduler（只跑任务），避免共享资源池。  
    - 为任务单独配置 DB 连接池与隔离队列（避免挤占 Web 连接）。  
  - 长期治理（可选）：
    - 建立“任务运行窗口保护”：任务启动前/运行中动态降低 Web 复杂接口的并发或降级。  
- 验证：
  - 指标：任务窗口 Web p95/p99 波动收敛；DB 连接等待显著下降；尖刺超时比例下降。  
  - 方法：对比禁用 Web scheduler 前后同时间窗的请求分位数与 DB 指标。

#### P0-3：导出接口慢/卡死 — `query.all()` 全量拉取 + 内存拼接 + 潜在 N+1
- 标题：导出（账户/实例/日志）在数据量增大时变慢甚至超时，拖垮 worker
- 证据：
  - 账户导出：直接 `accounts = query.all()`：`app/routes/files.py:340`。  
  - 实例导出：直接 `instances = query.all()`：`app/routes/files.py:401`，并在循环内 `instance.tags.all()`：`app/routes/files.py:428`。  
  - 日志导出：直接 `logs = query.all()`：`app/routes/files.py:548`。  
  - 导出渲染中存在关系字段兼容分支：`instance.tags.all() if hasattr(...) else ...`：`app/routes/files.py:195`（易隐藏 N+1）。  
  - 现象数据：待补充（建议补：导出条数、响应大小、耗时、worker 超时/内存峰值）。
- 瓶颈假设（按概率排序 3~5 条）：
  1) 全量 `.all()` 导致 DB/网络/ORM 反序列化成本与数据规模线性增长。  
  2) CSV/JSON 构建在内存中完成，且一次性返回，导致内存峰值与 GC 开销明显。  
  3) 关系字段（tags/instance 等）触发 N+1 查询，进一步放大 db_queries。  
  4) 导出与其他请求并发时抢占连接池/CPU，拖慢全站。  
- 需要的证据（如何采集）：
  - 记录导出接口的 `rows/items_count`、`response_bytes`、`db_queries/db_ms`、`serialize_ms`。  
  - 采样导出 SQL 的 `EXPLAIN`，确认是否 Seq Scan、是否能用索引。  
  - 对比“只导出 1000 条 vs 10000 条”的耗时与内存曲线。  
- 修复建议：
  - 短期止血（0.5~2 天）：
    - 为导出加硬限制与强制筛选（例如默认时间窗/最大 1w 条），并在 UI 提示“请缩小范围”。  
    - 优先把导出改为 streaming（逐行 `yield`），避免一次性 `getvalue()` 进内存。  
  - 中期重构（1~2 周）：
    - 将导出改为异步任务：生成文件存储（本地/对象存储）→ 会话中心查看进度 → 下载。  
    - 对导出查询做 eager load 或 join（一次查回 tags），彻底消除 N+1。  
  - 长期治理（可选）：
    - 建立“导出链路专用限流与队列”，避免导出把在线 worker 打满。  
- 验证：
  - 指标：导出接口的 `response_bytes/rows` 可控；导出不再触发 worker 超时；全站 p95/p99 不受导出影响。  
  - 方法：同一筛选条件下，改造前后对比耗时与内存峰值；并在高并发下回归关键页面。

### P1

#### P1-1：页面首屏慢（冷启动更明显）— 全局脚本过重 + 每页 app-info 请求 + 静态资源未版本化
- 标题：全站 FCP/LCP/INP 受基础模板影响，首屏“交互就绪”偏晚
- 证据：
  - base 模板加载大量通用 vendor/common 脚本：`app/templates/base.html:237`。  
  - 每页 DOMReady 后额外请求 `/admin/api/app-info`：`app/templates/base.html:302`，接口返回常量：`app/routes/main.py:15`。  
  - 静态资源引用未显式版本化（`url_for('static', ...)` 无 `v=`），缓存策略不易激进。证据：`app/templates/base.html:238`。  
  - 现象数据：待补充（建议补：LCP/INP、请求数、总 JS 体积、二次打开缓存命中率）。
- 瓶颈假设（按概率排序 3~5 条）：
  1) 通用脚本加载与解析执行占用主线程，推迟交互就绪（INP/Long Task）。  
  2) `/admin/api/app-info` 形成噪声请求与瀑布链路（尤其在弱网/高延迟）。  
  3) 缓存不稳定导致重复下载（无版本号时不敢设长缓存）。  
- 需要的证据（如何采集）：
  - Lighthouse/Trace：Long Task、JS 执行、请求 waterfall。  
  - Network：静态资源是否强缓存命中、是否频繁 304、总下载量。  
- 修复建议：
  - 短期止血（0.5~1 天）：
    - 将 app_name/app_version 直接注入 HTML（无需请求），删除或缓存 `/admin/api/app-info`。  
    - 对非关键脚本加 `defer`（需核对依赖顺序），并确认页面入口仍可正常 mount。  
  - 中期重构（1~2 周）：
    - 以页面为单位梳理依赖：把仅少数页面用到的库迁移到 `extra_js`，减少全站常驻脚本。  
    - 静态资源版本化：在 `url_for` 增加版本参数（如 `v=APP_VERSION`）或构建 hash（配合长缓存）。  
  - 长期治理（可选）：
    - 建立“页面资源预算”（总 JS/CSS/请求数阈值），并在 CI 里做回归检测（Lighthouse CI 或脚本化采样）。  
- 验证：
  - 指标：请求数、总 JS 体积、LCP/INP、DOMContentLoaded/Load 时间下降。  
  - 方法：同页面冷/热缓存对比；改造前后 Lighthouse 分数与 Trace 对比。

#### P1-2：筛选/搜索慢 — `ILIKE '%term%'` 导致 Seq Scan（数据量上来后 p95 会崩）
- 标题：列表页搜索在大数据下不可控变慢（实例/标签/账户等）
- 证据：
  - 实例列表：`like_term = f\"%{filters.search}%\"` + 多列 `ilike`：`app/routes/instances/manage.py:135`。  
  - 标签列表：多列 `ilike(f\"%{search}%\")`：`app/routes/tags/manage.py:352`。  
  - 实例账户列表（Grid API）：`AccountPermission.username.ilike(f\"%{search}%\")`：`app/routes/instances/manage.py:780`。  
  - 容量查询的 inactive 分支同样 `ilike`：`app/routes/instances/detail.py:674`。  
  - 现象数据：待补充（建议补：这些接口在 search 非空时的 p95 与 rows scanned）。
- 瓶颈假设（按概率排序 3~5 条）：
  1) `%term%` 模糊匹配无法走 B-Tree，导致 Seq Scan 或大范围回表。  
  2) 过滤字段缺少复合索引（where/join/order by 不匹配）。  
  3) 用户输入词过短/高频导致匹配面过大，响应体也变大。  
- 需要的证据（如何采集）：
  - 对 search 场景抓 `EXPLAIN (ANALYZE, BUFFERS)`；记录 `rows`、`shared_blks_read/hit`。  
  - 记录 search 词长度分布与命中行数（便于决定“最小长度/前缀匹配”策略）。  
- 修复建议：
  - 短期止血（0.5~2 天）：
    - UI 限制搜索最小长度（例如 ≥2/3），并对空/短词提示“请输入更长关键词”。  
    - 将“包含匹配”降级为“前缀匹配”（`term%`）用于高频列表（需要 UX 确认）。  
  - 中期重构（1~2 周）：
    - PostgreSQL：为相关列加 trigram GIN/GiST（或全文检索），并建立查询白名单（只对必要列做 fuzzy）。  
    - 把常用过滤条件（db_type/status/tag）优先走索引，搜索作为二级过滤。  
  - 长期治理（可选）：
    - 建立“慢搜索榜单”与索引回归（每次 schema 变更回看 top SQL）。  
- 验证：
  - 指标：search 场景的 p95 降到目标阈值；`EXPLAIN` 从 Seq Scan → Index Scan；buffers/read 显著下降。  

#### P1-3：标签批量页慢 — 全量拉实例/标签 + 分配双循环（O(N*M)）+ 关系加载风险
- 标题：批量分配标签在实例数/标签数增长时耗时和 DB 压力飙升
- 证据：
  - 批量页 API：全量返回所有实例：`app/routes/tags/bulk.py:403`；全量返回所有标签：`app/routes/tags/bulk.py:427`。  
  - 分配逻辑双重循环，且用 `if tag not in instance.tags` 做 membership 判断：`app/routes/tags/bulk.py:88`、`app/routes/tags/bulk.py:91`。  
  - 现象数据：待补充（建议补：实例总数、标签总数、一次分配涉及数量、db_queries）。
- 瓶颈假设（按概率排序 3~5 条）：
  1) 全量 API payload 过大（instances/tags），前端渲染与网络成本高。  
  2) 分配是 O(N*M) 双循环，且 `instance.tags` 可能触发关系加载导致 N+1。  
  3) 批量写入是逐条 append，缺少 bulk 插入/冲突忽略，commit 成本高。  
- 需要的证据（如何采集）：
  - 记录一次批量分配的 `instances_count/tags_count/created_relations` 与 `db_queries/db_ms`。  
  - 对比“选 100 实例 x 10 标签”与“1000 x 50”的耗时曲线。  
- 修复建议：
  - 短期止血（0.5~2 天）：
    - 把 instances/tags API 改为分页 + 搜索（至少支持按 name/host 过滤），避免全量下发。  
    - 分配前一次性查出现有关系集合（association 表），循环内做 set 判断，避免 ORM 关系 membership。  
  - 中期重构（1~2 周）：
    - 使用 association 表 bulk insert（带冲突忽略/去重），按批次提交。  
    - 前端改“先筛选再选择”（减少可选集合），并给出预计写入数量与耗时预期。  
  - 长期治理（可选）：
    - 为批量操作建立统一“批处理基线”（最大 batch、超时、进度、可回滚/重试）。  
- 验证：
  - 指标：批量 API 响应体显著下降；分配耗时随规模增长更平缓；db_queries 不随 N*M 爆炸。  

#### P1-4：容量 latest_only（已窗口函数）仍可能慢 — 大历史 + 额外回退分支 + Python 排序
- 标题：容量查询在历史记录多/库名多时仍可能成为热点慢点
- 证据：
  - latest_only 使用窗口函数取 rn=1：`app/routes/instances/detail.py:627`、`app/routes/instances/detail.py:652`。  
  - include_inactive 场景会额外遍历 inactive 库并补 placeholder：`app/routes/instances/detail.py:665`、`app/routes/instances/detail.py:677`。  
  - 最终在 Python 侧排序与分页切片：`app/routes/instances/detail.py:704`、`app/routes/instances/detail.py:715`。  
  - 现象数据：待补充（建议补：history 行数、库名数、该接口 p95、rows scanned）。
- 瓶颈假设（按概率排序 3~5 条）：
  1) window 查询仍需扫描/排序大量历史（索引不匹配时），db_ms 高。  
  2) include_inactive 回退分支在库数量大时遍历成本高。  
  3) Python 排序在大集合下占用 CPU，且无法利用 DB 的 limit/offset 优化。  
- 需要的证据（如何采集）：
  - `EXPLAIN (ANALYZE, BUFFERS)` 看是否大 Sort/Seq Scan。  
  - 记录 `rows_fetched`、`unique_databases`、`include_inactive` 命中率。  
- 修复建议：
  - 短期止血（0.5~2 天）：
    - 给接口加默认时间窗（例如最近 7/30 天），并在 UI 允许扩大范围。  
    - 当 `include_inactive=true` 时改为分页加载或显式二次请求（避免默认把 inactive 全补齐）。  
  - 中期重构（1~2 周）：
    - 为查询补齐更匹配的索引（例如 instance_id + database_name + collected_date/collected_at 的组合或表达式索引）。  
    - 将排序/分页尽量下沉到 DB（减少 Python 排序与全量 materialize）。  
  - 长期治理（可选）：
    - 对容量类查询建立“行数上限/超时与降级”（例如返回“数据量过大请缩小范围”并提示策略）。  
- 验证：
  - 指标：rows_fetched 显著下降；接口 p95 下降；CPU 使用下降；include_inactive 场景仍可用。  

### P2

#### P2-1：`safe_route_call` 成功路径统一 `commit()`（含 GET）可能带来可见开销与排障盲区
- 标题：路由包装层隐藏事务边界，可能在高 QPS 下形成额外 DB 往返
- 证据：
  - wrapper 成功路径总是 `db.session.commit()`：`app/utils/route_safety.py:146`。  
  - 异常路径 rollback 并记录日志：`app/utils/route_safety.py:121`、`app/utils/route_safety.py:133`。  
  - 现象数据：待补充（建议补：高频 GET 的 db_ms、COMMIT 次数、是否存在长事务）。  
- 瓶颈假设（按概率排序 3~5 条）：
  1) 对纯读接口，commit/transaction 管理带来额外 DB 往返与锁持有时间。  
  2) 事务边界不透明，难定位“哪条 SQL 导致 commit 卡住/失败”。  
  3) 在任务与请求并发时，commit/rollback 频率增加放大连接池争用。  
- 需要的证据（如何采集）：
  - 在慢请求日志中记录 `db_commit_ms`（或至少区分业务 db_ms 与 commit db_ms）。  
  - 统计每分钟 commit/rollback 次数与慢 commit 比例。  
- 修复建议：
  - 短期止血（0.5~1 天）：
    - 先做观测：把 commit 计时打出来，确认它是否真是热点。  
  - 中期重构（1~2 周）：
    - 按路由类型区分事务策略：GET 默认 rollback/close，写接口才 commit；或统一用 after_request 的 session cleanup 策略。  
  - 长期治理（可选）：
    - 明确“事务基线”：哪些接口必须事务、哪些必须只读，并建立 code review checklist。  
- 验证：
  - 指标：高频读接口的 db_ms 与 total_ms 下降；慢 commit 次数下降；无数据一致性回归。

---

## IV. 防御/回退路径的性能风险清单

> 目标：找出“为了兼容/兜底导致重复工作”的路径，并给出“命中率埋点 → 收敛 → 移除”的策略。

| 位置（文件:行号） | 类型 | 描述（性能风险） | 建议（命中率/收敛/移除） |
|---|---|---|---|
| `app/services/accounts_sync/permission_manager.py:240` | 回退 | 先按 `instance_account_id` 查不到再回退按 `(instance_id, db_type, username)` 再查，导致每账户最多 2 次 DB 查询 | 加埋点 `permission_record_lookup_fallback_hit`（hit/total/instance）；离线修复缺失的 `instance_account_id`；改为一次性预加载 map 并移除 per-row `.first()` |
| `app/routes/instances/detail.py:665` | 回退 | `include_inactive` 场景额外遍历 inactive 库并补 placeholder，数据大时会放大 CPU/DB 成本 | 统计 `include_inactive` 命中率与耗时；默认不补齐 inactive，改为按需加载；对大实例做分页与上限 |
| `app/routes/files.py:195` | 兼容 | `instance.tags.all() if hasattr(...) else instance.tags` 在导出循环内使用，易隐藏关系加载与 N+1 | 统计导出接口的 `db_queries`；明确 relationship 类型并统一访问方式；必要时在导出 query 侧 join 预取 tags |
| `app/templates/base.html:286` | 适配 | 每页请求 `/admin/api/app-info`（常量接口），增加请求数与 waterfall 噪声 | 直接在模板注入 app_name/app_version；或对该接口做强缓存并记录失败率/耗时；长期移除该请求 |
| `app/routes/instances/manage.py:763` | 兼容/兜底 | `include_permissions` 分支返回大字段（server/database permissions），若被误用会造成 payload 暴涨 | 增加 payload_bytes/rows 指标并告警；把 include_permissions 改为权限详情专用接口，列表禁止带大字段 |

---

## V. 最小可执行修复路线图（最多 10 条）

> 每条行动项都包含：预计收益（影响范围）+ 风险 + 验证方式。建议按顺序落地（先打穿 p95/p99 最大路径）。

1) 建立“最小观测闭环”（HTTP + 任务）  
   - 预计收益：0.5~2 天内把慢拆分为 db/external/render/serialize/payload，避免盲修；影响全站排障效率。  
   - 风险：低（主要是日志量与字段治理）。  
   - 验证：能输出 Top 慢接口/慢任务榜单（含 p95/p99、db_ms、db_queries、response_bytes）。  

2) P0：权限同步去 N+1（预加载 AccountPermission 映射 + 移除 per-row `.first()`）  
   - 预计收益：同步任务耗时大幅下降，同时减少 DB 压力，降低线上尖刺。  
   - 风险：中（需谨慎处理历史数据与回退逻辑）。  
   - 验证：db_queries 从 O(N) 降为 O(1~少量)；权限阶段耗时随账户数增长的系数显著下降。  

3) P0：将 scheduler/重任务从 Web 进程隔离（staging/prod 优先）  
   - 预计收益：显著降低 p95/p99 抖动与超时；提高稳定性。  
   - 风险：中-高（部署形态调整、运维改动）。  
   - 验证：任务运行窗口 Web p95/p99 不再显著抖动；DB 连接等待显著下降。  

4) P0：导出链路改造（限额 + streaming 或异步导出）  
   - 预计收益：消除大数据导出拖垮 worker 的风险；导出体验可预期。  
   - 风险：中（涉及前端交互与文件交付方式）。  
   - 验证：导出不再触发超时/内存峰值；全站 p95/p99 不受导出影响。  

5) P1：搜索性能治理（先 UI 约束，再索引/检索升级）  
   - 预计收益：实例/标签/账户等核心列表搜索在大数据下仍可用。  
   - 风险：中（索引构建成本、交互语义变化）。  
   - 验证：search 场景 `EXPLAIN` 走索引；p95 达标；慢搜索 Top SQL 收敛。  

6) P1：base 模板“减重 + 去 app-info 请求 + 静态资源版本化”  
   - 预计收益：冷启动/弱网首屏更快；减少噪声请求，定位慢更清晰。  
   - 风险：中（全局依赖梳理与潜在回归）。  
   - 验证：请求数与总 JS 体积下降；LCP/INP 改善；二次打开强缓存命中提升。  

7) P1：标签批量页 API 分页化 + 分配逻辑批处理化  
   - 预计收益：批量功能在规模增长后仍可用；减少 DB 压力。  
   - 风险：中（前后端契约与交互调整）。  
   - 验证：批量 API payload 下降；分配 db_queries 不随 N*M 爆炸；耗时曲线更平滑。  

8) P1：同步/容量采集任务引入“实例级并行 + 分批提交”并设并发上限  
   - 预计收益：降低长尾耗时，提升吞吐；在不影响 Web 的前提下更快完成任务。  
   - 风险：中（并发引入连接池/锁竞争，需要严格上限与分段事务）。  
   - 验证：任务总耗时与长尾下降；DB 连接等待不升高；失败重试不放大。  

9) 建立 payload 上限与大响应告警（response_bytes/items_count）  
   - 预计收益：防止“接口慢 = 返回太多数据”反复出现；长期治理收益高。  
   - 风险：中（可能影响既有调用方，需要渐进灰度）。  
   - 验证：Top API 的平均 response_bytes 降到阈值内；前端解析/渲染更快。  

10) 建立“Top 慢点持续追踪”机制（每周/每次发布后回归）  
   - 预计收益：性能不再回退；能持续压 p95/p99。  
   - 风险：低。  
   - 验证：每周输出 Top10 慢接口/慢任务趋势（含 db/external/render 占比），并能定位到代码与 SQL。  

