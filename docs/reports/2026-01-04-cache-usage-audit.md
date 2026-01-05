# 缓存使用现状审计报告

> 状态: Draft
> 负责人: team
> 创建: 2026-01-04
> 更新: 2026-01-04
> 范围: Flask-Caching(Redis/simple), 业务缓存, 限流缓存, 前端内存缓存, Nginx 静态资源缓存
> 关联: `app/settings.py`, `app/__init__.py`, `app/utils/cache_utils.py`, `app/services/cache_service.py`, `app/utils/rate_limiter.py`, `nginx/sites-available/*`

## 摘要结论

- 项目缓存基座为 Flask-Caching, 支持 `CACHE_TYPE=simple/redis` (配置入口: `app/settings.py:192`, 初始化入口: `app/__init__.py:241`).
- 当前存在 2 套 Python 侧缓存封装: 通用装饰器缓存(`app/utils/cache_utils.py:251`)与业务缓存服务(`app/services/cache_service.py:28`). 两者在 TTL, key, 失效能力上语义不一致, 且对 Redis 后端能力(如 pattern delete)利用不足.
- 缓存失效能力存在 P0 级问题: "清缓存" API 的核心实现为 no-op 且返回成功, 会导致运维/用户以为已清理但实际未生效(`app/services/cache_service.py:91`, `app/api/v1/namespaces/cache.py:214`).
- 静态资源在 prod Nginx 配置中被设置为 `Cache-Control: public, immutable` 且 `expires 1y`, 但模板侧未见静态资源指纹/版本参数, 存在发布后客户端长期使用旧资源的高风险(`nginx/sites-available/whalefall-prod:15`).
- 限流使用缓存实现滑动窗口, 在 Redis 场景为非原子 read-modify-write, 并在异常时降级为进程内内存, 在多进程/多实例部署下可能出现限流不准与绕过风险(`app/utils/rate_limiter.py:130`).

## 范围与方法

### 范围

- 配置层: `CACHE_TYPE`, `CACHE_REDIS_URL`, `CACHE_DEFAULT_TIMEOUT` 等.
- 应用层: Flask-Caching 初始化, 业务服务与工具封装.
- 接口层: cache 管理 API, health 探活.
- 运行环境层: Nginx 对静态资源的缓存策略.
- 前端层: 页面级内存缓存(Map).

### 方法

- 通过代码检索与静态阅读, 梳理所有缓存相关入口: 初始化, 读写, key 构造, TTL, 失效, 降级/兜底分支.
- 对关键路径提取证据点(文件:行号), 并按 P0/P1/P2 分级给出风险与建议.

## 缓存使用清单(现状)

### 1) Flask-Caching 基座(配置 + 初始化)

- 位置: `app/settings.py:192`
  - 类型: 兼容/回退
  - 描述: 读取 `CACHE_TYPE` 与 `CACHE_REDIS_URL`. 当 `CACHE_TYPE=redis` 且非 production, 允许 `CACHE_REDIS_URL` 缺失时回退到 `redis://localhost:6379/0`.
  - 建议: 明确区分 "本地开发兜底" 与 "生产强校验". 同时核对 `CACHE_DEFAULT_TTL` 等 key 是否被 Flask-Caching 实际消费, 避免配置漂移.
- 位置: `app/__init__.py:241`
  - 类型: 适配
  - 描述: `cache.init_app(app)` 初始化 Flask-Caching 扩展, 后续依赖同一实例提供缓存能力.
  - 建议: 缓存封装层应以此实例为唯一基座, 避免并行存在多套 API 与语义.

### 2) 通用装饰器缓存(CacheManagerRegistry + @cached)

- 位置: `app/utils/cache_utils.py:224`
  - 类型: 适配
  - 描述: 通过 `CacheManagerRegistry` 存放全局 `CacheManager`, 以避免直接写全局变量.
  - 建议: 若继续保留, 建议明确生命周期(多 app 实例/测试场景)与线程安全语义.
