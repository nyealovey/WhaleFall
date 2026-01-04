# 021 dependency and utils library refactor plan

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-03
> 更新: 2026-01-03
> 范围: Python backend dependencies, `app/utils`, auth rate limiting, payload validation, cache helpers
> 关联: `docs/standards/documentation-standards.md`, `docs/standards/changes-standards.md`, `docs/standards/halfwidth-character-standards.md`

---

## 动机与范围

目标: 用成熟库替换关键手写工具, 降低维护成本, 提升一致性与安全性, 并清理未使用依赖.

本计划覆盖:

- 依赖层: `pyproject.toml`, `uv.lock`, `requirements*.txt`
- 限流: `app/utils/rate_limiter.py`, `app/routes/auth.py`, `app/api/v1/namespaces/auth.py`
- 校验与清洗: `app/utils/data_validator.py` 及其服务层调用点
- 缓存封装: `app/utils/cache_utils.py` (只做收敛与对齐, 不做大改)

非目标:

- 替换 Flask 框架或大规模迁移 API 风格
- 引入新的数据库或修改既有数据库 schema
- 在本计划中重写 `connection_adapters` 的 DBAPI 适配器实现

## 现状扫描摘要

### 手写模块(候选替换)

- 限流: `app/utils/rate_limiter.py` (滑动窗口, Cache/内存降级, 自定义 header/redirect)
- 校验与清洗: `app/utils/data_validator.py` (表单 MultiDict 清洗, 业务字段校验, 简单 XSS 过滤)
- 缓存封装: `app/utils/cache_utils.py` (CacheManager, key 生成, decorator)

### 依赖可疑点(需确认后再动)

在当前工作树中, 未发现 `app/` 与 `scripts/` 直接引用以下依赖:

- `loguru`
- `requests`
- `pytz`
- `bleach`
- `psycopg2-binary`

注意: 以上仅代表静态引用扫描结果, 最终是否移除仍需结合运行时路径(例如动态导入, 运维脚本, 以及实际部署的 `DATABASE_URL` 方言).

## 不变约束(行为/契约/性能门槛)

- API 返回封套不变: 继续使用 `app/utils/response_utils.py` 与 `app/api/v1/models/envelope.py` 的结构.
- 认证与权限语义不变: 路由与 RESTX namespace 的返回码, 错误文案, 登录态保持不变.
- 反向代理信任模型不变: 继续依赖 `TrustedProxyFix`(`app/utils/proxy_fix_middleware.py`) 控制 `X-Forwarded-*` 的可信来源, 限流 key 不直接信任 `request.access_route`.
- 配置统一入口不变: 新增或调整配置项必须落在 `app/settings.py`.
- 性能门槛: 限流与校验不能引入明显可感知的额外延迟, 以现有 `uv run pytest -m unit` 与关键页面交互为准.

## 分层边界(依赖方向/禁止项)

- `routes/` 与 `api/v1/namespaces/` 只编排请求, 业务逻辑进入 `services/`.
- `services/` 可依赖 `repositories/`, `models/`, `utils/`, 但不应把 HTTP/Flask Response 拼装下沉到 service 内.
- `utils/` 优先保持纯函数与无副作用, 除非它明确是"集成型 helper"(例如 `route_safety` 这类集中 commit/rollback 的工具). 新增的校验/解析优先放入 `app/types/` 或独立 schema 模块.

## 分阶段计划(每阶段验收口径)

### Phase 0: 基线与回归口径

目标: 在开始改动前固定"验证命令"与关键行为基线, 避免重构引入暗改.

步骤:

- 运行基础门禁:
  - `make typecheck`
  - `ruff check app`
  - `uv run pytest -m unit`
- 记录 login 与 password reset 的现有行为:
  - HTML: `app/routes/auth.py`
  - API: `app/api/v1/namespaces/auth.py`
  - Header: `Retry-After`, `X-RateLimit-*`

验收:

- 上述门禁通过, 或在本计划 `progress` 文档中记录已知失败项与原因.

### Phase 1: 依赖清理(只做无争议项)

目标: 降低依赖面与供应链风险, 避免"装了但不用"造成的维护成本.

步骤:

- 再次扫描确认无直接引用:
  - `rg -n \"\\bloguru\\b|\\brequests\\b|\\bpytz\\b|\\bbleach\\b|psycopg2\" -S app scripts`
- 明确是否仍需要 `psycopg2-binary`:
  - `env.example` 当前使用 `postgresql+psycopg://`(psycopg3 方言).
  - 若生产仍存在 `postgresql+psycopg2://` 或未带方言的连接串, 需要先统一再移除.
- 在 `pyproject.toml` 中移除确认不用的依赖, 并用 `uv` 更新锁文件与导出文件:
  - `uv lock`
  - `uv export --format requirements-txt --output-file requirements.txt`
  - 如有 `requirements-prod.txt` 自动生成链路, 统一由脚本生成并保持一致.

