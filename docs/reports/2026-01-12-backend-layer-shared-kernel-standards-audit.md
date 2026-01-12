# 后端分层标准 vs Shared Kernel 标准一致性评审（2026-01-12）

## 0. 范围与输入

### 标准文件（本次评审依据）

- `docs/Obsidian/standards/backend/layer/README.md`
- `docs/Obsidian/standards/backend/layer/*.md`（API / Routes / Services / Repository / Models / Tasks / Schemas / Settings / Infra / Utils / Constants / Types / Forms-Views）
- `docs/Obsidian/standards/backend/shared-kernel-standards.md`

### 代码扫描范围（用于验证“边界跨越/违规现象”）

- `app/core/**`
- `app/utils/**`
- `app/infra/**`, `app/scheduler.py`
- `app/routes/**`, `app/api/**`
- `app/services/**`, `app/repositories/**`, `app/models/**`
- `app/schemas/**`
- `app/tasks/**`
- `app/forms/**`, `app/views/**`

### 方法说明

- **标准对照**：提炼每层「职责边界 / 依赖规则 / 例外条款」后交叉比对。
- **静态扫描**：用 `rg -n` 按标准提供的门禁口径扫描（例如 `Model.query`、`db.session`、跨层 import）。
- **抽样阅读**：对少数“看起来有歧义/例外”的模块做上下文确认（例如 tasks 的事务提交点、shared-kernel-like utils 的依赖）。

---

## 1. 结论摘要（TL;DR）

- **整体一致性：较高。** 分层标准（Routes/API/Services/Repository/Models/Tasks/Schemas/Settings/Infra/Utils）在“禁止跨层依赖、禁止 Routes/API 直接查库、禁止 Repository commit、shared kernel 不反向依赖业务层”等方面口径一致，并且代码扫描结果也基本符合。
- **主要问题集中在“边界定义不够精确/索引不完整”：**
  1) `shared-kernel-standards.md` 的“不得引入 HTTP/DB 概念”表述过宽，和仓库现状（`app/core/constants` 存在 HTTP 常量、`app/core/types` 存在 ORM 相关类型辅助）存在张力。
  2) `shared-kernel-standards.md` 关于 “re-export” 的一句话存在语义自相矛盾，易误导使用方。
  3) `layer/README.md` 的依赖方向图未覆盖 `Schemas/Settings/Infra`，会让读者误判真实依赖拓扑。
  4) “事务边界归属”在 `Services` 与 `Tasks` 的描述上存在重叠，需要补充**优先级与适用场景**。

---

## 2. 标准冲突 / 不一致点（含影响与建议）

> 说明：这里的“冲突”包含两类：  
> - **标准之间的硬冲突/口径不一致**（读者按文档做会左右互搏）  
> - **标准与仓库现实不一致**（文档描述与现存代码/结构不匹配，导致评审口径难落地）

### 2.1 Shared Kernel 的“HTTP/DB 概念禁止”表述过宽（标准 vs 仓库现实不一致）

- **修订前标准（问题来源）：** `docs/Obsidian/standards/backend/shared-kernel-standards.md`
  - “MUST NOT: 引入 HTTP/Flask/Werkzeug 概念 …”
  - “MUST NOT: 引入数据库/事务概念 … ORM query …”
- **仓库现实：**
  - `app/core/constants/__init__.py:3,15,31-34` 明确把 HTTP 常量纳入 `app/core/constants`（`HttpHeaders/HttpMethod/HttpStatus`）。
  - `app/core/types/orm_kwargs.py:1-6` 明确存在面向 ORM（SQLAlchemy）建模的类型辅助（虽无 ORM import，但语义上强相关）。
- **影响：**
  - 如果把“HTTP/DB 概念”按字面理解，当前 `app/core/constants` / `app/core/types` 的一部分内容将被判定为违规，从而导致评审结论不稳定。
  - 也会直接影响 shared-kernel-like utils 的“纯度”界定（见 2.4）。
