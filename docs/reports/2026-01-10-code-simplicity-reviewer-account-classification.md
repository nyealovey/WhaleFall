# Account Classification Simplicity Audit (code-simplicity-reviewer)

> 状态: Draft  
> 负责人: team  
> 创建: 2026-01-10  
> 更新: 2026-01-10  
> 范围: `docs/Obsidian/reference/service/account-classification-*.md`, `docs/Obsidian/reference/service/accounts-classifications-*.md` -> `app/services/account_classification/**`, `app/services/accounts/account_classifications_*`

## app/services/account_classification/dsl_v4.py

## Simplification Analysis

### Core Purpose
提供 DSL v4 的结构校验与执行(evaluate), 供分类规则引擎判断账户是否命中规则.

### Unnecessary Complexity Found
- optional prometheus metrics 的 no-op 模板与 builder 在多个模块重复(与 `permission_manager.py` 同构).
- `collect_dsl_v4_validation_errors()` 体积较大, 既做结构校验又做函数级校验, 嵌套函数较多, 阅读成本偏高.

### Code to Remove
- 抽出 metrics optional util, 删除重复模板.
- 将 validation 拆分为 2 层: shape validation + function args validation, 减少单函数体积.
- Estimated LOC reduction: 40-80

### Simplification Recommendations
1. 复用统一 metrics 工具
2. 将 validation 逻辑数据化
   - Current: 大量 if/elif 分支手写校验.
   - Proposed: 用 "fn -> required args schema" 的映射驱动校验, 减少重复分支.

### YAGNI Violations
- 将 metrics 逻辑内嵌到 DSL 文件会引入额外依赖面, 若当前没有指标采集要求, 建议延后.

### Final Assessment
Total potential LOC reduction: 10-20%  
Complexity score: Medium  
Recommended action: Minor tweaks only

## app/services/account_classification/orchestrator.py

## Simplification Analysis

### Core Purpose
编排分类流程: 加载规则(含缓存), 获取账户, 按 db_type 分组, 逐规则评估并写入 assignments, 输出汇总结果.

### Unnecessary Complexity Found
- `_classify_single_db_type()` 传入 accounts 已按 db_type 分组, 但 `_find_accounts_matching_rule()` 再次按 db_type 过滤(重复循环, 可删).
- `_group_rules_by_db_type()` 在 "分组" 过程中写缓存(`set_rules_by_db_type`), 将 side-effect 混入纯分组函数, 增加理解成本.
- 异常策略为 "捕获并返回 dict success=false"(49-80) + 内层循环再捕获, 导致错误路径分散.

### Code to Remove
- `_find_accounts_matching_rule()` 内对 `accounts` 的重复过滤.
- 将缓存写入从 `_group_rules_by_db_type()` 中剥离为单独步骤.
- Estimated LOC reduction: 30-80

### Simplification Recommendations
1. 消除重复过滤
   - Current: per db_type 已分组 -> 再 filter.
   - Proposed: `_find_accounts_matching_rule(rule, accounts)` 只做 evaluate, 不再关心 db_type.
2. 让分组函数无 side-effect
   - Current: group -> log -> set cache.
   - Proposed: group 只 return dict, cache 更新由上层明确调用.
3. 统一错误策略
   - Current: 多层 catch 并拼装 errors 列表.
   - Proposed: 让单层捕获负责 "转为可返回结构", 内层直接 raise, 代码更短且更可测.

### YAGNI Violations
- 大量防御性异常捕获会让 "bug" 被当成 "业务失败" 吞掉, 后续排查成本更高.

### Final Assessment
Total potential LOC reduction: 10-20%  
Complexity score: Medium-High  
Recommended action: Proceed with simplifications

## app/services/account_classification/auto_classify_service.py

## Simplification Analysis

### Core Purpose
作为 route 与 orchestrator 的薄封装: 负责参数规范化, 统一日志, 将 orchestrator 返回结构转换为更稳定的 payload.

### Unnecessary Complexity Found
- `instance_id` 参数类型联合过宽(`int | float | str | bool | None`), 本质上是为 route 输入兜底, 但扩大了 API 面.
- 同时存在 `AutoClassifyError` 与 `AppError` 的双体系, 错误策略略显复杂.

### Code to Remove
- 将 `instance_id` 入参简化为 `int | None` 并把解析责任留在 route 或 `parse_payload`.
- Estimated LOC reduction: 10-30