验收:

- `uv run pytest -m unit` 通过.
- 应用可启动(至少 `python app.py`), 且关键页面可访问.

回滚:

- 通过 git revert 回退 `pyproject.toml` 与锁文件改动.

### Phase 2: 用 `flask-limiter` 替换手写限流

目标: 用成熟限流组件替换 `app/utils/rate_limiter.py`, 减少自维护滑动窗口与 header 拼装逻辑.

推荐落地策略(最小改动):

- 保留现有 decorator API 形态 `login_rate_limit()` / `password_reset_rate_limit()`, 但内部改为调用 `flask-limiter` 的限流器, 以避免全仓库替换装饰器用法.

步骤:

- 引入依赖: `flask-limiter`
- 在 `app/__init__.py` 注册 limiter extension, 从 `Settings` 读取开关与 storage 配置:
  - storage 建议优先对齐 Redis, 并复用现有 `redis` 依赖
  - key 策略保持与现有一致:
    - login: `username:remote_addr`
    - password reset: `user_id(or anonymous):remote_addr`
- 迁移行为对齐:
  - API 请求返回 429, 并继续包含 `Retry-After` 与 `X-RateLimit-*` header
  - HTML 请求维持现有 UX: flash + redirect(如需要, 为 limiter 自定义 error handler)

验收:

- 单元测试覆盖:
  - login 限流触发后返回 429, 且 header 存在.
  - password reset 限流触发后返回 429, 且 header 存在.
- 手工回归:
  - `app/routes/auth.py` 登录页面限流路径与提示无回退.

回滚:

- 保留旧 `app/utils/rate_limiter.py` 实现一个版本周期, 以 feature flag 或快速 revert 方式回退.

### Phase 3: 用 `pydantic` 替换关键 payload 校验

目标: 收敛 `DataValidator` 的职责, 把"解析 + 默认值 + 校验 + 错误信息"统一为 schema.

步骤:

- 引入依赖: `pydantic`(可选: `pydantic-settings`, 若希望与 `Settings` 结构对齐)
- 先覆盖高价值写路径:
  - `app/services/instances/instance_write_service.py`
  - `app/services/credentials/credential_write_service.py`
  - `app/services/users/user_write_service.py`
  - `app/services/tags/tag_write_service.py`
- 将 `DataValidator` 降级为兼容层:
  - 保留 `sanitize_form_data` 作为 MultiDict -> dict 的薄封装
  - 业务字段校验迁移到 pydantic schema

验收:

- 原有错误口径不变(或在本计划中明确允许的文案微调范围).
- `make typecheck` 与 `uv run pytest -m unit` 通过.

回滚:

- schema 分模块落地, 每个服务可单独回退到 `DataValidator` 路径.

### Phase 4: 清洗策略决策(二选一)

决策点: 是否需要在任何字段中允许有限 HTML.

- 若只需要纯文本: 继续使用 `html.escape` 类似策略, 并移除 `bleach`.
- 若需要有限 HTML: 使用 `bleach.clean` 统一 allowlist, 并明确"哪些字段允许哪些 tag/attr".

验收:

- 安全扫描与人工 review 通过, 且不会误伤正常输入.

## 风险与回滚

- 依赖移除风险: 运行时路径或运维脚本的隐式依赖导致生产故障. 缓解: Phase 1 只移除"无争议"依赖, 并在灰度环境跑启动与关键任务.
- 限流替换风险: key 策略或 proxy 解析变化导致误限流/漏限流. 缓解: 保持 `request.remote_addr` 策略, 并在有代理与无代理两种部署形态下验证.
- 校验替换风险: 错误文案与字段边界变化影响前端提示. 缓解: 先落地最核心写路径, 并保留兼容层.

## 验证与门禁

- 单元测试: `uv run pytest -m unit`
- 类型检查: `make typecheck`
- 风格检查: `ruff check app`
- 命名巡检: `./scripts/ci/refactor-naming.sh --dry-run`
- 半角字符检查(文档与注释): `rg -n -P \"[\\x{3000}\\x{3001}\\x{3002}\\x{3010}\\x{3011}\\x{FF01}\\x{FF08}\\x{FF09}\\x{FF0C}\\x{FF1A}\\x{FF1B}\\x{FF1F}\\x{2018}\\x{2019}\\x{201C}\\x{201D}\\x{2013}\\x{2014}\\x{2026}]\" docs app scripts tests`

## 附录: 关键引用点(便于落地检索)

- 限流入口:
  - `app/utils/rate_limiter.py`
  - `app/routes/auth.py`
  - `app/api/v1/namespaces/auth.py`
- 校验入口:
  - `app/utils/data_validator.py`
  - `app/services/instances/instance_write_service.py`
- 缓存封装:
  - `app/utils/cache_utils.py`

