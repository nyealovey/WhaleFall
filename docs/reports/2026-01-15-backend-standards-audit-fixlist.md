> Status: Draft
>
> Owner: Codex（后端标准审计员 + 代码合规审计员）
>
> Created: 2026-01-15
>
> Updated: 2026-01-15
>
> Scope:
> - Standards: `docs/Obsidian/standards/backend/**/*.md`
> - Code: `app/**/*.py`（仅此范围；不列出/不判定 `app/**` 之外任何代码问题）
>
> Source Report:
> - `docs/reports/2026-01-15-backend-standards-audit-report.md`
>
> Evidence Artifacts:
> - `docs/reports/artifacts/2026-01-15-app-or-boolop.txt`
> - `docs/reports/artifacts/2026-01-15-app-silent-except-return.txt`
> - `docs/reports/artifacts/2026-01-15-app-json-columns.txt`

# 后端标准审计 - 全量修复清单 (2026-01-15)

## 0. 判定口径（避免“清单口径漂移”）

- “违规”：仅当标准为 MUST / MUST NOT（或等价强制措辞）且证据清晰时标记。
- “疑似问题/建议改进”：SHOULD / 标准歧义 / 需要业务语义确认的点，不强判违规。
- 每条必须可回链到证据：
  - 标准侧：`docs/...:行号`
  - 代码侧：`app/...:行号`

---

## 1. 标准侧修复清单（docs）

### STD-01（P1｜标准冲突）`error` 字段语义混用风险（boolean vs string）

- 类型：标准冲突/歧义
- 证据：
  - `docs/Obsidian/standards/backend/layer/api-layer-standards.md:122`
  - `docs/Obsidian/standards/backend/layer/api-layer-standards.md:134`
  - `docs/Obsidian/standards/backend/error-message-schema-unification.md:35`
  - `docs/Obsidian/standards/backend/error-message-schema-unification.md:72`
- 问题：对外 API envelope 的 `error` 定义为 boolean，但“错误消息字段统一”示例又把 `error` 当诊断字符串，容易诱发下游写 `or` 互兜底链（且该类互兜底链在标准中被禁止）。
- 建议修复：
  1) 在 `docs/Obsidian/standards/backend/error-message-schema-unification.md` 显式声明：对外 API envelope 的 `error` 永远是 boolean；
  2) 对“诊断字符串”字段改名（例如 `diagnostic_error`），或限定其仅允许出现在内部结果对象（非对外 envelope）。
- 验证方式（标准侧）：新增/调整“正反例”并在文档中给出“可执行判据”（读者能据此判断字段是否合法出现）。

### STD-02（P1｜标准冲突）`error_code` 的对外暴露边界不清（envelope vs data payload）

- 类型：标准冲突/歧义
- 证据：
  - `docs/Obsidian/standards/backend/layer/api-layer-standards.md:146`
  - `docs/Obsidian/standards/backend/error-message-schema-unification.md:38`
  - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:74`
- 问题：对外 error envelope 禁止 `error_code`，但 internal contract best-effort 的错误结构又要求必须包含 `error_code`；当 internal contract 错误需要进入对外 `data`（例如 `data.items[]` 的单项失败信息）时口径未收敛，容易逼迫下游写 `message_code/error_code` 互兜底链。
- 建议修复：
  1) 增加一条“可执行规则”：对外 API（包括 `data`）如需机器可读错误码，统一使用 `message_code`（或明确命名空间字段，如 `internal_contract_error_code`）；
  2) 给出映射策略：internal contract 的 `error_code` 如何映射到对外 `message_code`（或明确禁止透出）。
- 验证方式（标准侧）：补充 1 个“internal contract 错误透出到 data 的示例”，并标注允许/禁止字段集合。

### STD-03（P2｜标准歧义）`parse_payload` vs schema canonicalization 职责边界重叠

- 类型：标准歧义/不可执行点
- 证据：
  - `docs/Obsidian/standards/backend/layer/api-layer-standards.md:62`
  - `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:42`
  - `docs/Obsidian/standards/backend/layer/schemas-layer-standards.md:43`
- 问题：parse_payload 与 schema 都声称负责“strip/规范化”，边界不清会在“需要保留空白/原始值”的字段上诱发实现分裂与额外 `or` 兜底。
- 建议修复：在标准中补一张职责分界表（shape-level vs semantic-level），并显式定义 `preserve_raw_fields` 的优先级。

### STD-04（P2｜标准歧义）schema 校验失败异常链路不够“开箱即用”（ValueError vs ValidationError）

- 类型：标准歧义/不可执行点
- 证据：
  - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:47`
  - `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md:48`
