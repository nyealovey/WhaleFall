# 后端 Repository / Serializer 分层重构方案（开发期直迁 / 小步可验证）

> 文档目的：将“查询组织（Query）”与“序列化（JSON 输出）”从 `routes/services/utils` 的散落实现中剥离出来，形成清晰边界：`routes → services → repositories → models` 与 `serializers`（纯转换）。
>
> 生成日期：2025-12-24

---

## 1. 背景与问题定义

当前后端存在三类典型债务：

1) **查询组织散落**：列表/详情接口在 routes 中直接拼 SQLAlchemy 查询、拼 join/filter/order/paginate，导致复用与测试困难。
   - 证据：`app/routes/instances/manage.py:130`（过滤/排序/标签 join 等查询逻辑集中在 route 文件内）。

2) **“工具层”承载业务语义**：部分 `utils` 直接访问 DB 并返回业务数据，边界模糊（后续难以判断属于基础设施还是业务策略）。
   - 证据：`app/utils/query_filter_utils.py:1`（“统一筛选器数据访问工具”本质是查询/读模型能力）。

3) **序列化契约不稳定**：不同路由对同一概念（items/total/pages 等）输出不完全一致，前端长期存在兜底解析（`response?.data || response || {}`，以及 items/users 等容错）。
   - 证据：`app/static/js/modules/views/auth/list.js:203`、`app/static/js/modules/views/tags/index.js:120`（前端解包/兜底频繁出现）。

本方案聚焦 P2-1：**引入显式 `repositories/serializers` 目录与边界**，以小步方式迁移高复杂页面（优先 instances/ledgers），并通过测试与门禁“可验证”地推进。

---

## 2. 目标与非目标

### 2.1 目标（必须达成）

- **边界清晰**：routes 不再直接拼复杂 SQLAlchemy 查询；序列化不再散落在 routes/services；utils 不再承担业务读模型。
- **小步可回退**：每次迁移只改一个端点/一个域的一小段链路，必要时以 `git revert` 回退单个 PR，禁止“一次性大爆改”。
- **可验证**：为迁移路由建立 HTTP 契约测试（schema/字段稳定性），并配合现有门禁脚本。
- **不做兼容/兜底**：不引入“旧字段别名/双读双写/旧实现开关/影子对比”等兼容层；如需调整响应字段，直接同步更新前端与测试，并在 PR 描述中明确列出变化点。

### 2.2 非目标（本阶段不做）

- 不在本方案内一次性调整 `safe_route_call` 的“统一 commit”策略（现状保留，后续单独 ADR 讨论）。
- 不在本方案内重写所有 routes（只选 Top 2~3 个高复杂/高频路由做样板）。
- 不在本方案内引入新的 ORM/序列化框架（保持 SQLAlchemy 与现有 `to_dict()`/字典序列化风格）。

---

## 3. 目标架构：分层定义与依赖方向

### 3.1 分层职责（强约束）

#### Routes（`app/routes/**`）

- 只做：参数解析/权限校验/调用 service/返回 `jsonify_unified_*`。
- 不做：
  - 不直接拼复杂 Query（允许 `Model.query.get_or_404` 这类最小读取）。
  - 不做序列化拼装（不再手写 `items = [...]` 的大量 dict 逻辑）。
- 事务：由 `safe_route_call` 统一处理（现状保留）。

#### Services（`app/services/**`）

- 只做：业务编排（选择 repository、调用多个 repository、做跨实体策略）、事务边界（未来可演进）。
- 不做：
  - 不输出 HTTP schema（不返回 Flask Response/不拼 `success/message`）。
  - 不负责“复杂 Query 组装细节”（交给 repositories）。
- 输入输出：
  - 输入：已规范化的参数对象（dataclass/TypedDict），避免 `dict[str, Any]` 扩散。
  - 输出：领域结果对象（ORM 对象、DTO、或聚合结果 dataclass），由 serializers 转为 JSON。

#### Repositories（新增：`app/repositories/**`）

- 只做：Query 组装与 DB 读取（**不 commit**，不做序列化）。
- 建议约定：
  - 每个 repository 文件只负责一个实体/一个聚合视角（例如 `instances_repository.py`、`tags_repository.py`）。
  - 返回值尽量稳定：要么返回 ORM 实体，要么返回固定结构 DTO（dataclass/TypedDict），避免“半 ORM 半 dict”。

