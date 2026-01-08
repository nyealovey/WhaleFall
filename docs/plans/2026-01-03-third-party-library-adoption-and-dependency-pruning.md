# 第三方库采用与依赖清理实施计划

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-03
> 更新: 2026-01-04
> 范围: `app/utils/**`, `app/services/cache_service.py`, `app/api/v1/namespaces/cache.py`, `app/static/js/**`, `pyproject.toml`, `requirements*.txt`
> 关联: `docs/Obsidian/standards/halfwidth-character-standards.md`, `docs/Obsidian/standards/documentation-standards.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> 说明: 上面这一行是给自动化执行器的约束. 如果是人工执行, 可以忽略.

**Goal:** 清理"已引入但未使用"的第三方库, 收敛重复的手写实现, 并把关键能力(安全清洗, 缓存失效, HTTP 客户端)落到可验证的单一入口.

**Architecture:** 先做"依赖-用量-重复实现"三表盘点, 再按风险从低到高分阶段落地: (1) 删除纯未使用依赖与前端 vendor, (2) 修复当前行为明显错误但改动面可控的点, (3) 收敛抽象层并补齐单元测试与门禁脚本.

**Tech Stack:** Flask, Flask-RESTX, SQLAlchemy, Flask-Caching(+Redis backend), Flask-WTF(CSRF), structlog, Vanilla JS, vendor libs(umbrella, lodash, dayjs, mitt, gridjs, tom-select).

---

## 0) 决策矩阵(库, 作用, 现状, 计划)

说明: 本表只覆盖本次"重复实现/未充分利用"扫描命中的库. 其它依赖(例如数据库驱动)不在本计划的主整改范围.

| 领域 | 库 | 作用(它负责什么) | 仓库当前状态 | 决策 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 后端安全 | `bleach` | HTML 清洗, 白名单 tag/attribute/protocol, 去除危险内容 | 已移除(2026-01-04) | 移除 | 项目无用户富文本输入,渲染依赖 Jinja autoescape |
| 后端缓存 | `flask-caching` | 统一缓存 API, 多后端(SimpleCache, Redis 等), 提供常用装饰器 | 已引入且在初始化中使用 | 保留 | 作为唯一缓存基座 |
| 后端缓存后端 | `redis` | Redis 客户端, 供 Flask-Caching Redis 后端使用 | 已引入, settings 支持 Redis | 保留(当 `CACHE_TYPE=redis`) | 若生产永不启用 Redis, 后续再评估 |
| 后端日志 | `structlog` | 结构化日志, processors(处理器链), 上下文绑定 | 大量使用 | 保留 | 已是项目选择的日志栈 |
| 后端日志(替代) | `loguru` | 便捷 logger, sink/rotation(输出/轮转)等 | 已移除(2026-01-04) | 移除 | 同时检查 README 等文档是否误导 |
| 后端 HTTP | `requests` | 对外 HTTP 客户端 | 已移除(2026-01-04) | 移除 | 未发现对外 HTTP 调用场景 |
| 后端时区 | `pytz` | 旧式时区库, zoneinfo 之前的主流方案 | 已移除(2026-01-04) | 移除 | 优先使用 `zoneinfo` + `tzdata` |
| 后端时区 | `tzdata` | IANA tz 数据, 用于系统未内置 tzdata 的环境 | 已声明 | 保留 | 支撑 `zoneinfo.ZoneInfo` |
| 后端 PG 驱动 | `psycopg[binary]` | psycopg v3 驱动, binary extras 便于安装 | 代码使用(`import psycopg`) | 保留 | 当前 adapter 使用 psycopg v3 |
| 后端 PG 驱动(旧) | `psycopg2-binary` | psycopg v2 wheels | 已移除(2026-01-04) | 移除 | 避免双驱动并存带来的歧义 |
| 前端 HTTP(备选) | `axios`(vendor) | HTTP 客户端, 拦截器, 取消请求 | 已移除(2026-01-04) | 移除(优先) | 另一种方案: 采用 axios 并删掉 `httpU` |
| 前端进度条 | `nprogress`(vendor) | 顶部进度条, 常用于 ajax 导航 | vendored, 未被引用 | 移除 | 另一种方案: 集成到 HTTP 层后再启用 |

---

## 0.1) 各库详解(作用, 如何替代手写代码)

本节把决策矩阵里的每个库展开讲清楚, 让"为什么保留/移除/采用"可以被复核, 也能被测试覆盖.

### `bleach`(Python)

它负责什么:
- 针对"不可信 HTML 输入, 但需要以 HTML 方式渲染"的清洗器.
- 采用 allowlist(白名单)策略: 只允许指定 tag/attribute/protocol, 其余内容会被转义或移除(取决于配置).

它和当前手写实现的关系:
- `app/utils/data_validator.py` 的 `DataValidator.sanitize_string` 试图对所有字符串做统一的 XSS 清理.
- 但 XSS 安全依赖渲染上下文(HTML 文本, HTML 属性, URL, JS 字符串等). 单一"通用清洗"很容易带来错误的安全感.

决策建议:
- 只有当产品存在"富文本 HTML 字段"且确实会被当作 HTML 渲染时才保留 `bleach`.
- 如果所有用户输入最终都以普通文本渲染(依赖 Jinja autoescape), 更合理的策略是移除 `bleach`, 避免"依赖存在但无语义"的漂移.
- 本项目确认无用户富文本输入, 本次决策: 移除 `bleach`, 并将 `sanitize_string` 收敛为输入规范化.

如果选择"采用", 具体要做什么:
- 新增专用 helper(例如 `sanitize_rich_text_html`) 来集中配置 allowlist.
- 用单元测试明确允许/禁止的 tag/attribute/protocol, 并验证 `<script>`, `javascript:`, `onerror=` 等不会残留.
- 模板只对"已清洗过的 HTML"使用 safe 渲染, 禁止对原始用户输入直接标记 safe.

### `flask-caching`(Python)

它负责什么:
- Flask 扩展, 提供统一的 `Cache` API, 支持多种后端(SimpleCache, Redis 等).
- 统一能力包括 `get/set/delete/clear`, 并提供常用装饰器(例如 `cached`, `memoize`)用于函数级缓存.

它和当前手写实现的关系:
- 当前仓库存在两层 wrapper:
  - `app/services/cache_service.py`: 偏业务的缓存读写封装(分类规则, 规则评估等).
  - `app/utils/cache_utils.py`: 偏通用的 cache manager + 自定义 `cached` 装饰器(主要用于 dashboard).
- 两层都基于 Flask-Caching, 但 key 生成规则与失效逻辑存在重复/分叉.

这里"充分利用"具体指:
- Flask-Caching 作为唯一缓存基座, 不再发明第二套 get/set/delete.
- 能用 Flask-Caching 官方能力就用官方能力. 只有在官方无法覆盖的跨领域需求(例如 user/instance 级失效)才保留项目自定义层.

### `redis`(Python)

它负责什么:
- 当 `CACHE_TYPE=redis` 时, 作为 Flask-Caching Redis 后端的 Python 客户端库.
- Redis 原生提供适合做缓存失效的原语(例如 pattern scan, set, 原子操作), 但 Flask-Caching 默认并不提供完整的高层失效 API.

它和当前手写实现的关系:
- 当前 `invalidate_user_cache`/`invalidate_instance_cache` 实际不删除任何 key, 但返回成功.
- 要实现可控的失效, 至少需要二选一:
  - 维护 key 索引(按 user/instance 记录 keys), 失效时按索引批量 delete.
  - 采用可 pattern delete 的 key 命名规则(前缀可枚举), 并在 Redis 后端上调用 `delete_pattern`.

本计划的立场:
- 优先 key 索引方案, 因为当前 cache key 被 hash, 无法通过 prefix 推导出 pattern.
- 初期实现尽量只依赖 `Cache.get/set/delete`(把索引存成 JSON 列表). 后续若有性能需求, 再考虑用 Redis set 优化.

### `structlog`(Python)

它负责什么:
- 结构化日志框架, 通过 processors(处理器链)组装 event 字典, 支持上下文绑定, 输出 JSON 等.
- 本仓库已将其作为主日志栈(见 `app/utils/structlog_config.py`).

为什么保留:
- 已实现 request_id/user_id 等上下文注入, 并支持写入数据库统一日志.
- 再引入 `loguru` 会导致日志体系分裂, 维护者不清楚应使用哪个 logger, 也会增加一致性成本.

### `loguru`(Python)

它负责什么:
- 另一套日志库, 提供便捷 API, 更丰富的格式化, sink 管理等.

为什么移除:
- `app/**` 未发现运行时使用点.
- 与当前基于 structlog 的结构化日志体系功能重叠. 两套并存只会制造选择歧义, 没有明确收益.

### `requests`(Python)

它负责什么:
- 对外 HTTP 客户端, 用于从服务端请求第三方接口.

为什么移除:
- 仓库内未发现对外 HTTP 使用点(未找到 `import requests`).
- 移除可降低依赖面与供应链维护成本, 也避免无意义的版本升级与安全补丁噪音.

### `pytz` 和 `tzdata`(Python)

它们分别负责什么:
- `pytz`: 旧式时区库, 在 `zoneinfo` 之前常用于时区转换与本地化.
- `tzdata`: IANA tz 数据包, 用于系统未内置 tzdata 的环境(例如极简 Docker 镜像), 以支撑 `zoneinfo`.

为什么移除 `pytz`:
- 当前仓库在 `app/utils/time_utils.py` 使用 `zoneinfo.ZoneInfo`.
- 保留 `pytz` 会制造两套时区 API, 也会增加依赖体积与维护成本.

为什么保留 `tzdata`:
- 它能让 `zoneinfo` 在不带系统 tzdata 的运行环境中正常工作(尤其是精简镜像).

### `psycopg[binary]` 和 `psycopg2-binary`(Python)

它们分别负责什么:
- `psycopg[binary]`: psycopg v3 驱动, 新 API, binary extras 便于安装.
- `psycopg2-binary`: psycopg v2 wheels, 旧 API, 通常只为遗留代码保留.

为什么保留 v3, 移除 v2:
- 当前仓库在 `app/services/connection_adapters/adapters/postgresql_adapter.py` 使用 psycopg v3(`import psycopg`).
- 未发现 v2 的 import. 双驱动并存会增加行为差异与打包问题风险, 没必要.

### `axios`(前端 vendor)

它负责什么:
- Promise 风格的 HTTP 客户端, 可替代 `fetch`, 常用能力包括拦截器, 取消请求, 统一错误处理等.

为什么现在属于"未使用的资产":
- `axios` 曾仅存在于 `app/static/vendor/axios`, 但模板未引入, 业务 JS 也未引用(已于 2026-01-04 移除).

决策与原因:
- 已移除, 以降低前端资源体积与维护成本.
- 若未来确实需要 axios 能力(全局拦截器, cancelation 等), 需要明确"以 axios 作为唯一 HTTP 栈", 并同步删除 `httpU`, 避免双栈并存.

### `nprogress`(前端 vendor)

它负责什么:
- 顶部进度条 UI, 常用于页面导航或耗时的 ajax 请求反馈.

为什么移除:
- 已 vendored, 但仓库内无引用.
- 若未来要启用, 应集成到 HTTP 层(httpU 或 axios)统一驱动, 避免页面各自维护进度条状态.

### `umbrella` 和 `httpU`(前端)

它们分别负责什么:
- `umbrella`: 轻量 DOM helper, 提供基础的 DOM 选择与事件等能力.
- `httpU`: 本仓库自定义的 HTTP 封装, 目标是统一: HTTP API, CSRF header 注入, timeout, 错误解析.

为什么当前阶段选择保留并强化 `httpU`:
- 已在 `app/templates/base.html` 全局加载, 且多数模块已使用.
- 当前主要问题是"使用方式不一致"(存在少量 raw `fetch` 绕开封装), 而不是能力缺失.

## 1) 我们要统一的单一入口(Single Source of Truth)

### A) 缓存层

目标形态:
- 底层只保留一个 cache 基座: Flask-Caching `Cache` 实例.
- 项目层只保留一层跨领域 helper, 用于承载 Flask-Caching 没有覆盖但项目必须统一的能力:
  - key 生成规则统一
  - Redis 后端尽力提供 pattern/批量失效能力
  - 非 Redis 后端要有明确的降级策略(禁止"什么都没做却返回成功")
- 业务域缓存(例如 `ClassificationCache`)保持为薄 wrapper, 不重复造 get/set/delete 等原语.

### B) 输入清洗/输出转义

目标形态:
- 明确定义: 什么是 sanitize(输入清洗), 什么是 validate(输入校验), 什么是 escape(输出转义).
- 避免反模式: "写入时 escape, 渲染时再 escape"(double escaping).
- 若保留 `bleach`, 必须有明确的职责边界(只用于 rich text HTML)并配套单元测试.

### C) 前端 HTTP 客户端

目标形态:
- 前端页面调用后端 API 只有一种方式(单一入口).
- 通用行为集中在一个地方: CSRF header 注入, timeout, 错误 envelope 解析, 以及一致的 JSON shape 处理.

---

## 2) 里程碑与进度表(建议)

假设开始日期: 2026-01-05(Mon). 可按团队产能调整.

| 里程碑 | 日期 | 产出 | 验收口径 |
| --- | --- | --- | --- |
| M0: 基线 + 决策锁定 | 2026-01-05 | 明确 `bleach` 取舍与缓存失效方案 | 单测可通过, 决策写入本文 |
| M1: 清理未使用的 Python 依赖 | 2026-01-06 | 移除 `requests`, `loguru`, `pytz`, `psycopg2-binary` | `uv run pytest -m unit` 通过, `make typecheck` 通过 |
| M2: 缓存失效能力纠正 | 2026-01-07 到 2026-01-08 | `invalidate_user_cache`/`invalidate_instance_cache` 变为真实生效, 不再"空实现也报成功" | cache API 行为确定, 单测覆盖新增行为 |
| M3: 前端 HTTP 统一 + vendor 清理 | 2026-01-09 | 移除未使用的 vendor(`axios`, `nprogress`), 把 raw `fetch` 收敛为 `httpU` | 手工冒烟: 账户统计刷新可用 |
| M4: `bleach` 决策落地 | 2026-01-12 | 采用并加测试, 或干净移除依赖 | 测试覆盖选定语义, 必要时更新文档 |
| M5: 最终验证 | 2026-01-13 | 跑门禁与单测 | `./scripts/ci/ruff-report.sh style`, `./scripts/ci/pyright-report.sh`, `uv run pytest -m unit` 通过 |

---

## 3) 实施任务(能 TDD 就 TDD)

### 任务 0: 建立基线信号

**文件:**
- 不改代码

**步骤 1: 运行单元测试**

执行: `uv run pytest -m unit`
期望: 通过. 若失败, 先记录失败作为变更前 baseline, 避免把无关问题混进本次整改.

**步骤 2: 运行类型检查**

执行: `make typecheck`
期望: 通过. 若失败, 先记录 baseline, 不在本计划里顺手修无关类型错误.

**步骤 3: 运行 lint 报告**

执行: `./scripts/ci/ruff-report.sh style`
期望: 通过. 若失败, 先记录 baseline.

---

### 任务 1: 移除未使用的 Python 依赖(低风险)

**涉及库与作用:**
- `requests`: 对外 HTTP 客户端. 当前仓库无使用点, 可移除.
- `loguru`: 替代日志框架. 当前仓库已选 structlog, 可移除.
- `pytz`: 旧式时区库. 当前仓库用 zoneinfo, 可移除(前提是无隐式依赖).
- `psycopg2-binary`: psycopg v2 驱动. 当前仓库用 psycopg v3, 可移除(除非运行环境强依赖 v2).

**文件:**
- 修改: `pyproject.toml`
- 修改: `requirements.txt`
- 修改: `requirements-prod.txt`
- 修改(如存在): 提到这些依赖的文档(例如 `README.md`)

**步骤 1: 做一次"依赖是否真的在用"的防误删检查(可选, 但建议)**

说明: 如果仓库没有类似门禁, 至少先用全局搜索确认没有运行时代码 import 这些库, 避免误删.
执行: `rg -n \"loguru|requests|pytz|psycopg2\" -S .`
期望: 只命中 docs/lock/requirements, 不命中 `app/**` 的运行时代码 import.

**步骤 2: 从依赖清单中移除未使用依赖**

修改上面的依赖文件, 删除未使用依赖条目.

**步骤 3: 验证**

执行: `uv run pytest -m unit`
期望: 通过

执行: `make typecheck`
期望: 通过

---

### 任务 2: 缓存失效能力纠正(修复"永远 True 的空实现")

问题说明:
- `app/services/cache_service.py` 的 `invalidate_user_cache`/`invalidate_instance_cache` 当前为 no-op, 但返回 `True`.
- `app/api/v1/namespaces/cache.py` 会据此返回"清除成功".
- 结果是: 页面与 API 看起来成功了, 实际缓存未失效, 会阻碍排障并制造错误认知.

**涉及库与作用:**
- `flask-caching`: 缓存基座 API. 提供 `get/set/delete/clear` 与 backend 接入.
- `redis`: 当 `CACHE_TYPE=redis` 时的后端. 可以支撑更强的失效策略(但需要明确实现方式).

**文件:**
- 修改: `app/services/cache_service.py`
- 修改: `app/utils/cache_utils.py`
- 修改: `app/api/v1/namespaces/cache.py`(仅当响应语义需要调整)
- 新增测试: `tests/unit/services/test_cache_service_invalidation.py`

**方案选择(编码前必须选定):**

Option A(推荐): key 索引表驱动的失效
- 写缓存项时, 同时写入索引映射:
  - `whalefall:index:user:{instance_id}:{username}` -> keys 列表
  - `whalefall:index:instance:{instance_id}` -> keys 列表
- 失效时读取索引, 批量 delete keys, 最后删除索引 key.
- 即使 cache key 做了 hash, 也能工作(因为不依赖 prefix 推导).
- 在非 Redis 后端需明确降级策略:
  - 方案 1: 索引仍存 JSON 列表(能力有限, 但至少行为真实).
  - 方案 2: 明确返回 False 并在 API 层告知"当前后端不支持该类失效", 禁止假成功.

Option B: 结构化 key + pattern delete
- 停止对 key 做 hash, 改为结构化 key: `whalefall:{prefix}:{instance_id}:{username}:{db_name}`.
- 在 Redis 后端使用 `delete_pattern` 清除 `whalefall:*:{instance_id}:*`.
- 风险更高: 会改变 key 格式与缓存命中行为, 需要迁移策略.

本计划默认采用 Option A.

**步骤 1: 先写失败的单元测试**

新增 `tests/unit/services/test_cache_service_invalidation.py`:
- 准备(Arrange): 使用一个 fake cache backend(SimpleCache)或内存 stub, 模拟 `get/set/delete`.
- 执行(Act): 写入若干 cache entries + 对应索引 entries, 调用 `invalidate_user_cache`/`invalidate_instance_cache`.
- 断言(Assert): 相关 keys 被删除, 并且仅在"确实执行删除"时返回 `True`.

期望: 实现前测试应 FAIL.

**步骤 2: 实现基于索引的失效**

在 `app/services/cache_service.py`:
- 增加内部 helper:
  - `_track_key_for_user(instance_id, username, cache_key)`
  - `_track_key_for_instance(instance_id, cache_key)`
  - `_invalidate_keys(keys)`(负责吞吐后端异常并统一返回语义)
- 修改写入路径(调用 `self.cache.set` 的地方), 将 key 注册进索引.
  - 最小落地范围: 分类规则缓存与规则评估缓存, 因为这些是线上可感知的主要缓存点.

在 `app/utils/cache_utils.py`:
- 处理 `invalidate_pattern(self, pattern)` 这个"看起来像方法但实际不是方法"的代码:
  - 要么把它变成 `CacheManager.invalidate_pattern(pattern)` 方法并写测试,
  - 要么删除它, 避免死代码误导维护者.

**步骤 3: 运行单测**

执行: `uv run pytest -m unit tests/unit/services/test_cache_service_invalidation.py -v`
期望: 通过

**步骤 4: 跑回归单测**

执行: `uv run pytest -m unit`
期望: 通过

---

### 任务 3: 前端 HTTP 统一与 vendor 清理

问题说明:
- 仓库已有 `app/static/js/core/http-u.js`(自定义 HTTP wrapper), 之前发布过未使用的 `axios` vendor(已于 2026-01-04 移除).
- 存在页面直接用 raw `fetch`, 绕开统一封装, 导致行为不一致.

**涉及库与作用:**
- `umbrella`: 轻量 DOM helper. 本仓库的 `httpU` 依赖它的加载顺序与风格.
- `axios`(vendor): 已移除(2026-01-04), 此前未被使用.
- `nprogress`(vendor): 顶部进度条 UI. 当前未被使用.

**文件:**
- 修改: `app/static/js/modules/views/accounts/statistics.js`
- 修改: `app/templates/base.html`(仅当它引用了待删除 vendor)
- 删除: `app/static/vendor/axios/`(已于 2026-01-04 移除)
- 删除: `app/static/vendor/nprogress/nprogress.js` 和 `app/static/vendor/nprogress/nprogress.css`(若移除 nprogress)

**步骤 1: 把 raw fetch 收敛到 httpU**

修改 `app/static/js/modules/views/accounts/statistics.js`:
- 使用 `window.httpU.get(API_ENDPOINT)` 并按项目统一 envelope 处理响应.
- 保持现有 UI 行为不变(loading toggle, notify 调用).

**步骤 2: 移除未使用 vendor**

- 确认模板与业务 JS 均未引用 nprogress.
- 只有在确认无引用后才删除 vendor 文件, 避免线上 404.

**步骤 3: 手工冒烟清单**

- 打开账户统计页面.
- 点击 "refresh-stats" 按钮.
- 确认请求成功, UI 数据更新.

---

### 任务 4: `bleach` 决策与实现

问题说明:
- `DataValidator.sanitize_string` 目前的"XSS 清理"逻辑存在语义问题: 先对 HTML 做了转义, 然后再删除 `<script` 等模式, 实际上这些模式已不可能匹配到(因为已被转义).
- `bleach` 已声明为依赖但未使用, 导致"依赖存在但能力未落地".

**涉及库与作用:**
- `bleach`: 专用于"不可信 HTML, 但需要以 HTML 方式渲染"的清洗器.

**文件:**
- 修改: `app/utils/data_validator.py`
- 修改: `tests/unit/utils/test_data_validator.py`
- 修改: `pyproject.toml` 和 requirements 文件(若移除 bleach)

**决策检查点(二选一, 并写入提交信息/文档):**

Option A: 移除 `bleach`, 把 `sanitize_string` 简化为"只做 normalize"
- 输入按纯文本处理, 渲染时依赖 Jinja autoescape.
- `sanitize_string` 只做最小 normalize: strip, 去除不可见字符(例如 null byte), 必要时做空白规范化.
- 这是典型 CRUD 应用里最一致, 最不容易误用的策略.

Option B: 保留 `bleach`, 定义专用的 HTML sanitizer
- 引入 `sanitize_rich_text_html(value: str) -> str`, 使用 `bleach.clean(...)` 并明确 allowlist.
- 只允许在"明确会以 HTML 渲染"的字段上使用(并且模板必须在清洗后才允许 safe 渲染).

不要保留一个"看起来像 XSS 防护, 实际语义不清"的通用清洗器, 更不要对所有字段一刀切使用.

**步骤 1: 先写失败的测试**

扩展 `tests/unit/utils/test_data_validator.py`:
- 增加包含 `<script>`, `javascript:`, 以及事件处理属性(例如 `onerror=`)的输入用例.
- 根据选定方案(Option A 或 Option B)断言期望行为.

期望: 实现前测试应 FAIL.

**步骤 2: 实现**

在 `app/utils/data_validator.py` 实现所选方案.

**步骤 3: 验证**

执行: `uv run pytest -m unit tests/unit/utils/test_data_validator.py -v`
期望: 通过

---

## 4) 执行进度跟踪(实施时勾选)

- [x] M0: 基线就绪 + 决策锁定
- [x] M1: 未使用的 Python 依赖已移除
- [ ] M2: 缓存失效能力正确且有单测
- [ ] M3: 前端 HTTP 统一(raw fetch -> httpU 已完成), nprogress 待处理
- [x] M4: bleach 取舍已落地且有单测
- [ ] M5: 最终验证通过