- **建议（选一条路线，写进 shared kernel 标准并统一口径）：**
  1) **收敛定义（推荐）**：把禁止条款改为“不得依赖 Flask/Werkzeug request context/Response，不得包含错误→HTTP status 映射，不得触达 `db.session`/Repository，不得包含会触发 I/O 的 DB/HTTP 行为”；并明确“协议级常量（headers/method/status enum）与 type-only 结构可在 `app/core/*` 存在”。
  2) **严格隔离**：把 HTTP 常量从 `app/core/constants/**` 移出（例如迁移到 `app/utils/**` 或 `app/infra/**`），把 ORM typed helpers 移出 `app/core/types/**`（例如迁移到 `app/repositories/**` 或单独的 `app/infra/types/**`），让 shared kernel 真正不出现任何 HTTP/DB 语义。

> [!done] 已执行（2026-01-12）
> 已按「1) 收敛定义」更新 `docs/Obsidian/standards/backend/shared-kernel-standards.md` 的“职责边界”条款（见该文件 `### 1) 职责边界`），将“概念禁止”收敛为“HTTP 框架运行时/DB 事务边界/I/O 禁止”，并补充协议/契约层常量与 type-only 结构的允许范围。

### 2.2 “re-export” 语句存在自相矛盾（标准内部不一致）

- **现有标准：** `docs/Obsidian/standards/backend/shared-kernel-standards.md:42-43`
  - “不提供 `app.core.constants` / `app.core.types` 的 re-export；所有调用方必须改用 `app.core.constants` / `app.core.types`。”
- **问题：**
  - 前半句与后半句引用的 import 路径完全一致，导致读者无法判断“禁止的旧入口”到底是什么。
  - 推测作者本意是：**不允许在 `app/core/__init__.py` 做跨包 re-export**（例如 `from app.core import HttpHeaders`），而应该让调用方显式 import `app.core.constants` / `app.core.types`。
- **建议：**
  - 把该句改为更可执行的版本，例如：
    - “禁止在 `app/core/__init__.py` 进行 re-export；调用方必须显式 import `app.core.constants.*` / `app.core.types.*`。”
    - 或列出“旧入口 → 新入口”的映射（如果历史上存在 `app.constants` / `app.types` 等旧模块）。

> [!done] 已执行（2026-01-12）
> 已按上述建议更新 `docs/Obsidian/standards/backend/shared-kernel-standards.md` 的 `> [!important]` 条款，明确禁止在 `app/core/__init__.py` 做 re-export，并要求调用方显式 import `app.core.constants.*` / `app.core.types.*`。

### 2.3 `layer/README.md` 依赖方向图未覆盖 `Schemas/Settings/Infra`（索引不完整 → 边界误解）

- **现有标准：** `docs/Obsidian/standards/backend/layer/README.md` 的 Mermaid 图只展示了 Routes/API/Tasks/Services/Repositories/Models/FormsViews/Utils/SharedKernel/Constants/Types。
- **问题：**
  - `Schemas`、`Settings`、`Infra` 已经有独立标准（`schemas-layer-standards.md`、`settings-layer-standards.md`、`infra-layer-standards.md`），但在“依赖方向(概览)”中缺失，会误导新同学认为这些不是层的一部分或不重要。
  - 典型例子：Routes/API 强制使用的 `safe_route_call` 实际落在 `app/infra/route_safety.py`，但依赖图没有表达 Routes/API 对 Infra 的依赖。
- **建议：**
  - 更新图或至少补充一段文字：把 `Infra/Settings/Schemas` 加入依赖方向概览，并明确它们的典型被依赖方（例如 `Services -> Schemas`、`Routes/API/Tasks -> Infra`、`create_app -> Settings`）。