#### Serializers（新增：`app/serializers/**`）

- 只做：对象 → JSON dict（**不访问 DB**，不做 commit/flush）。
- 统一约束：
  - 输入类型明确（ORM/DTO），输出类型使用 `app/types/structures.py:JsonDict/JsonValue`。
  - 严禁在 serializer 中再查询 DB（避免隐式 N+1）。

### 3.2 依赖方向（允许/禁止）

允许：
- `routes → services`
- `services → repositories`
- `repositories → models/db`
- `services → serializers`（可选：service 只返回 DTO，由 route 调 serializer）
- `routes → serializers`（可选：route 调 serializer，把 service 返回值转 JSON）

禁止：
- `repositories → serializers`（repository 不负责输出）
- `serializers → repositories/models 查询`（serializer 不做 IO）
- `routes → repositories`（除非“临时桥接”，且必须在同一 PR 内清理）
- `utils → models/db`（仅保留基础设施级别例外；现有 `query_filter_utils` 需迁移）

---

## 4. 目录结构与命名规范（落地约定）

### 4.1 新增目录

建议新增：

```text
app/
  repositories/
    __init__.py
    instances_repository.py
    tags_repository.py
    ledgers/
      __init__.py
      database_ledger_repository.py
  serializers/
    __init__.py
    instances_serializer.py
    tags_serializer.py
    ledgers/
      __init__.py
      database_ledger_serializer.py
```

说明：
- 若某域已有 service 子目录（如 `services/ledgers/`），repository/serializer 也可按域建子目录，减少单文件膨胀。
- 命名采用完整单词 snake_case；避免缩写。

### 4.2 类型治理（强制）

- 新增跨模块共享的结构类型（DTO/TypedDict/Protocol）必须放在 `app/types/`（遵守仓库规范）。
  - 示例：`app/types/listing.py`（分页参数/响应）、`app/types/instances.py`（实例列表 DTO）。
- 禁止在业务模块临时声明 `dict[str, Any]` 结构作为公共 API。

---

## 5. 迁移策略（开发期直迁：不保留双实现）

### Phase 0：建立契约与基准（先锁行为）

目标：先把“行为”锁住，再做结构迁移；避免“重构顺手改坏输出结构”。

1) 为选定路由建立 **HTTP 契约测试**（建议先覆盖 2 个端点）：
   - `GET /instances/api/instances`（实例列表）
   - `GET /databases/api/ledgers`（台账/列表类）
2) 契约断言内容（最小集合）：
   - 响应 envelope 存在：`success/error/message/timestamp`
   - data 内关键字段存在：`items/total/page/pages/limit`（若现有接口不同，则以现状为准）
   - items 中关键字段集合稳定（建议“必须包含字段”，避免脆弱的全量快照）
3) 门禁脚本全绿（不得新增命中）：
   - `./scripts/code_review/error_message_drift_guard.sh`
   - `./scripts/code_review/pagination_param_guard.sh`

### Phase 1：引入目录与最小样板（只迁移 1 个端点）

以实例列表为样板，推荐迁移路径：

1) 新增 repository：`InstancesRepository.list_instances(filters) -> Pagination[Instance] | DTO`
2) 新增 serializer：`serialize_instance_list_item(instance, metrics, tags) -> JsonDict`
3) 新增 service：`InstanceListService.list(filters) -> InstanceListResult`
4) routes 仅保留：
   - 参数解析（尽量用 dataclass/TypedDict）
   - 调用 service
   - `jsonify_unified_success(data=...)`
5) 同一 PR 内**删除旧实现**（routes 内旧 Query/旧序列化拼装），避免双维护。

### Phase 2：扩大覆盖面（按域迁移）

优先顺序建议：
1) `instances` 域（列表/详情的 read 链路）
2) `ledgers` 域（台账类多筛选、多 join）
3) `tags`/`credentials`（相对标准 CRUD，作为收尾）

### Phase 3：清理 utils 的“业务读模型”

- 将 `app/utils/query_filter_utils.py` 的 DB 读能力迁移到对应 repository，并在迁移完成后删除/降级该 util（仅保留纯函数部分）。

---

## 6. 发布与回退策略（开发期：不做开关/不做兼容）

