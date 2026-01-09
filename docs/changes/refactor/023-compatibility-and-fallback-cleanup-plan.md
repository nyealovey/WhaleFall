# 023 compatibility and fallback cleanup plan

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-04
> 更新: 2026-01-04
> 范围: config, api contracts, permissions snapshot/facts, logging context
> 关联: `docs/Obsidian/standards/doc/documentation-standards.md`, `docs/Obsidian/standards/doc/changes-standards.md`, `docs/Obsidian/standards/halfwidth-character-standards.md`, `docs/reference/config/environment-variables.md`, `docs/plans/2026-01-03-compat-fallback-migration-cleanup.md`

---

## 动机与范围

目标: 收敛后端的兼容/兜底/回退逻辑, 把 "静默兜底" 改成 "可观测 + 可下线", 并通过分层边界把兼容逻辑压到系统边界处.

本计划覆盖(以 Python 后端为主):

- 配置读取的历史别名与默认策略: `app/settings.py`
- API 结果归一化与契约收敛: `app/api/v1/namespaces/*`
- 权限快照 v4 与 facts 构建链路的 shape 兼容: `app/services/accounts_sync/*`, `app/services/accounts_permissions/*`
- 结构化日志上下文的安全兜底与解耦: `app/utils/logging/*`

非目标:

- 大规模重写 Flask/RESTX 框架用法
- UI 或 `app/static/vendor/**` 三方代码清理
- 引入新的 "silent fallback" 分支(除非有明确事故复盘或线上证据)

## 现状扫描摘要(关键命中点)

### A) 配置兼容与回退

- env var 历史别名: `app/settings.py:159` 读取 `JWT_REFRESH_TOKEN_EXPIRES` 失败时回退 `JWT_REFRESH_TOKEN_EXPIRES_SECONDS`.
- 数据库连接串缺失回退: `app/settings.py:170` 非 production 缺失 `DATABASE_URL` 时回退 sqlite.

### B) API 契约与结果归一化

- `success` 字段缺失时默认成功: `app/api/v1/namespaces/accounts.py:262` 使用 `pop("success", True)`.
- payload 解析兜底为空 dict: `app/api/v1/namespaces/connections.py:125` 使用 `get_json(silent=True)` 并在非 dict 时回退 `{}`.

### C) 权限数据版本化与 shape 兼容

- 字段别名桥接: `app/services/accounts_sync/permission_manager.py:127` 把 `database_privileges_pg` 归一化到 `database_privileges`.
- facts 构建支持多种输入形态: `app/services/accounts_permissions/facts_builder.py:45` 支持 list, `{"granted": [...]}`, 以及 `{"PRIV": true}`.
- v4 快照强约束 fail-fast: `app/services/accounts_permissions/snapshot_view.py:20` 非 v4 直接抛错(该策略应保留).

### D) 结构化日志兜底

- module 字段多级兜底: `app/utils/logging/handlers.py:180` 使用 `or` 链回退到 "app".
- context 序列化异常兜底: `app/utils/logging/handlers.py:271` `to_dict()` 失败回退 `str(value)`.

## 不变约束(行为/契约/性能门槛)

- 对外 API envelope 不变: 继续使用 `app/api/v1/models/envelope.py` 与 `app/utils/response_utils.py` 的封套结构.
- 权限快照 v4 的 fail-fast 不变: snapshot 缺失或非 v4 必须是显式错误, 不做自动兜底 legacy.
- 生产环境关键配置缺失必须 fail-fast: `DATABASE_URL`, `SECRET_KEY`, `JWT_SECRET_KEY` 等口径保持不变.
- 重构期不引入新的静默吞错: 新增兜底必须有日志或指标, 且在 doc 中写清下线条件.

## 分层边界(依赖方向/禁止项)

约束目标: 兼容逻辑应优先落在边界层, 避免扩散到核心逻辑.

- 边界层: `app/settings.py`, `app/api/v1/namespaces/*`, `app/schemas/*`, `app/services/*/adapters/*`
  - 允许: 字段别名, 类型归一化, version gate, "fail closed" 策略.
  - 必须: 兼容分支可观测(日志/metric), 有明确清理计划.
- 核心业务层: `app/services/**`(除 adapters), `app/repositories/**`
  - 不建议: 读取 HTTP 请求对象, 直接依赖 `flask.g` / `current_user`, 或在深层做隐式兼容映射.
  - 建议: 使用显式的输入结构(已规范化 dict 或 schema), 并在进入 service 前完成 canonicalization.

## 分阶段计划(每阶段验收口径)

### Phase 0: 基线与清单冻结

目标: 固定验证命令与命中点清单, 避免边改边漂移.

步骤:

- 跑基础门禁:
  - `make typecheck`
  - `ruff check app`
  - `uv run pytest -m unit`
- 生成兼容/兜底命中点清单(用于后续复核):
  - `rg -n \"\\.get\\(.*\\)\\s+or\\s+\" app --glob \"*.py\" -S`
  - `rg -n \"(?i)(legacy|deprecated|compat|fallback|migration|version)\" app --glob \"*.py\" -S`

验收:

- 门禁通过, 或在对应 `*-progress.md` 中记录已知失败项与原因.

### Phase 1: 先可观测, 后收敛(不改变外部行为)

