# Module: `app/schemas`

## Simplification Analysis

### Core Purpose

集中维护 Pydantic schema，作为“写路径 payload / query 参数 / internal&external contract”的单入口：
- 写路径：字段类型转换、默认值、业务校验（中文错误文案）
- API query：参数 canonicalization（避免 `or` truthy 兜底链覆盖合法 falsy）
- 内外部 contract：将“脏 dict / JSON 列”规整为稳定结构，避免业务层散落兼容链
- 统一错误映射：`validate_or_raise()` 将 Pydantic 错误收敛为项目 `ValidationError`

### Unnecessary Complexity Found

- 多个 query schema 文件重复定义同一套 `_parse_int/_parse_text` helper（实现完全一致但分散复制粘贴）
  - `app/schemas/accounts_query.py:23` + `app/schemas/accounts_query.py:44`
  - `app/schemas/tags_query.py:22` + `app/schemas/tags_query.py:43`
  - `app/schemas/instances_query.py:24` + `app/schemas/instances_query.py:46`
  - `app/schemas/credentials_query.py:23` + `app/schemas/credentials_query.py:45`
  - `app/schemas/history_sessions_query.py:23` + `app/schemas/history_sessions_query.py:45`
  - `app/schemas/history_logs_query.py:26` + `app/schemas/history_logs_query.py:47`
  - `app/schemas/partition_query.py:21` + `app/schemas/partition_query.py:43`
  - 影响：维护面膨胀；任何微调都需要多点同步；读代码时反复“跳过样板代码”

- 多个 query schema 文件重复定义 `_parse_tags`（实现一致）
  - `app/schemas/accounts_query.py:52`
  - `app/schemas/instances_query.py:71`
  - `app/schemas/credentials_query.py:79`

- `app/schemas/yaml_configs.py` 内存在结构重复（同形但分散）
  - `AccountFilterRuleConfig`/`DatabaseFilterRuleConfig` 的字符串列表 coercion 逻辑重复
  - `AccountFiltersConfigFile`/`DatabaseFiltersConfigFile` 的 db_type key normalize 逻辑重复

### Code to Remove

- 已落地：
  - `app/schemas/query_parsers.py`：新增 query 参数解析 helper 单入口（不引入新抽象层，仅搬运重复函数）
  - 删除各 query schema 文件内重复的 `_parse_int/_parse_text/_parse_tags` 定义
  - `app/schemas/yaml_configs.py`：内部抽出小函数复用，删除重复实现
- Estimated LOC reduction: ~273 LOC（仅代码净删；`git diff` 统计：-482 + (122+87)）

### Simplification Recommendations

1. 抽出 query 参数解析 helper（删重复优先）
   - Current: 每个 query 文件自带一套 `_parse_int/_parse_text/_parse_tags`
   - Proposed: `app/schemas/query_parsers.py` 提供 `parse_int/parse_text/parse_tags/(optional)` 并复用
   - Impact: 减少重复样板代码；降低维护成本；查询 schema 更聚焦业务字段语义

2. `yaml_configs.py` 内部去重（不跨文件引入新抽象）
   - Current: 两套几乎相同的 list coercion + key normalize
   - Proposed: 提取成 2 个纯函数复用（保持错误文案与行为一致）
   - Impact: 代码更短更直白；减少未来“改一处忘另一处”的风险

### YAGNI Violations

- query schema 文件中反复 copy 同样的解析函数，本质是“提前在每个文件里复制一套工具箱”；在已有稳定实现的前提下，多份副本没有任何现实收益，只会增加维护负担。

### Final Assessment

Total potential LOC reduction: ~273 LOC（已落地）
Complexity score: Medium（主要问题是“重复样板代码”，而非业务逻辑复杂）
Recommended action: 优先去重 + 保持行为不变；用现有 unit tests 兜住回归
