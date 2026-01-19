# Module: `app/models`

## Simplification Analysis

### Core Purpose

维护 ORM 数据模型（SQLAlchemy），为 Repository/Service 层提供稳定的数据结构与表/列定义；并在 `app/models/__init__.py` 提供统一导出入口，降低上层 import 心智负担。

### Unnecessary Complexity Found

- `app/models/__init__.py:22` 与 `app/models/__init__.py:94`：`__all__` 曾重复定义两次，属于纯样板重复（无行为收益）。
- `app/models/__init__.py:68`：`module_map` 在 `__getattr__()` 内部每次调用都重新构造；同时其 key 集合与 `__all__` 也构成重复源（易出现不一致）。

### Code to Remove

- `app/models/__init__.py:68`（已删除）- `__getattr__()` 内部每次重建的 `module_map`
- `app/models/__init__.py:94`（已删除）- 底部重复 `__all__` 列表
- Estimated LOC reduction: ~19 LOC（仅代码净删；`git diff` 统计：-43 +24）

### Simplification Recommendations

1. 使用单一映射源驱动 `__all__` 与 lazy import
   - Current: `__all__` + `__getattr__()` 内部 `module_map` + 底部再复制一份 `__all__`
   - Proposed: 模块级 `_MODEL_MODULE_MAP` 单入口；`__all__` 保持静态列表（避免 Pyright 对动态 `__all__` 的告警）
   - Impact: 删除重复；降低 drift 风险；`__getattr__()` 更短更直白

### YAGNI Violations

- 重复维护多份“模型名清单”（`__all__`/`module_map`/再次 `__all__`）属于典型的维护负担型 YAGNI：没有任何当前收益，只会增加 drift 风险。

### Final Assessment

Total potential LOC reduction: ~19 LOC（已落地）
Complexity score: Low（主要是样板重复）
Recommended action: 保持模型表结构不动，仅做导出入口去重
