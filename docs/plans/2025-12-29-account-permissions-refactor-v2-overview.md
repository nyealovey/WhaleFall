# 账户权限重构 v2 总览(已弃用)

> 状态: 草稿  
> 创建: 2025-12-29  
> 更新: 2025-12-29  
> 本文是“总览/结论版”，细节分别见：  
> - `docs/plans/2025-12-29-account-permission-storage-v2.md`（权限存储 v2：快照真源 + 迁移策略）  
> - `docs/plans/2025-12-29-account-classification-dsl-v2.md`（账户分类 DSL v2：Facts 层 + capabilities + AST）  
> 说明: 本文已弃用, 请以 `docs/plans/2025-12-30-account-permissions-refactor-v3.md` 为准.

## 1. 摘要(这次重构的结论)

### 1.1 存储结论：权限真源改为“版本化快照”

- 在 `account_permission` 表新增：
  - `permission_snapshot`(jsonb)：权限快照真源（可扩展、可追溯）
  - `permission_snapshot_version`(int)：快照结构版本
- 迁移策略：**阶段 1 双写 → 阶段 2 切读（快照优先、旧列回退）→ 阶段 3 回填 + 删旧列**（全程可回滚）。

### 1.2 分类结论：跨 DB 统一用 DSL v2（但保留 legacy 过渡）

- 引入三层：
  - **Raw Snapshot**（permission_snapshot：用于展示/追溯）
  - **Facts**（统一事实层：供规则评估使用）
  - **DSL v2**（JSON AST + version：统一评估引擎）
- 规则存储升级：在 `classification_rules` 增 `dsl_expression(jsonb)` 等字段；评估链路 **优先 DSL v2，否则回退 legacy**，支持灰度迁移。

### 1.3 已确认的关键决策（你刚刚问的“结论”）

1) `capabilities` 维护方式：**代码常量维护（A）**  
2) 新 db_type 接入策略：**必须同步补齐高级模式（B）**（不能只上“通用能力分类”）  
3) DSL 写法：标签式谓词 **`has_capability("GRANT_ADMIN")`**  
4) 权限细化粒度(更新)：分类/DSL/规则 UI **不做表/对象级**；统一建模到 `global/server/database`。Oracle 表空间“删除/管理”属于 **server scope 系统权限**（例如 `DROP TABLESPACE`），必须纳入可配置/可评估范围  
5) 本期 capabilities 最小集合：**`SUPERUSER` + `GRANT_ADMIN`**  
6) `GRANT_ADMIN` 严格口径：**仅“实例级/广义授权能力”**（排除仅对象 owner 范围内 grant）  
7) 展示页：需要展示 schema/table/object 明细（来源为 raw snapshot）  
8) `tablespace_quotas`：不参与规则评估，也不用于页面展示  
9) PostgreSQL 表空间管理/使用类权限：保留，并归入 `server` scope（参考 Oracle）  

> 说明：Doris 仅为规划，本期不纳入实现；对应草案已标记为 Backlog：`docs/plans/2025-12-29-dbtype-doris-onboarding.md`。

---

## 2. 为什么现状不可扩展（当前痛点）

现状是“按 db_type 拆固定字段/固定 JSON 列”存权限，导致：

- 新增 db_type = 改表 + 改硬编码字段清单 + 改多处 service/DTO/UI（扩展路径不闭环）
- 权限模型割裂：同一语义在不同 DB 落到不同列/不同 key，适配层越来越厚
- 结构稀疏：大部分列长期 NULL，迁移/演进成本越来越高
- 分类链路隐藏 bug：UI 能配但后端不生效；采集字段落库丢；`or` 默认值回退导致规则语义漂移

---

## 3. 新架构总览

### 3.1 Permission Snapshot（存储真源）

`permission_snapshot` 存“整份权限快照”，并约定：

- 标准化的通用 categories：`global_privileges` / `server_permissions` / `database_privileges` / `roles` / `type_specific` / `errors`
- DB 专有字段：先落 `extra.*`（用于展示/追溯），必要时再标准化提升为顶层 category

展示侧与分类侧共享同一份快照来源，避免“双真源”。

### 3.2 Facts（统一事实层）

从 snapshot 里提取一份**稳定的、跨 DB 的 facts**，包括：

- `capabilities: set[str]`（例如 `SUPERUSER` / `GRANT_ADMIN`）
- `roles: set[str]`
- `privilege_grants: list[PrivilegeGrant]`（scope 仅 `global/server/database`）
- `attrs`（来自 `type_specific` 的少量可比较字段）

> 重点：Facts 层是“规则评估唯一输入”，用于隔离各 DB 字段名差异与细节噪声。

### 3.3 DSL v2（规则表达 + 评估）

- DSL 采用 JSON AST（可版本化、可校验、可 fail-closed）
- UI 输出 AST（短期可视化构建器；不做自然语言/文本编辑器）
- evaluator 对未知 fn/非法参数 **fail-closed**，避免误分类

---

## 4. 展示（UI）策略：避免“可选项与评估不一致”

### 4.1 单一真源：PermissionConfig

规则 UI（高级模式）里“可选择的角色/权限项”，必须来自 `permission_configs`（按 `db_type + category`），并保证：

- UI 能选到的项，后端 Facts/DSL 必须能消费
- 采集能拿到的数据，落库必须保留（至少进入 snapshot/extra）

### 4.2 展示两层视图

- **Raw view**：直接展示 snapshot（含 `extra.raw_*`），用于排障与可追溯
- **Normalized view**：展示 facts + capabilities（并可展示“capability 触发原因”）

---

## 5. 分期建议（不实现也能拆解清晰）

- Phase 1（存储）：加 `permission_snapshot*`，同步流程双写（旧列 + snapshot）
- Phase 2（展示/读取）：展示与 API 优先读 snapshot，旧列仅回退；补齐“Raw/Normalized”展示
- Phase 3（分类引擎）：引入 Facts + DSL v2，引擎优先 DSL；保留 legacy 规则回退
- Phase 4（规则统一，另起一期）：把既有 legacy 规则逐步迁移为 DSL v2，完成后删除 legacy 分支
- Phase 5（收敛）：回填历史数据，删除旧权限列与硬编码字段清单

---

## 6. 展示边界（已确认）

- **分类/DSL/规则 UI**：只支持 `global/server/database`（PostgreSQL/Oracle 表空间管理类权限归入 `server` scope 参与评估；不细化到具体表空间名）  
- **展示**：需要展示 schema/table/object 明细（来自 raw snapshot，不参与 DSL 评估）；`tablespace_quotas` 不展示