> [!done] 已执行（2026-01-12）
> 已更新 `docs/Obsidian/standards/backend/layer/README.md` 的 Mermaid 依赖方向图，补齐 `Schemas/Settings/Infra` 节点与常用依赖方向。

### 2.4 shared-kernel-like utils 的“纯度”边界不清（标准之间隐含冲突）

- **现有标准：**
  - `docs/Obsidian/standards/backend/shared-kernel-standards.md:38-40,75-77` 说明 shared-kernel-like utils 位于 `app/utils/**`，但必须保持“纯”，并举例“boundary tools”可能依赖 `structlog`。
  - `docs/Obsidian/standards/backend/layer/utils-layer-standards.md:33-41` 把 utils 分为“纯工具(shared-kernel-like)”与“边界工具”。
- **仓库现实：**
  - `app/utils/time_utils.py` 作为 shared-kernel-like utils（文档点名示例）曾依赖 `structlog`（现已移除）。
- **影响：**
  - 只要标准口径不清，未来新增 shared-kernel-like utils 时仍可能重复引入 `structlog` 造成评审争议与口径漂移。
- **建议：**
  - 在 shared kernel / utils 标准中明确：`structlog` 是否允许出现在“纯工具”里？
    - 若允许：写清楚“允许用于纯函数的 best-effort warning，但不得读取 request context / 不得做 I/O”。
    - 若不允许：要求把日志注入上层（通过参数或 callback），或改用标准库 `logging` 并保持无全局副作用。

> [!done] 已执行（2026-01-12）
> 已对 `app/utils/time_utils.py` 执行“最简方案”落地：移除 `structlog` 与 `LOGGER.warning(...)`，保持 silent best-effort 返回值语义不变（失败返回 `None`）。

### 2.5 事务边界归属：Services vs Tasks 的优先级需要补齐（标准之间重叠）

- **现有标准：**
  - `docs/Obsidian/standards/backend/layer/services-layer-standards.md:31-32,85-87` 强调“commit/rollback 不应分散”“事务边界由 Service 控制”。
  - `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:48` 允许 tasks 作为事务边界入口阶段性 `commit/rollback`。
- **影响：**
  - 对长任务（批量同步/采集）而言，确实需要分段提交；但标准需要明确：
    - 任务是否可以“覆盖”service 的事务边界？
    - 被 tasks 调用的 service 是否必须做到“绝不 commit”（避免重复提交/嵌套事务混乱）？
- **建议：**
  - 在两份标准中增加一致口径的“优先级条款”：
    - Web 请求写路径：Service 是事务边界入口。
    - 长任务/批处理：Tasks（或 Infra worker）可以作为事务边界入口；此时被调用的 Service/Runner 必须不 `commit`，只做 `flush`/状态变更，提交由 tasks 统一掌控。

> [!done] 已执行（2026-01-12）
> 已分别更新 `docs/Obsidian/standards/backend/layer/services-layer-standards.md` 与 `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md`，补齐“事务边界优先级（Web vs Tasks）”条款并统一口径。

---

## 3. 边界跨越 / 违规现象（代码扫描结果）

### 3.1 未发现的违规（按标准门禁口径扫描）

以下扫描项均未发现匹配（未列出输出表示 0 matches）：

- `app/core/**` 未发现反向依赖业务层（`app.(api|routes|tasks|services|repositories|models|forms|views|settings|infra|schemas)`），也未发现 `flask/werkzeug/db.session/Model.query` 等敏感依赖。
- `app/core/constants/**` 未发现依赖 `app.core.types` / `app.core.exceptions`（符合 `constants-layer-standards.md` 与 shared kernel 依赖规则）。
- `app/core/types/**` 未发现依赖 `app.models` / `db.session` / `app.core.exceptions`（符合 `types-layer-standards.md`）。
- `app/utils/**` 未发现依赖 `app.models/app.services/app.repositories/app.routes/app.api` 或 `db.session`（符合 `utils-layer-standards.md`）。
- `app/routes/**` 未发现 `Model.query` / `db.session`（符合 `routes-layer-standards.md`）。
- `app/api/**` 未发现 `Model.query` / `db.session`（符合 `api-layer-standards.md`）。
- `app/schemas/**` 未发现对 `models/db/services/repositories/routes/api` 的依赖（符合 `schemas-layer-standards.md`）。
- `app/repositories/**` 未发现 `db.session.commit()`（符合 `repository-layer-standards.md`）。

