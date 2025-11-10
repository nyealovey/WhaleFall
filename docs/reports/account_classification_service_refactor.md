# 账户分类服务按库拆分方案

## 背景与现状

- `app/services/account_classification_service.py` 长达 1,090 行，集成了规则加载、缓存、账户查询、按数据库类型分组、规则匹配、批量写入等所有职责。
- 虽然代码已经尝试按 `db_type` 做分组，但逻辑仍集中在单个类中，导致新增数据库类型、扩展匹配能力或排查问题时需要理解整份大文件。
- 账户同步（`app/services/account_sync/adapters/*.py`）与容量同步（`app/services/database_sync/adapters/*.py`）已经采用“按数据库适配器 + 协调器”模式，具备成熟的按库拆分经验，可复用到分类领域。

## 痛点总结

1. **职责耦合**：缓存、查询、规则评估和数据写入捆绑在单一类中，难以独立测试或替换。
2. **按库扩展成本高**：新增数据库要同时修改 `_evaluate_*`、过滤、批量写入等多个位置。
3. **可观测性不足**：日志虽多，但跨库处理顺序、失败、重试策略没有统一抽象。
4. **与同步流程割裂**：分类依赖账户权限快照，却没有直接复用账户/容量同步已有的适配器和连接工厂，重复维护数据库方言差异。

## 目标

- 将“按数据库类型”的分类逻辑下沉到可插拔的分类器模块，复用账户同步/容量同步的适配器模式，降低大文件复杂度。
- 保持现有 API（`auto_classify_accounts_optimized`）不变，对上层调用透明。
- 为后续并行化处理、按库限流、队列化执行预留钩子。

## 当前进展（2025-11-07）

- ✅ 移除 `_group_accounts_by_db_type` 写入“accounts_by_db_type”缓存的逻辑，缓存服务同步删除对应 API，`/cache/api/classification/stats` 仅统计规则缓存。
- ✅ 在 `app/services/statistics/account_statistics_service.py` 中新增 `fetch_rule_match_stats`，`/account_classification/api/rules/stats` 提供聚合后的命中数；前端通过 `fetchRuleStats` 拉取统计数据，列表接口不再实时评估规则。
- ✅ 新增 `app/services/account_classification/` 包，拆出 `cache.py`、`repositories.py`、`classifiers/` 以及 `orchestrator.py`，原 `AccountClassificationService` 仅作为兼容入口。
- 🚧 后续需要在 orchestrator 基础上补充更多监控指标、与账户同步协同的任务处理，以及 Feature Flag 化切换流程。

## 目标架构

```
app/services/account_classification/
├── orchestrator.py          # 暴露现有 service 接口，负责流程编排
├── repositories.py          # 规则、账户、分配的查询与写入
├── cache.py                 # 针对规则/账户的缓存封装
├── classifiers/
│   ├── base.py              # 定义抽象基类（接口同 AccountSync adapter）
│   ├── mysql_classifier.py
│   ├── sqlserver_classifier.py
│   ├── postgresql_classifier.py
│   └── oracle_classifier.py
└── factory.py               # 根据 db_type 返回具体 Classifier
```

- **Classifier 接口**：接收账户列表与规则集合，返回匹配结果及统计。接口风格与 `account_sync/adapters/base_adapter.py` 对齐，方便共享工具（如连接、权限解析）。
- **Repository**：封装 `AccountPermission`、`ClassificationRule`、`AccountClassificationAssignment` 的查询和写入，暴露清晰的输入/输出，便于单测。
- **Orchestrator**：保留日志、性能统计与缓存失效控制，仅负责“拿数据→按库调度→聚合结果”。
- **缓存层**：抽离 `cache_manager` 使用方式，提供统一的 key 命名与序列化，避免 Service 直接操作缓存。

## 缓存与统计策略

