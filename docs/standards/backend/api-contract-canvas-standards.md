# [Deprecated] API Contract 画布标准(SSOT)

> 状态: Deprecated
> 负责人: WhaleFall Team
> 创建: 2026-01-07
> 更新: 2026-01-08
> 范围: (legacy) `docs/Obsidian/canvas/**-api-contract.canvas`
> 替代:
> - `./api-contract-markdown-standards.md`
> - `../../Obsidian/API/accounts-api-contract.md`

## 0. 废弃说明

本规范已废弃: 后续 API contract 统一采用 Obsidian Markdown(`docs/Obsidian/API/**-api-contract.md`) 维护, 不再将 `.canvas` 作为 SSOT.

下方内容仅作为历史记录保留, 不再作为强制标准执行.

## 1. 目的

- 为 "API 路径清单" 提供单一真源(single source of truth, SSOT), 避免 Markdown 表格与代码实现漂移.
- 让评审者在 30 秒内确认: 新增/删除/改名的 endpoint 已同步更新契约.

## 2. 适用范围

- MUST: 所有对外 JSON API(`/api/v1/**`) 的 method + path 清单.
- MAY: 仅用于索引与审查, 详细 schema 仍以 OpenAPI 为准.
- MUST NOT: 将页面路由(HTML)与内部调试路由纳入本规范.

## 3. 规则

### 3.1 单一真源

- MUST: `/api/v1/**` 的 endpoint 表(方法 + 路径)以各域的 `docs/Obsidian/canvas/**/**-api-contract.canvas` 为准.
- MUST: `docs/Obsidian/canvas/api-v1-api-contract.canvas` 仅作为索引, 不承载全量 endpoint 表.
- MUST: OpenAPI(`/api/v1/openapi.json`) 中出现的每个 operation(Method + Path) 必须至少出现在 1 个 `**-api-contract.canvas` 的表格中.
- SHOULD: 同一个 operation 只出现在 1 个 contract canvas 中; 如确需跨域重复, 必须在 `Notes` 说明原因.
- MUST NOT: 在其他 Markdown 文档重复维护 "全量 endpoint 表格". 其它文档只允许:
  - 链接到索引 canvas; 或
  - 引用 OpenAPI(`/api/v1/openapi.json`) 作为 schema 细节来源.

### 3.2 画布布局(两层)

- MUST: 每个 `**-api-contract.canvas` 必须包含 2 层内容:
  - 第一层: 3 个固定框(左/中/右).
  - 第二层: API 清单表(Endpoints).
- MUST: 第一层 3 个固定框必须一直存在, 即使没有内容也保留, 不允许省略.

第一层(固定 3 栏)的语义与颜色约定:

- 左(橙色): `统一封套/幂等/其他说明`(color: `2`)
- 中(绿色): `缓存契约`(color: `4`)
- 右(红色): `关键约束/错误`(color: `1`)

说明:

- SHOULD: 如果某栏无内容, 使用 `- (none)` 占位, 避免误解为遗漏.

### 3.3 API 清单表(Endpoints)

- MUST: 第二层必须以 Markdown 表格呈现, 且必须包含以下列(顺序固定):

`| Method | Path | Purpose | Idempotency | Pagination | Notes |`

字段说明:

- `Method`: HTTP method, 全大写.
- `Path`: 必须包含版本前缀(`/api/v1`), 使用 OpenAPI 风格参数(例如 `/api/v1/users/{user_id}`).
- `Purpose`: 端点语义(一句话), 允许引用 OpenAPI `summary`.
- `Idempotency`: 推荐写法:
  - 读: `yes (read)`
  - 写: `no` / `yes-ish`(例如 pause/resume 这类重复调用可接受)
- `Pagination`: `page/limit` / `limit/offset` / `-`.
- `Notes`: 非显性约束与迁移说明(例如 CSRF, 权限, side effects, 兼容/下线计划).

- MUST: `Path` 使用 OpenAPI 风格参数(例如 `/api/v1/users/{user_id}`), 不使用 Flask rule 风格(例如 `/api/v1/users/<int:user_id>`).
- MUST: 禁止省略列, 即使 `Pagination`/`Notes` 为空也要用 `-` 填充.

### 3.4 索引画布约束

- MUST: `api-v1-api-contract.canvas` 至少包含:
  - 指向每个域 contract canvas 的 `file` node(便于在 Obsidian 中跳转)
  - 1 个索引表格(建议字段: `Domain`/`Canvas`/`Tags`/`Operations`)
- SHOULD: 索引画布由脚本生成, 避免人工维护漂移.

### 3.5 变更流程

- MUST: 任何新增/删除/改动 endpoint 的 PR, 必须同步更新受影响的域 contract canvas.
- SHOULD: 同时校验:
  - OpenAPI schema: `uv run python scripts/dev/openapi/export_openapi.py --check`
  - Contract 覆盖率: `uv run python scripts/dev/openapi/export_api_contract_canvas.py --check`

## 4. 正反例

### 4.1 正例

| Method | Path | Purpose | Idempotency | Pagination | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | /api/v1/health/ping | ping | yes (read) | - | - |
| POST | /api/v1/instances/{instance_id}/actions/restore | restore instance | yes-ish | - | csrf required |

### 4.2 反例

- 缺少版本前缀: `/health/ping`
- 使用 Flask rule 参数: `/api/v1/users/<int:user_id>`
- 在多个 Markdown 文档里重复维护同一份全量 endpoint 表格

## 5. 门禁/检查方式

### 5.1 自动生成与校验

- 生成索引(覆盖写入): `uv run python scripts/dev/openapi/export_api_contract_canvas.py --output docs/Obsidian/canvas/api-v1-api-contract.canvas`
- 校验覆盖率(不写入): `uv run python scripts/dev/openapi/export_api_contract_canvas.py --check`

说明:

- `--check` 会对比 OpenAPI vs `docs/Obsidian/canvas/**/**-api-contract.canvas` 的表格抽取结果, 发现缺失/过期则返回非 0.
- 当 endpoint 变更导致缺失较多时, 优先补齐对应域的 contract canvas, 再生成索引.

## 6. 变更历史

- 2026-01-07: 初版, 以 `/api/v1` 路由清单为试点, 引入 contract canvas + 索引 canvas.