### 3.2 需要解释的“疑似边界跨越”（取决于标准对概念边界的定义）

> 这些点目前更像“标准口径需要澄清”，而不是明确的实现错误。

- `app/core/constants/__init__.py:3,15,31-34` 把 HTTP 常量纳入 shared kernel 的 constants（与 `shared-kernel-standards.md:50` 的字面含义存在张力）。
- `app/core/types/orm_kwargs.py:1-6` 在 shared kernel 的 types 中引入 ORM（SQLAlchemy）强相关的类型辅助（与 `shared-kernel-standards.md:51` 的字面含义存在张力）。
- `app/utils/time_utils.py` 曾依赖 `structlog`（现已移除）；标准口径仍建议明确，避免后续回归。

### 3.3 事务边界实践的现状（与标准重叠点相关）

- `app/tasks/capacity_collection_tasks.py:41-88` 任务内多处 `db.session.commit()/rollback()`，体现 tasks 作为长任务事务边界入口的实践（符合 `tasks-layer-standards.md:48`，但需要和 `services-layer-standards.md:85` 的表述统一优先级）。

---

## 4. 边界定义不清晰点（建议在标准中补齐）

1) **Shared Kernel 的“HTTP/DB 概念”到底禁止到什么粒度？**  
   建议把禁止项从“概念”改成“依赖/副作用/适配层”维度，避免把协议级常量也判为违规。

2) **Schemas 校验发生在谁的边界？**  
   `schemas-layer-standards.md:42` 的“进入 Service 前”容易被理解为 Routes/API 调 schema；但 Routes/API 标准的依赖清单并未显式包含 `app.schemas.*`。建议明确：  
   - Service 公开方法的“入口处”必须 `validate_or_raise`；Routes/API 只做原始参数读取与最小规整。

3) **Routes(JSON) vs API(v1) 的定位边界**  
   两者都承载 JSON 封套与 `safe_route_call`，但“何时新增 endpoint 应选 Routes 还是 API”缺少决策表。建议按“面向 UI 内部 vs 对外集成、是否需要 OpenAPI、版本化策略”等维度写清楚。

4) **Infra vs Utils 的边界**  
   两者都可能承载“失败隔离/兜底/统一包装”。建议加一条简明准则：  
   - 有副作用/事务边界/线程/锁/worker → `app/infra/**`  
   - 纯函数/轻量转换（无 request/db）→ `app/core/**` 或 shared-kernel-like `app/utils/**`

5) **Layer README 的依赖方向图应覆盖真实层集合**  
   建议补 `Schemas/Settings/Infra`，并明确它们的被依赖方向。

---

## 5. 建议的后续行动（可执行）

1) 修订 `docs/Obsidian/standards/backend/shared-kernel-standards.md`：
   - 收敛“HTTP/DB 概念禁止”的表述粒度（见 2.1 建议）。
   - 修正 `re-export` 句子的语义（见 2.2 建议）。
   - 明确 shared-kernel-like utils 对 `structlog` 的态度（见 2.4 建议）。

2) 更新 `docs/Obsidian/standards/backend/layer/README.md`：
   - 将 `Schemas/Settings/Infra` 纳入依赖方向概览或补充文字说明（见 2.3）。

3) 统一“事务边界优先级”：
   - 在 `services-layer-standards.md` 与 `tasks-layer-standards.md` 补充一致的优先级说明（见 2.5）。