- **移除账户按库缓存（已完成）**：`_group_accounts_by_db_type` 不再写入 `accounts_by_db_type` 缓存，缓存服务也移除对应的 get/set 接口，彻底取消大规模账户快照序列化。
- **精简规则缓存（部分完成）**：当前仅保留按 `db_type` 的规则缓存；后续 orchestrator 成型后，将把缓存读写集中到新模块。
- **统计接口替代实时评估（已完成）**：`matched_accounts_count` 由 `AccountClassificationAssignment` 聚合得到，`account_statistics_service.fetch_rule_match_stats` + `/account_classification/api/rules/stats` 已上线，前端通过 `fetchRuleStats` 异步加载命中数。

## 与账户/容量同步的对齐方式

| 分类服务 | 参考模块 | 复用点 |
| --- | --- | --- |
| `classifiers/base.py` | `account_sync/adapters/base_adapter.py` | 定义统一接口、提供公共工具（权限标准化、错误包装）。 |
| `factory.py` | `account_sync/adapters/factory.py` | 根据 `db_type` 选择实现，默认 fallback 或抛错。 |
| `repositories.py` | `account_sync/account_query_service.py` | 使用相同的实例选择、批量加载方式，减少重复 SQL。 |

通过上述对齐，可以直接共享：
- 数据库连接与凭证解析方式；
- 统一的 `db_type` 枚举、驱动超时设置；
- 任务跟踪（`sync_session_service`）指标上报格式。

## 实施步骤

1. **基线梳理**  
   - 衍生单元测试覆盖 `_evaluate_*` 现有行为，确保拆分后可回归。  
   - 提取当前日志、性能指标需求，形成 checklist。

2. **引入目录与基类（已完成）**  
   - `app/services/account_classification/` 已包含 orchestrator、repository、cache、classifiers 等模块，原 Service 保留兼容入口。

3. **迁移数据访问与缓存**  
   - 将 `_get_rules_sorted_by_priority`、`_get_accounts_to_classify`、`_cleanup_all_old_assignments`、`_add_classification_to_accounts_batch` 挪至 `repositories.py`，Service 调用 repository。  
   - ✅ 已移除账户按库缓存；下一步需要把规则缓存读写集中到 `cache.py` 并收敛调用入口。

4. **按库拆分规则评估（已完成）**  
   - `classifiers/<db>_classifier.py` 承载 `_evaluate_<db>` 逻辑，`ClassifierFactory` 负责路由。

5. **编排层瘦身（已完成）**  
   - `orchestrator.py` 现负责“加载→分组→调用 classifier→聚合→写入”，并保留串行执行模式。

6. **拆分统计接口（已完成）**  
   - `account_statistics_service.fetch_rule_match_stats` + `/account_classification/api/rules/stats` 已提供聚合结果；`/api/rules` 保留元数据，前端通过 `fetchRuleStats` 补充命中数。  
   - 后续可复用该统计接口供仪表盘、任务详情等页面调用。

7. **对接任务与监控**  
   - 如分类任务通过 Celery/Scheduler 触发，可复用 `sync_session_service` 记录每个 DB 的阶段状态（参考 capacity 同步）。  
   - 将“按库结果”落在统一表或缓存，方便 UI 展示。

8. **渐进迁移与回归**  
   - 分阶段切换：先将一个数据库类型迁移到新 classifier，启用 Feature Flag；待验证后覆盖其余数据库。  
   - 最终删除旧的 `_evaluate_*` 与大文件，保留对 orchestrator 的调用接口不变。

## 风险与缓解

- **行为偏差风险**：通过为每种 DB 的 classifier 增补单元测试以及对照旧实现的样本数据，确保匹配结果一致。
- **性能回退**：拆分后初期仍保持串行；在 pipelines 层打点，观察单库耗时，再考虑并发。
- **依赖冲突**：与账户同步共享模块时需注意循环依赖，可把通用工具下沉到 `services/common/` 或 `utils/db/`。

## 成果指标

- `AccountClassificationService` 主文件控制在 < 300 行，只保留 orchestrator 逻辑。
- 新增数据库类型时只需实现一个 `classifier`，无需触碰 orchestrator 或 repository。
- 分类任务可输出“按库统计 + 错误”结构，便于 UI 展示和容量/账户同步一致化。
