# Platform Services Simplicity Audit (code-simplicity-reviewer)

> 状态: Draft  
> 负责人: team  
> 创建: 2026-01-10  
> 更新: 2026-01-10  
> 范围: `docs/Obsidian/reference/service/{cache,sync-session,scheduler,partition,health,filter-options}.md` -> `app/services/{cache_service.py,sync_session_service.py,scheduler/**,partition/**,partition_management_service.py,health/**,common/**}`

## app/services/cache_service.py

## Simplification Analysis

### Core Purpose
提供统一缓存接口, 支持规则缓存与评估结果缓存, 并提供健康检查与 invalidate API.

### Unnecessary Complexity Found
- 多个 invalidate API 为占位实现并始终返回 True(例如 91-120), 容易让调用方误以为缓存已失效.
- 大量重复的 "if not self.cache: return ..." + try/except + json loads 模板.
- `globals()[\"cache_service\"] = service` 写法不必要(初始化逻辑过度动态).

### Code to Remove
- 占位 invalidate 方法(或改为显式 NotImplementedError/ValidationError).
- 抽取 `get_json/set_json/delete_key` 等 helper, 删除重复 try/except 模板.
- 将 `globals()` 赋值改为正常的 `global cache_service`.
- Estimated LOC reduction: 80-160

### Simplification Recommendations
1. 让 cache invalidation 语义真实
2. 收敛重复模板为 2-3 个 helper
3. 明确缓存内容格式(统一存 dict 或统一存 JSON string), 删除双格式兼容分支

### YAGNI Violations
- "旧格式兼容" 与 "模式匹配 invalidate" 若无明确调用或存量数据, 建议不要长期保留占位.

### Final Assessment
Total potential LOC reduction: 15-30%  
Complexity score: High(重复模板 + 占位语义)  
Recommended action: Proceed with simplifications

## app/services/sync_session_service.py

## Simplification Analysis

### Core Purpose
管理 SyncSession 与 SyncInstanceRecord 的创建与状态更新, 提供会话统计更新, 供 accounts/capacity/aggregation 等任务复用.

### Unnecessary Complexity Found
- try/except/log/flush 模板在多个方法内重复(创建会话, 添加记录, start/complete/fail/cancel).
- error handling 策略不一致: `get_session_records` 选择 raise, 但 `get_sessions_by_type/category/recent` 选择返回空列表(静默降级).
- `db.session.flush()` 在同一事务里多次调用, 多数场景只需要一次 flush.

### Code to Remove
- 统一错误策略, 删除 "查询失败返回空列表" 的静默行为, 或返回结构化错误而不是空值.
- 抽取最小事务模板 helper, 删除重复 try/except.
- Estimated LOC reduction: 80-140

### Simplification Recommendations
1. 统一错误策略: read API 失败要么都 raise, 要么都返回明确 error payload
2. 让 service 只负责业务状态变更, 日志由上层统一封套

### YAGNI Violations
- 静默 return [] 会掩盖数据库故障, 增加运维排障成本.

### Final Assessment
Total potential LOC reduction: 15-25%  
Complexity score: High(重复模板 + 策略不一致)  
Recommended action: Proceed with simplifications

## app/services/scheduler/scheduler_jobs_read_service.py

## Simplification Analysis

### Core Purpose
列出 scheduler jobs 并输出稳定 DTO, 附带 trigger 参数与 last_run_time 推断.

### Unnecessary Complexity Found
- `_collect_trigger_args` 同时兼容 dict/list 两种 fields 形态, 分支较多, 且依赖字符串判断 CronTrigger 类型.

### Code to Remove
- 若 APScheduler 版本固定, 可只支持一种字段形态, 删除不必要分支.
- Estimated LOC reduction: 10-40

### Simplification Recommendations
1. 以 APScheduler 的稳定 API 获取 cron 表达式, 避免内部结构分支.

### Final Assessment
Total potential LOC reduction: 5-20%  
Complexity score: Medium  
Recommended action: Minor tweaks only

## app/services/scheduler/scheduler_job_write_service.py

## Simplification Analysis

### Core Purpose
更新内置任务的 cron trigger 配置.

### Unnecessary Complexity Found
- 只支持 cron trigger, 但仍保留 `_build_trigger` 的间接层.
- `SchedulerJobResource` 仅用于提供 `id` 属性, 对当前写场景略重.

### Code to Remove
- 内联 `_build_trigger` -> `_build_cron_trigger`.
- 若不需要通用 resource 模式, 可直接返回 job 或简单 dict.
- Estimated LOC reduction: 10-30

### Final Assessment
Total potential LOC reduction: 5-15%  
Complexity score: Medium  
Recommended action: Minor tweaks only

## app/services/partition/partition_read_service.py

## Simplification Analysis

### Core Purpose
读取分区信息并输出 snapshot, 提供 list/search/sort 与 core metrics chart 数据.

### Unnecessary Complexity Found
- `get_partition_info_snapshot` 与 `get_partition_status_snapshot` 同构调用链, 仅返回 DTO 不同, 可复用内部 helper.
- 多处 `except Exception -> raise SystemError` 模板重复.

### Code to Remove
- 抽取 `_fetch_partition_info()` 返回 `(partitions, missing, status, totals...)` 并复用.
- Estimated LOC reduction: 30-60

### Final Assessment
Total potential LOC reduction: 10-20%  
Complexity score: Medium  
Recommended action: Proceed with simplifications

## app/services/partition_management_service.py

## Simplification Analysis

### Core Purpose
创建与清理分区, 查询分区列表并附带 size/record_count/status.

### Unnecessary Complexity Found
- `create_partition`/`cleanup_old_partitions` 的循环内嵌套 `begin_nested()` + 多重 except, 代码冗长.
- `PARTITION_SERVICE_EXCEPTIONS` 内包含 SQLAlchemyError, 但同时又单独捕获 SQLAlchemyError, 分支重复.
- `_format_size` 与 `BYTES_IN_*` 未被引用(`_format_size` 629-645), 属于 dead code.

### Code to Remove
- 删除 `_format_size` + `BYTES_IN_*`.
- 外层 begin_nested 足以保证 all-or-nothing, 内层 begin_nested 可删除并用单层 try/except 记录 failures.
- 将异常集合收敛为 `Exception` 并统一 safe_exc 转换, 删除重复分支.
- Estimated LOC reduction: 80-160

### Simplification Recommendations
1. 让事务结构更直观(单层 begin_nested + failures 收集 + 最后 raise)
2. 删除 dead code

### Final Assessment
Total potential LOC reduction: 15-25%  
Complexity score: High  
Recommended action: Proceed with simplifications

## app/services/health/health_checks_service.py

## Simplification Analysis

### Core Purpose
提供 ping/basic health/database/cache/system/uptime 等基础探活输出.

### Unnecessary Complexity Found
- 无明显不必要复杂度(各 check 独立且短).

### Final Assessment
Total potential LOC reduction: 0-5%  
Complexity score: Low  
Recommended action: Already minimal

## app/services/common/filter_options_service.py

## Simplification Analysis

### Core Purpose
提供通用下拉选项与 filters options 的读服务封装.

### Unnecessary Complexity Found
- DTO 构建里较多 `getattr/cast` 噪声, 本质是 model typing 问题.

### Final Assessment
Total potential LOC reduction: 0-10%  
Complexity score: Low  
Recommended action: Minor tweaks only

