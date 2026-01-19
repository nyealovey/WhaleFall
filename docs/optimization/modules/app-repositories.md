# Module: `app/repositories`

## Simplification Analysis

### Core Purpose

Repository 层只做“Query 组装 + 数据库读写(add/flush/select/count)”：
- 不做业务编排、不做序列化、不返回 Response、不 commit
- 作为 Service 层与 ORM/SQLAlchemy 的边界，收敛数据访问细节

### Unnecessary Complexity Found

- 重复的“实例标签映射”查询逻辑在同一仓库文件内出现两次
  - `app/repositories/instances_repository.py:119`（`fetch_tags_map`）
  - `app/repositories/instances_repository.py:323`（`_collect_instance_metrics` 直接复用 `fetch_tags_map`）
  - 已落地：删除重复 SQL 与样板代码

- 重复的 `list_instances_by_ids` 实现（完全复制粘贴）
  - `app/repositories/instances_repository.py:83`
  - `app/repositories/instances_batch_repository.py:31`
  - 已落地：`InstancesBatchRepository.list_instances_by_ids` 委托到 `InstancesRepository.list_instances_by_ids`

- 同一文件内重复的投影组装循环（同形逻辑出现两次）
  - `app/repositories/ledgers/database_ledger_repository.py:60`（`list_ledger` 中构建 `DatabaseLedgerRowProjection`）
  - `app/repositories/ledgers/database_ledger_repository.py:91`（`iterate_all` 中重复构建同样的 projection）
  - 已落地：抽成极小的 `_to_row_projection(...)` helper（仅服务当前文件两处调用）

### Code to Remove

- 已落地：
  - `app/repositories/instances_repository.py:323` - 删除重复 tags 查询块（改为调用 `fetch_tags_map`）
  - `app/repositories/instances_batch_repository.py:31` - 删除复制粘贴的 `list_instances_by_ids` 实现（改为委托调用）
  - `app/repositories/ledgers/database_ledger_repository.py:60` - 删除重复的 projection 构建循环（改为复用 helper）
- Estimated LOC reduction: ~30 LOC（仅代码净删；本模块当前变更 `git diff` 统计：-64 +34）

### Simplification Recommendations

1. 复用已有 helper，而不是在同文件里重复写一套
   - Current: 同一 repo 文件里重复写 tags mapping 查询
   - Proposed: 直接调用 `fetch_tags_map`
   - Impact: 更少 SQL 与样板代码；逻辑更聚焦；风险低（复用的是已在别处使用的现有行为）

2. 去掉“同实现复制粘贴”
   - Current: `InstancesBatchRepository` 复制了一份 `list_instances_by_ids`
   - Proposed: 委托给 `InstancesRepository` 的实现
   - Impact: 未来改动只需维护一处；降低 drift 风险

3. 抽出仅服务当前文件的最小 helper（不引入跨模块抽象）
   - Current: 同一个 projection 组装循环写两遍
   - Proposed: `_to_row_projection(...)` 单入口，供两处调用
   - Impact: 读代码更直接；删除重复；不改变数据访问语义

### YAGNI Violations

- “复制一份 helper/循环逻辑以备将来修改”属于典型 YAGNI：没有当前收益，只会制造多处维护点与不一致风险。

### Final Assessment

Total potential LOC reduction: ~30 LOC（已落地）
Complexity score: Medium（主要是“重复样板代码”，不是业务逻辑复杂）
Recommended action: 以“复用/删除重复”为主，避免跨文件/跨层新抽象