- 问题：文档同时要求 service 抛 `ValidationError`、schema 侧用 `ValueError` 表达校验失败，但未给出“哪一层负责捕获并转换”的最小示例，容易出现 ValueError 泄露到 route/api 导致错误封套漂移。
- 建议修复：补一段最小示例链路：pydantic validator 抛 ValueError → `validate_or_raise` 捕获 → 转换为 `ValidationError`（并说明 message_key/message_code 的走向）。

### STD-05（P2｜不可执行）Tasks 标准出现“复杂/薄”类 MUST NOT 但缺少可验证判据

- 类型：不可执行点（影响审计/评审一致性）
- 证据：
  - `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md:49`
- 问题：MUST NOT “堆叠复杂业务逻辑”缺少量化/可检验判据，导致审计无法稳定落地，进而促使实现为了“过评审”引入额外 wrapper/兜底链（反而更复杂）。
- 建议修复：给出 2~3 条可验证触发条件（示例：单任务函数 >50 行、循环内 I/O、多段事务提交等），并说明例外如何申请/如何补测试。

### STD-06（P1｜标准冲突）internal contract scope 过宽：与日志/审计类 JSON 的 version 要求冲突

- 类型：标准冲突/歧义
- 证据：
  - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`
  - `docs/Obsidian/standards/backend/structured-logging-minimum-fields.md:41`
  - `app/models/unified_log.py:65`
- 问题：internal contract 要求“长期存储的内部结构化 payload 必须包含 version”，但结构化日志的 `UnifiedLog.context` 并未版本化；若按字面执行会迫使日志 context 引入无意义 version 字段。
- 建议修复：在 internal contract 标准中增加“排除项/例外清单”，明确日志类 JSON（如 `UnifiedLog.context`）不纳入 internal contract versioning。

---

## 2. 代码侧修复清单（仅 `app/**`）

### CODE-01（P0｜违规）DB JSON 字段 `sync_details` 未做 internal contract 版本化

- 判定：违规（MUST）
- 标准依据：
  - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`
- 代码位置（写入/透传 `sync_details` 且未包含 `version`）：
  - `app/tasks/accounts_sync_tasks.py:100`
  - `app/services/capacity/capacity_collection_task_runner.py:155`
  - `app/services/accounts_sync/accounts_sync_service.py:289`
  - `app/services/sync_session_service.py:259`
- 问题：`sync_details` 当前是“无版本号的任意 dict”，一旦字段演进/重命名，下游容易被迫写 `or` 兜底链或形状适配，违背 internal contract “单入口 canonicalization + 显式版本”的约束。
- 建议修复（可落地）：
  1) 定义契约：例如 `sync_details.version=1`；
  2) 增加 adapter/normalizer 单入口（建议放 `app/schemas/internal_contracts/sync_details_v1.py`）；
  3) 写入口只写最新版本 canonical 形状；读入口对缺失/未知版本 fail-fast 或返回 best-effort 错误结构（按标准 4.1.1）；
  4) 制定退出条件并删除兼容分支：`docs/Obsidian/standards/backend/compatibility-and-deprecation.md:64`。
- 验证方式（代码侧，建议补单测）：
  - 新版写入能稳定产出 `version=1`；
  - 旧数据（无 version）可迁移/可观测，且退出条件达成后可删除兼容分支。

### CODE-02（P1｜违规）持久化 JSON（Text 存储）解析失败时 silent fallback（无任何日志/告警）

- 判定：违规（MUST NOT）
- 标准依据：
  - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50`
- 代码位置：
  - `app/models/account_classification.py:214`（`json.loads(...)` 失败直接 `return {}`）
  - `app/models/database_type_config.py:84`（`json.loads(...)` 失败直接 `return []`）
- 问题：解析失败通常意味着数据被污染或写入口径漂移；直接返回空结构会掩盖问题并诱发上层继续执行（长尾故障风险）。
- 建议修复（按业务影响二选一）：
  1) fail-fast：抛出项目异常并走统一错误处理；
  2) 显式降级：允许返回空结构，但必须记录结构化日志（包含 `fallback=true`/`fallback_reason`），并确保调用方把它当失败处理（不要继续按空结构执行业务）。
- 验证方式：补单测覆盖“脏数据/非法 JSON”场景；至少断言“不会 silent fallback”。

### CODE-03（P1｜违规）审计/变更类 JSON 字段未版本化：`AccountChangeLog.privilege_diff/other_diff`

- 判定：违规（MUST）
- 标准依据：
  - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`
- 代码位置：
  - 列定义：`app/models/account_change_log.py:50`、`app/models/account_change_log.py:51`
  - 写入：`app/services/accounts_sync/permission_manager.py:746`、`app/services/accounts_sync/permission_manager.py:747`
- 问题：DB JSON 列属于 internal payload 的适用范围；差异结构一旦演进（字段变更/条目结构调整），下游消费（API/UI/统计）容易引入互兜底链。
- 建议修复：
  1) 定义 diff contract（例如 `account_change_log_diff.version=1`，并明确 `privilege_diff/other_diff` 的 canonical 形状）；
  2) 在写入前由 adapter 统一构造（避免业务层散落拼装 list/dict）；
  3) 如历史数据已存在：制定迁移与退出条件（同 `compatibility-and-deprecation`）。
- 备注：若团队希望该列保持“半结构/自由扩展”，应在标准侧显式增加例外条款（否则按现行 MUST 口径属于违规）。

### CODE-04（P1｜违规）DB JSON 字段 `AccountPermission.type_specific` 未版本化

- 判定：违规（MUST）
- 标准依据：
  - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`
- 代码位置：
  - 列定义：`app/models/account_permission.py:58`
  - 写入：`app/services/accounts_sync/permission_manager.py:486`
- 问题：`type_specific` 属于长期存储的内部结构化 payload；字段扩展/语义变更会导致跨模块消费不稳定。
- 建议修复（两种路径择一）：
  1) version 化并建立 adapter（推荐：与 permission_snapshot 的 v4 结构保持一致的命名与迁移策略）；
  2) 将 `type_specific` 完全收敛到已版本化的 `permission_snapshot` 内（再逐步弃用独立列；需评估迁移成本与查询场景）。

### CODE-05（P2｜建议改进）高风险 `or` 兜底：可能覆盖合法空值/引入隐式优先级

- 判定：建议改进（SHOULD；需要业务语义确认）
- 标准依据：
  - `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:78`
  - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:114`
- 代码位置（代表性样本；全量见 artifacts）：
  - `app/tasks/accounts_sync_tasks.py:88`（`summary_dict.get(\"inventory\", {}) or {}`）
  - `app/tasks/accounts_sync_tasks.py:89`（`summary_dict.get(\"collection\", {}) or {}`）
  - `app/services/accounts_sync/accounts_sync_service.py:299`（`... if isinstance(details, dict) else {}`）
  - `app/routes/credentials.py:57`（`... or \"created_at\"`；`order` 同类）
- 建议修复：
  - 对“空值也可能合法”的字段改为 `is None` 或显式缺失判定；
  - 对 internal payload 的兜底应升级为“显式错误结构”（避免 `{}` 继续流转）。

---

## 3. 批量复核清单（不强判违规，但必须有人收口）

### REVIEW-01（P2｜待复核）`except ...: return default` 且 except 内无任何 call（疑似 silent fallback）

- 背景标准：
  - fallback 判据：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:53`
  - 禁止 silent fallback：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50`
- 处理建议（统一动作）：
  1) 逐条判断是否属于 fallback（尤其“外部依赖/缓存/系统信息”类）；
  2) 若属于 fallback：确保在**边界层**（route/task/worker 的一次操作范围内）记录 `fallback=true`/`fallback_reason`（可用 `log_fallback`）；
  3) 若不属于 fallback（输入校验/解析失败属正常分支）：用命名/注释/单测明确“返回 None/False 的语义”，避免未来被当作 silent fallback。
- 全量位置（32 处）：见 `docs/reports/artifacts/2026-01-15-app-silent-except-return.txt`
- 重点先复核（更像“运行期降级”的条目）：
  - `app/services/health/health_checks_service.py:132`（返回“未知”）
  - `app/services/connection_adapters/adapters/mysql_adapter.py:181`（返回 None）
  - `app/utils/cache_utils.py:210`（返回 0）
  - `app/settings.py:84`（解析失败返回 False）

### REVIEW-02（P2｜待复核）`or` 兜底链全量盘点（759 处）

- 背景标准：
  - 对合法 `0/\"\"/[]/{}` 的字段，避免 `or` 覆盖：`docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:78`
  - internal payload 的 `or` 兜底约束：`docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:114`
- 处理建议：
  1) 先按目录优先级复核：`app/services` → `app/api` → `app/repositories`；
  2) 把“覆盖合法空值”的点替换为 `is None`/显式缺失判定；
  3) internal payload 相关兜底尽量收敛到 adapter/normalizer 单入口。
- 全量位置（759 处）：见 `docs/reports/artifacts/2026-01-15-app-or-boolop.txt`

### REVIEW-03（P2｜待复核）DB JSON/JSONB 字段是否都满足 internal contract “version + 单入口”

- 背景标准：
  - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:54`
  - `docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md:105`
- 全量 JSON/JSONB 列位置：见 `docs/reports/artifacts/2026-01-15-app-json-columns.txt`
- 说明：本清单已明确标出 4 个“确定缺 version/需修复”的字段（见 CODE-01/03/04），其余字段应维持现状或补充“已 version/已 adapter”的证据（单测/契约文件）。

