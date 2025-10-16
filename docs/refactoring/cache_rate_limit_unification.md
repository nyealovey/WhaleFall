> 注意：本文件已被《统一改造执行计划》整合与编排。执行请以 `docs/refactoring/unified_refactoring_plan.md` 为准；本文件保留作专题说明与背景参考。

# 缓存与速率限制统一方案

目标
- 以 `app/utils/cache_manager.py` 作为缓存统一入口，路由层禁止直接访问底层 Cache；`app/services/cache_manager.py` 作为领域封装需统一回用 utils 层或合并。
- 以 `app/utils/rate_limiter.py` 的 `rate_limit`/`api_rate_limit` 系列为统一入口，标准化响应头与错误处理路径（对齐全局错误处理器）。

缓存统一
- Key 命名：`<prefix>:<sha256(args,kwargs)>`（参数序列化 + 哈希），避免在业务层手写 query-string；统一通过 `cache_manager` 封装生成键。
- Key 前缀规范：参考 `SystemConstants.CacheKeys`（如 `api:`、`dashboard:`、`user:` 等）；示例：`api:instances:list:v1:<sha256>`。
- TTL 规范（与 `SystemConstants` 对齐）：
  - 列表：`60s`
  - 统计：`300s`
  - 配置/枚举：`3600s`
  - 领域长缓存（账户权限等）：按现状保留更长 TTL（如 2h/1d/7d），封装在服务层，统一入口仍走 utils 层。
- 禁止在业务层拼装不一致的 key；统一通过 `cache_manager` 封装。

限流统一
- 返回头：`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`，失败时附带 `Retry-After`（秒）。
- 现状默认：`SystemConstants.RATE_LIMIT_WINDOW`（当前 300s）、`SystemConstants.RATE_LIMIT_REQUESTS`（当前 1000/窗口）；登录限制默认关闭（`LOGIN_RATE_LIMIT=999999`）。
- 推荐生产：普通接口 `60/min`，敏感/登录接口更严（如 `10/min`）；作为迁移项统一调整 `SystemConstants`。
- 错误返回统一（建议）：限流装饰器抛出业务异常（如 `RateLimitExceeded`）并由全局增强错误处理器统一返回结构；现状实现直接返回 JSON（`{"error", "message", "retry_after"}`）并设置响应头，迁移阶段允许共存。

示例
```python
from app.utils.rate_limiter import api_rate_limit

@api_rate_limit(limit=30, window=60)
def search():
    ...
```

迁移步骤
1) 搜索项目中的自定义/占位限流装饰器（如 `app/utils/decorators.py` 中的 `rate_limit`），统一替换为 `app/utils/rate_limiter.py` 的 `api_rate_limit`/`rate_limit`。
2) 路由禁用直接 `cache.set/get`，统一走 `cache_manager` 封装（键与 TTL 走 utils 层生成）。
3) 为缓存异常与速率限制异常统一错误路径：优先上抛业务异常，由增强错误处理器格式化；暂未改造处维持现状 JSON，但在 PR 中标注待迁移。
4) 按推荐生产参数在 `SystemConstants` 调整默认限流窗口与配额，保留环境可配置与常量校验。

## 涉及代码位置
- `app/utils/cache_manager.py`
- `app/utils/rate_limiter.py`
- `app/utils/decorators.py`（如仍存在速率限制装饰器，需统一迁移）
- `app/routes/*.py`
- `app/services/cache_manager.py`（领域封装需统一复用 utils 层接口）

---

## 缓存策略细则
- Key 规范：`<prefix>:<sha256(args,kwargs)>`（避免暴露参数细节与键膨胀）
  - 列表：`instances:list:v1:<sha256(page,size,filters)>`
  - 统计：`dashboard:metric:v1:<sha256(name,range,gran)>`
  - 配置：`configs:enum:v1:<sha256(type)>`
- TTL 建议：
  - 列表：60s（用户操作频繁，避免过旧）；
  - 统计：300s（图表允许轻度延迟以提升性能）；
  - 配置/枚举：3600s（低变更频率）。
- 失效策略：
  - 写操作后失效相关前缀（例如：`instances:*`）；
  - 图表统计在窗口结束或强制刷新时失效；
  - 由 `cache_manager` 提供统一的失效封装，避免各处手写。
- 并发与降级：
  - 缓存击穿采用请求级互斥/单航班策略（single-flight）；
  - 下游异常时记录结构化日志并走降级（返回 `None` 触发直连查询/重试）；错误由全局处理器统一格式化（不使用 `APIResponse`）。

## 速率限制细则
- 维度：IP、用户、接口；默认采用用户维度（`api_rate_limit`），登录/注册等安全接口采用 IP 维度。
- 窗口与限额（与 `SystemConstants` 对齐）：现状 `300s/1000`；推荐普通接口 `60/min`，敏感接口 `10/min`。
- 响应头：
  - `X-RateLimit-Limit`: 当前窗口限额；
  - `X-RateLimit-Remaining`: 剩余可用次数；
  - `X-RateLimit-Reset`: 窗口重置时间戳（秒）。
- 失败响应：`429` + 现状 JSON（`{"error", "message", "retry_after"}`）并附带 `Retry-After`；推荐改为抛出业务异常交由增强错误处理器统一结构。
- 日志：记录 `user_id/ip/module/endpoint` 与限流命中次数，便于审计。

## 示例：统一限流装饰器
```python
from app.utils.rate_limiter import api_rate_limit

@api_rate_limit(limit=60, window=60)
def search():
    # 正常处理
    ...
```

## 迁移清单
1) 将自定义的缓存访问与 key 拼装，迁移为 `cache_manager` 封装调用（键前缀与哈希统一）。
2) 将不同风格的限流实现统一迁移为 `rate_limiter.api_rate_limit`/`login_rate_limit` 等标准装饰器。
3) 为图表与统计接口补齐缓存层与失效策略，设定合适 TTL（与 `SystemConstants` 对齐）。
4) 将限流异常路径统一对齐增强错误处理器；在过渡期标注仍返回 JSON 的端点并排期迁移。

## 验收标准
- 样本抽取 5 个路由：缓存 key 前缀与哈希统一，TTL 合理且命中率提升。
- 样本抽取 3 个敏感接口：限流响应头完整返回；触发 429 时错误结构统一或在过渡清单中标注。
- 写操作后相关列表或统计缓存正确失效并刷新数据；缓存异常场景降级与日志记录验证通过。

## 风险与回退
- 风险：过度缓存导致数据延迟或一致性问题；需评估 TTL 与失效范围。
- 回退：对问题路由降低或移除缓存策略；限流仅保留最小安全线并记录审计日志；异常路径回退为现状 JSON 响应。

## 现状与差异（审计结论）
- 速率限制：`app/utils/rate_limiter.py` 已统一设置 `X-RateLimit-*` 头并在超限时返回 JSON；默认值来自 `SystemConstants`（当前偏宽），登录限制关闭。
- 缓存：存在 `app/utils/cache_manager.py` 与 `app/services/cache_manager.py` 两套封装（默认 TTL 5min vs 7d）；建议以 utils 层为基础统一接口，服务层保留领域长缓存但调用统一入口。
- 装饰器重复：`app/utils/decorators.py` 中存在占位 `rate_limit`，需迁移到统一实现并删除/废弃。