### Simplification Recommendations
1. 缩小输入类型
2. 若 orchestrator 已负责 "success=false" 结构, 这里可直接透传并由路由层封套, 让 service 只做日志与参数处理.

### YAGNI Violations
- 将 orchestrator 的 dict result 再包装成 dataclass, 若没有更多调用方, 可能是过早抽象.

### Final Assessment
Total potential LOC reduction: 5-15%  
Complexity score: Low-Medium  
Recommended action: Minor tweaks only

## app/services/accounts_permissions/facts_builder.py

## Simplification Analysis

### Core Purpose
从权限 snapshot(v4) 构建 query-friendly 的 `permission_facts`, 供统计查询与分类规则评估使用.

### Unnecessary Complexity Found
- DB 类型分支较多, 但总体为纯函数 + 小 helper 的组合, 属于合理复杂度.
- 存在对旧形态/宽松输入的兼容分支(例如 privilege dict fallback), 如果没有存量数据需求, 可评估删减以收敛输入面.

### Code to Remove
- 若已确认 snapshot 形态稳定为 v4, 可移除部分 fallback shape 解析分支, 让失败更早暴露.
- Estimated LOC reduction: 20-60(取决于兼容分支是否保留)

### Simplification Recommendations
1. 明确输入契约
   - Current: 允许多种形态(dict/list/mapping of booleans)并尽量容错.
   - Proposed: 仅接受 v4 snapshot 结构, 非法输入直接标记错误, 让上游修复数据来源.
2. 数据驱动 capabilities 规则(可选)
   - 将各 DB 的 capability 判定规则提取为配置表, 减少 if/elif 体积(但不要过度抽象).

### YAGNI Violations
- 若不存在 v4 之外的存量数据, 过多容错会长期增加维护成本.

### Final Assessment
Total potential LOC reduction: 5-15%  
Complexity score: Medium(主要来自多 DB 规则与兼容逻辑)  
Recommended action: Minor tweaks only(先确认输入契约, 再决定删减范围)

## app/services/accounts/account_classifications_read_service.py

## Simplification Analysis

### Core Purpose
聚合 repository 调用并输出稳定 DTO: classifications, rules, assignments, stats, permissions.

### Unnecessary Complexity Found
- 每个 read API 都有同构 try/except -> log_error -> raise SystemError 的模板, 代码重复明显.
- DTO 构建存在重复字段拼装(例如 classification list vs detail).

### Code to Remove
- 抽出 `_wrap_repo(op_name, fn)` 模板, 或由统一封套层处理异常并在 service 内只做转换.
- 抽出 `_to_classification_item()` 等 DTO builder.
- Estimated LOC reduction: 30-60

### Simplification Recommendations
1. 用最小 helper 消除重复
2. 保持 "service 仅负责 DTO", repository 负责 query, 错误封套放在上层, 减少重复层级.

### YAGNI Violations
- None(主要是重复代码, 非额外功能)

### Final Assessment
Total potential LOC reduction: 15-25%  
Complexity score: Medium  
Recommended action: Proceed with simplifications

## app/services/accounts/account_classifications_write_service.py

## Simplification Analysis

### Core Purpose
作为账户分类域的写入边界: payload 校验与归一化, 调用 repository 完成 add/delete/flush, 以及触发缓存失效.

### Unnecessary Complexity Found
- 大量 `cast()` 来回转换, 主要原因是 normalize 函数返回 `dict[str, object]`(类型噪声).
- DB error 映射重复(创建/更新/删除多处 try/except SQLAlchemyError -> DatabaseError).
- `_get_db_type_options()` 每次调用都构造列表, 可作为常量或缓存.

### Code to Remove
- 将 normalize 返回值改为 dataclass/TypedDict, 删除大部分 `cast()` 局部变量.
- 抽出 `_wrap_db_error(action, exc, extra)`.
- Estimated LOC reduction: 60-120

### Simplification Recommendations
1. 用强类型结构替代 `dict` normalize
2. 收敛 DB error 处理
3. 缓存或常量化 db_type options

### YAGNI Violations
- 过多的类型噪声会让后续改动成本上升, 建议尽早收敛.

### Final Assessment
Total potential LOC reduction: 10-25%  
Complexity score: Medium-High  
Recommended action: Proceed with simplifications