- 位置: `app/utils/cache_utils.py:251`
  - 类型: 防御/回退
  - 描述: `cached()` 装饰器以 "缓存 miss 时执行函数" 的方式复用函数返回值.
  - 关键点: 以 `cached_value is not None` 判断命中(`app/utils/cache_utils.py:272`), 这会导致函数返回 `None` 时永远无法缓存, 形成 cache penetration.
  - 建议: 引入 sentinel 或显式区分 miss/hit, 使 `None` 可缓存.
- 位置: `app/services/dashboard/dashboard_overview_service.py:28`, `app/services/dashboard/dashboard_charts_service.py:16`
  - 类型: 缓存/性能
  - 描述: Dashboard 聚合数据使用 `@dashboard_cache(timeout=...)` 做短 TTL 缓存.
  - 建议: key 构造应使用归一化参数(例如 chart_type 的 lower 版本), 避免缓存碎片化(`app/services/dashboard/dashboard_charts_service.py:53`).

### 3) 业务缓存服务(CacheService)

- 位置: `app/services/cache_service.py:28`
  - 类型: 适配
  - 描述: `CacheService` 作为业务缓存 API, 承载 classification 规则缓存, 规则评估缓存, 以及 cache 管理接口.
  - 建议: 与 `cache_utils` 的职责边界需要明确, 否则会长期产生 TTL/key/失效能力漂移.

#### 3.1 分类规则缓存

- 位置: `app/services/cache_service.py:233`
  - 类型: 兼容
  - 描述: `get_classification_rules_cache()` 读取 `classification_rules:all`. 目前 set 侧写入为 dict(`rules`, `cached_at`, `count`), get 侧类型标注为 list, 上层通过兼容逻辑兜底(`app/services/account_classification/cache.py:29`).
  - 建议: 统一读写数据结构, 明确 schema/version 字段, 收敛兼容分支.
- 位置: `app/services/cache_service.py:344`
  - 类型: 兼容
  - 描述: `get_classification_rules_by_db_type_cache()` 同时兼容 dict 新格式与 list 旧格式(`app/services/cache_service.py:364`/`app/services/cache_service.py:372`).
  - 建议: 在缓存值中加入 `schema_version`, 并制定淘汰旧格式的时间点与清理动作.

#### 3.2 规则评估缓存

- 位置: `app/services/cache_service.py:144`
  - 类型: 缓存/性能
  - 描述: `rule_eval` 缓存 key 通过 SHA-256 哈希生成(`app/services/cache_service.py:64`), value 存储为 dict(包含 `cached_at`).
  - 建议: 若需要按 rule/account 批量失效, 当前哈希 key 会丢失可枚举信息, 需要额外的 "索引集合" 或 "明文前缀" 设计, 否则无法实现精确失效.

### 4) 限流缓存(RateLimiter)

- 位置: `app/utils/rate_limiter.py:130`
  - 类型: 防御/回退
  - 描述: 登录/重置密码限流在 cache 可用时写入 "窗口内时间戳列表", cache 异常时降级为进程内内存(`app/utils/rate_limiter.py:155`).
  - 风险: Redis 场景为非原子 get-modify-set, 并发下可能丢更新. 内存降级在多进程部署下不可共享, 存在绕过与不一致.
  - 建议: 使用 Redis 原子原语或 Lua 脚本实现滑动窗口/计数器, 并限制降级策略(例如只在 development 允许).

### 5) 探活缓存(health check)

- 位置: `app/services/health/health_checks_service.py:54`
  - 类型: 防御
  - 描述: 通过写入/读取固定 key `health_check` 做缓存探活.
  - 建议: 统一 health 探活逻辑与 key 前缀, 避免与业务 key 冲突, 并确保 TTL 足够短.

### 6) 前端内存缓存

