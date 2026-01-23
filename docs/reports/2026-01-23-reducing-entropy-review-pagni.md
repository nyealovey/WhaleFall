> **Status**: Draft
> **Owner**: Codex（reducing-entropy）
> **Created**: 2026-01-23
> **Updated**: 2026-01-23
> **Mindset**: PAGNI（Probably Are Gonna Need It）
> **Success Metric**: 只允许“极小新增”，但必须能显著减少未来返工/补丁导致的总代码量
> **Scope**: `/Users/apple/Github/WhaleFall`（静态审查；以 DB schema、日志/封套、API 版本化为重点）

# reducing-entropy 审查报告：PAGNI (2026-01-23)

## 1. 核心原则（PAGNI 的触发条件）

默认仍是 YAGNI（能删就删）。

只有同时满足以下 3 条，才允许“现在加一点点代码”：

1) 以后补的成本是现在的 10x+（需要触及大量模块/接口/数据回填）
2) 这是经验性高频坑（不是“也许未来会用到”的想象）
3) 现在的最小实现足够小（分钟/小时级，不引入新平台/新层）

## 2. PAGNI 候选清单（按优先级）

### 2.1 P0：统一的“用户操作审计（Audit Events）”落库

现状证据：

- 现有日志更多偏“运行日志/账号变更日志”，未见通用的操作审计模型（全库未搜到 audit 模型定义）。

PAGNI 现在最小实现（尽量少代码）：

- 新增表 `audit_events`（建议字段）：
  - `id`
  - `actor_id`（操作者）
  - `action`（动作：create/update/delete/...）
  - `target_type` / `target_id`
  - `request_id`
  - `created_at`
  - `metadata`（jsonb，严禁写入敏感数据）
- 新增一个极小 helper（函数级别即可，不要再建一层 service）：
  - 在“写操作边界”显式调用（用户/凭据/标签/实例等高风险写路径优先）

未来能避免的代码膨胀：

- 避免后期为合规/追责在几十个写接口里补“日志拼装 + 统一字段 + 回填脚本”
- 避免为了“谁改了什么”再加第二套表/索引/导出工具链

风险：

- DB 写压力上升（但可控）
- `metadata` 可能误写敏感信息（需要明确 allowlist）
- 事务边界要明确（建议同事务：业务失败则审计也回滚）

验证步骤：

- 做 1~2 个典型写操作（新建标签/禁用用户/更新凭据），确认 audit_events 记录写入且字段正确
- 触发一次失败写操作，确认没有“业务失败但审计成功”的半落库

备注（仓库硬约束）：

- **迁移脚本禁止修改历史版本**：必须新增 migration（不要改 `migrations/versions/20251219161048_baseline_production_schema.py`）

### 2.2 P1：为“会被更新的表”补 `updated_at`（否则未来监控/排序必返工）

现状证据：

- `users`：只有 `created_at`，没有 `updated_at`（`app/models/user.py:1`）
- `sync_instance_records`：只有 `created_at`，状态/统计会更新但无更新时间（`app/models/sync_instance_record.py:1`）

PAGNI 现在最小实现：

- 给两表新增 `updated_at`
- 更新点采用最小策略二选一（不要两套都上）：
  1) ORM `onupdate=time_utils.now`（最少改动）
  2) 在 `start_sync/complete_sync/fail_sync` 等状态流转方法里显式赋值（可读性更强）

未来能避免的代码膨胀：

- 避免后续要做“最近修改用户/同步卡住检测/重试”时再加字段 + 回填脚本 + 兼容分支

风险：

- 存量数据回填口径要定（可以用 `created_at` 或现有时间字段兜底）
- 若更新频繁，索引策略要谨慎（先不加索引也可以）

验证步骤：

- 更新用户字段（角色/启用状态），确认 `updated_at` 变化
- 跑一次同步流程，确认 record 的 `updated_at` 随状态变化更新

### 2.3 P1：`account_permission` 补 `created_at/updated_at`（权限生命周期管理迟早会用）

现状证据：

- `app/models/account_permission.py:1` 主要用 `last_sync_time/last_change_time`，缺少通用 created/updated

PAGNI 现在最小实现：

- 至少补 `created_at`
- 更建议同时补 `updated_at`，区分“首次出现”和“最近刷新”

未来能避免的代码膨胀：

- 避免未来做保留策略/清理过期/排查“首次出现时间”时新增冗余表或写回填脚本

风险：

- 历史数据回填策略需明确（可用 `last_sync_time` 兜底）

验证步骤：

- 触发一次权限同步，确认新写入记录带 `created_at`
- 再触发更新，确认 `updated_at` 更新

### 2.4 P1：request_id 打通“日志与响应封套”（否则未来排障会到处补丁）

现状证据：

- 已有 context var：`app/utils/logging/context_vars.py:5`
- structlog 会读取并写入 event：`app/utils/structlog_config.py:157`
- 但未见统一设置点（需要在 request 生命周期里 set/reset）

PAGNI 现在最小实现：

- `before_request`: 从 `X-Request-Id` 读取或生成 UUID，写入 `request_id_var`
- `after_request`: 清理 context var，避免跨请求污染
- 在成功/错误封套中附带 `request_id`（例如 `meta.request_id`）

未来能避免的代码膨胀：

- 避免之后每个异常处理/日志点都“临时补 request_id”

风险：

- 必须清理 context var，否则出现跨请求串号

验证步骤：

- 发起请求并触发错误：确认日志与响应体包含同一 `request_id`
- 再发起下一请求：确认 request_id 不复用

### 2.5 P2：API 版本化债务点（早期不收敛，未来会双轨维护）

现状证据：

- `/dashboard` 路由在某些条件返回 JSON（不在 `/api/v1` 体系内），容易形成 API 双轨

PAGNI 现在最小实现：

- 所有 JSON 统一走 `/api/v1/dashboard`
- `/dashboard` 只渲染 HTML（或转调 API）

未来能避免的代码膨胀：

- 避免 API 演进/鉴权/错误封套改两份

风险：

- 需要确认前端是否依赖 `/dashboard` 的 JSON 响应

验证步骤：

- 打开 dashboard 页面，确认网络请求只访问 `/api/v1/dashboard`

## 3. 执行建议（控制新增代码的边界）

建议把 PAGNI 限制在“基础设施/数据不可逆”的小列表：

- 审计落库（audit_events）
- timestamps（updated_at/created_at）
- request_id 贯通
- API 版本化收敛

其余内容默认仍按 reducing-entropy 的原则：能删就删，避免“提前为未来扩展”写大量抽象。