- **不引入迁移开关**：routes 内不保留 `if flag: new else: old` 的双路径；迁移完成即只剩新实现。
- **回退方式**：以 PR 粒度控制风险，问题出现时直接 `git revert <PR commit>` 回退到迁移前状态（要求每次 PR 只迁移 1 个端点/1 个链路片段）。
- **字段变化管理**：若确需调整响应字段/命名，必须同步修改前端与测试；同时更新相关文档（例如 `docs/standards/backend/error-message-schema-unification.md` 若涉及 envelope 变化）。

---

## 7. 验证方案（单测 / 契约 / 静态 / 运行时）

### 7.1 单测建议（优先级从高到低）

1) **Serializer 单测（纯函数）**：输入固定对象/DTO，断言输出字段集合与默认值处理（最稳定、成本最低）。
2) **Repository 单测（轻量）**：不建议对 SQL 字符串做强断言；建议用 sqlite memory + 最小 fixture 验证过滤/排序是否生效（或只覆盖关键分支）。
3) **Service 单测**：mock repository，验证编排与边界（不关心 SQLAlchemy 细节）。

### 7.2 routes 契约测试（必须）

- 目标：锁住 HTTP schema，防止重构把字段“改没了/改名了”。
- 建议断言：
  - `success/error/message/timestamp` 存在
  - `data.items` 为 list
  - `data.total/page/pages` 为数字
  - 关键字段集合包含（而非全量等于）

### 7.3 静态门禁（必须）

- Ruff：`./scripts/ruff_report.sh style` 或 `ruff check <files>`
- Pyright：`npx pyright --warnings <files>`
- 门禁脚本（不得新增命中）：
  - `./scripts/code_review/error_message_drift_guard.sh`
  - `./scripts/code_review/pagination_param_guard.sh`

### 7.4 运行时验证清单（上线前）

- 实例列表页：筛选、排序、分页、标签筛选组合查询；确认 total/pages 与预期一致。
- Ledgers 列表页：多筛选组合 + 分页；确认前端不再触发“解包兜底”分支（可通过浏览器网络响应与 console 行为观察）。
- 任务/同步链路：与本方案无直接变更时，仅回归“读链路未受影响”。

---

## 8. “样板迁移”建议：以 Instances 列表为第一落点

### 8.1 为什么选它

- 查询复杂度高：包含搜索、状态、标签 join、last_sync_time 子查询、分页/排序（`app/routes/instances/manage.py:130` 起）。
- 前端依赖强：实例列表是核心入口，能快速暴露 schema 漂移问题。

### 8.2 目标拆分（按 PR 粒度）

1) 抽 repository：把 `_apply_instance_filters/_apply_instance_sorting/_collect_instance_metrics` 的 Query/聚合读取迁移到 `InstancesRepository`
2) 抽 serializer：把 instance 列表 item 的 dict 拼装迁移到 `InstancesSerializer`
3) 收敛 route：route 仅保留参数解析 + 调 service + 返回 unified response

每一步都建议独立 PR（更易 review、更易回退）。

---

## 9. 风险矩阵与缓解（只列高风险）

| 风险 | 场景 | 缓解 |
|---|---|---|
| N+1 查询 | serializer 触发懒加载或 service 忘记预加载 | serializer 禁止 DB IO；repository 统一预加载策略（`selectinload/joinedload`） |
| schema 漂移 | items 字段名/分页字段变化导致前端异常 | 先上 routes 契约测试；如需字段调整，同 PR 更新前端与测试 |
| 事务边界混乱 | service/repo 内部 commit 与 `safe_route_call` commit 冲突 | repository/service 禁止 commit；由 `safe_route_call` 统一（现状） |
| 回退成本高 | 一次性搬迁多个端点导致 revert 影响面大 | 每次 PR 只迁移 1 个端点/1 个链路片段；必要时直接 `git revert` |

---

## 10. 验收标准（完成定义）

当以下条件满足时，可认为 P2-1 分层重构“完成第一阶段”：

1) `app/repositories/**` 与 `app/serializers/**` 建立并被至少 1 个高复杂端点使用（建议 instances 列表）。
2) 对该端点的 routes 契约测试通过，且在 CI/本地门禁下无新增违规。
3) 迁移端点的 routes 内旧 Query/旧序列化拼装已删除，routes 仅保留“参数解析 → 调 service → unified response”。