- 位置: `app/static/js/modules/views/history/logs/logs.js:21`
  - 类型: 缓存/性能
  - 描述: 使用 `Map` 缓存当前日志列表的条目, 打开详情时优先命中, 否则请求详情接口(`app/static/js/modules/views/history/logs/logs.js:577`).
  - 建议: 明确 "列表 item 是否等同详情". 若详情字段更全, 命中缓存时也应补拉详情或标注为摘要, 避免展示不一致.

### 7) Nginx 静态资源缓存

- 位置: `nginx/sites-available/whalefall-prod:15`
  - 类型: 缓存/HTTP
  - 描述: `/static/` 使用 `expires 1y` + `Cache-Control: public, immutable`.
  - 风险: 若静态文件名未指纹化(例如 `app.js?v=...` 或 `app.<hash>.js`), 浏览器可能长期不更新资源, 导致发布后前端逻辑与后端接口不匹配.
  - 建议: 要么引入静态资源指纹化, 要么降低 TTL 并移除 `immutable`, 同时配合 ETag/Last-Modified.

## 发现清单(按优先级)

### P0

#### P0-1: 清缓存 API 返回成功但实际未失效

- 位置: `app/services/cache_service.py:91`, `app/services/cache_service.py:107`, `app/api/v1/namespaces/cache.py:102`, `app/api/v1/namespaces/cache.py:163`, `app/api/v1/namespaces/cache.py:214`
- 类型: 回退/防御
- 描述: `invalidate_user_cache()` 与 `invalidate_instance_cache()` 仅记录日志并固定返回 `True`, 但未执行任何删除. 上层 API 依据返回值展示 "清除成功".
- 影响: 运维与用户误判问题已处理, 实际缓存继续生效, 可能造成数据不一致或排障延迟.
- 建议:
  - Redis 后端: 提供真实失效实现(推荐 "索引集合 + 批量删除" 或 "可枚举前缀 + delete_pattern").
  - 非 Redis 后端: 明确返回 "not supported", 禁止 silent success.
  - API 层: 返回 "删除数量" 或 "是否实际执行", 并在响应中区分 no-op.

#### P0-2: prod 静态资源 immutable + 长 TTL 但缺少指纹化

- 位置: `nginx/sites-available/whalefall-prod:15`, `app/templates/*`(静态引用)
- 类型: 缓存/HTTP
- 描述: `/static/` 强缓存 1 年且 immutable, 但模板静态引用未见版本参数或指纹文件名(示例: `app/templates/credentials/list.html:10`).
- 影响: 新版本发布后浏览器继续使用旧 JS/CSS, 触发前后端不匹配, 造成页面异常且难以通过刷新修复(需清缓存/换浏览器).
- 建议: 落地静态资源指纹化或调整 Nginx 策略为短 TTL + 可复用缓存校验.

#### P0-3: 限流实现可被并发与部署拓扑影响

- 位置: `app/utils/rate_limiter.py:155`, `app/utils/rate_limiter.py:168`
- 类型: 防御/回退
- 描述: 缓存限流采用 get-modify-set, 不具备 Redis 原子性. 异常降级到内存会在多进程/多实例下造成不一致.
- 影响: 限流可能不准(误封或放行), 且降级路径可能被探测并绕过.
- 建议: 使用 Redis 原子实现, 并限制降级条件(例如仅 development 允许).

### P1

#### P1-1: 装饰器缓存无法缓存 None 返回值

- 位置: `app/utils/cache_utils.py:272`
- 类型: 兼容/回退
- 描述: 命中判断 `cached_value is not None` 导致 None 永远视为 miss.
- 影响: 特定函数在返回 None 场景会持续穿透, 造成重复计算与下游压力.
- 建议: 使用 sentinel 或将 miss/hit 区分为 tuple, 使 None 可缓存.

#### P1-2: 缓存封装层重复且语义漂移

