# Module: `app/core/types`

## Simplification Analysis

### Core Purpose

提供项目级别的类型别名/TypedDict/Protocol，作为各层共享的“类型词汇表”，用于静态检查与减少类型漂移。

### Unnecessary Complexity Found

- `app/core/types/query_protocols.py:1`（已删除）：`QueryProtocol` 协议未在仓库代码/测试中使用，属于纯 YAGNI。
- `app/core/types/__init__.py:60`（已简化）：从聚合导出面（`__all__`）移除未使用的 `QueryProtocol`。
- `app/core/types/accounts.py:5`（已简化）：移除 `TYPE_CHECKING` + runtime alias（`Mapping = dict`）的“兜底式”写法。
- `app/core/types/sync.py:6`（已简化）：移除 `TYPE_CHECKING` + runtime fallback（Any/Mapping 回退），改为直接导入轻量依赖类型。
- `app/core/types/orm_kwargs.py:17`（已简化）：删除仅被单个子类继承的 `BaseSyncDataOrmFields`，内联字段到 `AccountPermissionOrmFields`。

### Code to Remove

- `app/core/types/query_protocols.py:1`（已删除）- 未使用的 `QueryProtocol`
- `app/core/types/__init__.py:60`（已改写）- 从聚合导出面移除未使用类型
- `app/core/types/accounts.py:5`（已改写）- `TYPE_CHECKING` 分支与 runtime alias
- `app/core/types/sync.py:6`（已改写）- runtime fallback 分支
- `app/core/types/orm_kwargs.py:17`（已改写）- 单次复用的 `BaseSyncDataOrmFields`
- Estimated LOC reduction: ~102 LOC（git diff: -110/+8）

### Simplification Recommendations

1. 删除未使用的类型与导出面（`QueryProtocol`）
   - Current: 存在“看似可用”的协议类型，但无调用方/测试覆盖
   - Proposed: 删除 `app/core/types/query_protocols.py`，并从 `app/core/types/__init__.py` 移除导出
   - Impact: 减少维护面与误导；净删 ~84 LOC

2. 去掉类型文件里的“防御性 fallback”
   - Current: `TYPE_CHECKING` + runtime fallback（Any/Mapping）降低可读性
   - Proposed: 直接导入轻量依赖类型，避免额外分支
   - Impact: 类型模块更直观；减少隐式行为

3. 内联一次性抽象
   - Current: `BaseSyncDataOrmFields` 仅服务单个 TypedDict
   - Proposed: 直接把字段放进 `AccountPermissionOrmFields`，删除基类
   - Impact: 少一层继承；更易定位字段来源

### YAGNI Violations

- 未被使用的 `QueryProtocol`：典型“可能未来用到”的抽象，当前只增加维护成本。
- 类型模块中的 runtime fallback：在无明确循环依赖/性能瓶颈证据时属于过度防御。

### Final Assessment

Total potential LOC reduction: ~100 LOC（以删未用协议为主）
Complexity score: Low → Lower
Recommended action: 优先删除 `QueryProtocol`，再收敛 TYPE_CHECKING fallback 与一次性抽象