目标: 保留现有兼容行为, 但把 "被命中" 变得可追踪, 并为后续删除准备数据.

任务:

- env var 历史别名命中告警:
  - 触发点: `app/settings.py:159`
  - 行为: 当读取到 `JWT_REFRESH_TOKEN_EXPIRES_SECONDS` 且主变量缺失时, 记录 warning, 并在日志中带上 `env_var=JWT_REFRESH_TOKEN_EXPIRES_SECONDS`.
  - 文档: 在 `docs/reference/config/environment-variables.md` 明确该别名的下线版本窗口.
- `success` 缺失的兼容统计:
  - 触发点: `app/api/v1/namespaces/accounts.py:262`
  - 行为: 当返回 payload 缺失 `success` 字段时, 记录 warning 或 counter, 但不修改默认值(先保留 `True`).
- 权限字段别名桥接命中统计:
  - 触发点: `app/services/accounts_sync/permission_manager.py:127`
  - 行为: 当输入包含 `database_privileges_pg` 时记录一次 metric 或 structured log, 以便判断是否仍有生产者在用.
- facts builder 非 canonical shape 标记:
  - 触发点: `app/services/accounts_permissions/facts_builder.py:45`
  - 行为: 当命中 `{"PRIV": true}` 这类 fallback shape 时, 往 facts.errors 追加类似 `PRIVILEGE_SHAPE_FALLBACK`(或仅做日志), 便于定位数据源.

验收:

- `uv run pytest -m unit` 通过.
- 日志中可检索到上述兼容命中事件(至少在本地用构造输入触发一次).

### Phase 2: 契约收敛与兼容分支下线(分模块逐步推进)

目标: 在收集到 Phase 1 的命中数据后, 逐步删除不再需要的兼容分支, 并同步更新文档.

任务(建议按风险从低到高):

1) env var 历史别名下线:
   - 删除 `JWT_REFRESH_TOKEN_EXPIRES_SECONDS` 读取分支.
   - 更新: `docs/reference/config/environment-variables.md`, `env.example`.
2) 权限字段别名下线:
   - 删除 `database_privileges_pg` 的映射键.
   - 前置: 先确认所有 upstream producer 已输出 canonical key.
3) facts builder shape 收敛:
   - 若 snapshot 版本为 4, 要求 privileges 仅接受 canonical shape, 不再接受 bool map.
   - 对不合法输入: fail closed(返回空 privileges 并写入 errors), 不做 silent fallback.
4) `success` 缺失默认值收敛(需要决策):
   - 方案 A(更严格): 缺失 `success` 视为失败, 并要求所有调用链显式写入 `success`.
   - 方案 B(兼容过渡): 缺失 `success` 时通过 `status` 推断, 并在下一版本移除推断.

验收:

- `make typecheck` 与 `uv run pytest -m unit` 通过.
- `docs/reference/config/environment-variables.md` 与 `env.example` 不再包含已下线别名.

### Phase 3: 分层解耦与清理(可选, 只做边界收敛)

目标: 把 "依赖框架上下文的兜底" 收敛到边界, 减少 service/utils 对 Flask 全局的耦合.

候选任务:

- 日志上下文采集解耦:
  - 触发点: `app/utils/logging/handlers.py:224`
  - 方向: 把 `g/current_user` 读取改为由上游(请求入口)注入 context, handler 仅做格式化与 scrub.

验收:

- 不改变日志表结构与主要字段名, 仅减少 "handler 内部读全局" 的比例.

## 风险与回滚

- 风险: 兼容分支下线会影响旧客户端或旧数据源.
  - 缓解: Phase 1 先做命中统计, Phase 2 再删除, 并在文档中明确下线窗口.
  - 回滚: git revert 对应 PR, 或临时恢复兼容分支(仅限短期).
- 风险: `success` 默认值变更可能导致前端或任务调度误判状态.
  - 缓解: 先补齐 upstream producer 的显式字段, 再改默认策略, 并增加回归用例.

## 验证与门禁

- 单元测试: `uv run pytest -m unit`
- 类型检查: `make typecheck`
- Ruff: `ruff check app`
- 命名巡检: `./scripts/ci/refactor-naming.sh --dry-run`
- 半角字符检查(文档与注释): `rg -n -P \"[\\x{3000}\\x{3001}\\x{3002}\\x{3010}\\x{3011}\\x{FF01}\\x{FF08}\\x{FF09}\\x{FF0C}\\x{FF1A}\\x{FF1B}\\x{FF1F}\\x{2018}\\x{2019}\\x{201C}\\x{201D}\\x{2013}\\x{2014}\\x{2026}]\" docs app scripts tests`

## 附录: 需要重点跟踪的兼容点(P0/P1)

| Priority | Location | Type | Notes |
|---|---|---|---|
| P0 | `app/api/v1/namespaces/accounts.py:262` | compat | `success` 缺失默认 `True`, 需要先观测后收敛 |
| P0 | `app/services/accounts_sync/permission_manager.py:127` | compat | `database_privileges_pg` 字段别名桥接 |
| P1 | `app/settings.py:159` | compat | JWT refresh env var 历史别名 |
| P1 | `app/services/accounts_permissions/facts_builder.py:45` | compat | privileges 支持 bool map fallback shape |