- 位置: `app/utils/cache_utils.py:38`, `app/services/cache_service.py:28`, `app/__init__.py:244`
- 类型: 适配/可维护性
- 描述: 同一项目内存在 CacheManagerRegistry 与 cache_service 两套全局缓存封装, TTL 与 key 规则不统一, 且失效能力分散.
- 影响: 新功能接入缓存时容易选错入口, 导致一致性与失效策略不可控.
- 建议: 收敛到单一项目级缓存 helper, 明确 "key, TTL, 失效, 监控" 统一口径.

#### P1-3: 缓存 key 设计阻碍精确失效

- 位置: `app/services/cache_service.py:64`
- 类型: 适配
- 描述: 业务缓存 key 采用哈希隐藏了 instance_id/username 等维度, 使得按维度失效无法通过 pattern 完成.
- 影响: 只能全量清空或 no-op, 不利于运维与数据一致性.
- 建议: 引入可枚举前缀(例如 `whalefall:instance:{id}:user:{name}:...`)或维护反向索引集合.

#### P1-4: cache 管理接口统计口径不可靠

- 位置: `app/api/v1/namespaces/cache.py:214`
- 类型: 防御
- 描述: `/cache/clear/all` 用 `cleared_count` 统计成功, 但下层当前固定返回 True, 导致统计失真.
- 影响: 运维误判, 自动化脚本/监控依赖该字段会产生错误结论.
- 建议: 返回真实删除数, 或在 API 响应中增加 `noop`/`not_supported` 字段.

### P2

#### P2-1: pattern delete 能力存在但未接入主路径

- 位置: `app/utils/cache_utils.py:190`
- 类型: 适配
- 描述: 存在 `invalidate_pattern()` 逻辑(依赖后端 `delete_pattern`), 但未被业务失效路径使用, 且形态为类外函数.
- 建议: 若需要 pattern delete, 将其收敛为 `CacheManager.invalidate_pattern()` 并提供统一入口; 否则删除死代码以降低维护成本.

#### P2-2: 缓存配置项命名可能引发误解

- 位置: `app/settings.py:499`
- 类型: 兼容/可维护性
- 描述: `CACHE_DEFAULT_TTL`, `CACHE_RULE_TTL` 等被写入 `app.config`, 但 Flask-Caching 实际核心消费项主要为 `CACHE_DEFAULT_TIMEOUT` 与后端连接参数. 其余更像业务配置.
- 建议: 将 "Flask-Caching 配置" 与 "业务 TTL 配置" 分组命名(例如 `BIZ_CACHE_*`), 或在文档中明确哪些 key 由哪个模块消费.

## 建议与后续行动(可执行清单)

### 近期(建议 1-3 天内)

- 修复 P0-1: 让清缓存 API 返回真实语义(执行了什么, 删除了多少, 是否支持).
- 修复 P0-2: 为静态资源引入指纹化或调整 Nginx 强缓存策略.
- 修复 P0-3: 限流改为 Redis 原子实现, 并限制降级策略.

### 中期(建议 1-2 周)

- 收敛缓存封装层, 统一 key/TTL/失效/监控口径.
- 为关键缓存路径补齐测试: Redis 场景写入/读取/失效, None 缓存语义, key 归一化.

## 证据与数据来源

- 缓存配置与校验: `app/settings.py:192`, `app/settings.py:485`, `app/settings.py:645`
- Flask-Caching 初始化与注入: `app/__init__.py:241`
- 通用装饰器缓存: `app/utils/cache_utils.py:224`, `app/utils/cache_utils.py:251`
- 业务缓存服务: `app/services/cache_service.py:28`
- cache 管理 API: `app/api/v1/namespaces/cache.py:67`
- classification 缓存适配: `app/services/account_classification/cache.py:29`
- 限流: `app/utils/rate_limiter.py:130`
- 健康检查: `app/services/health/health_checks_service.py:54`
- 前端日志页缓存: `app/static/js/modules/views/history/logs/logs.js:21`
- Nginx 静态资源缓存: `nginx/sites-available/whalefall-prod:15`, `nginx/sites-available/whalefall-dev:15`

