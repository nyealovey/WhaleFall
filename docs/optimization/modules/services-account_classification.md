# account_classification（services/account_classification + utils/account_classification_dsl_v4.py）

## Core Purpose

- 提供账户分类能力：
  - 规则加载/缓存（ClassificationCache）
  - DSL v4 规则校验与执行（re-export 到 `app/utils/account_classification_dsl_v4.py`）
  - 自动分类编排（AccountClassificationService / AutoClassifyService）

## Unnecessary Complexity Found

- （已落地）`app/services/account_classification/auto_classify_service.py:1`：
  - `TYPE_CHECKING ... else ...` 仅为切换 `ClassificationEngineResult` 的导入路径，属于无收益的分支样板。
  - 该类型在运行时可直接从 `app.core.types.classification` 导入，避免条件分支与重复 import。

- （已落地）`app/services/account_classification/orchestrator.py:21`：
  - `CLASSIFICATION_RUNTIME_EXCEPTIONS/CACHE_INVALIDATION_EXCEPTIONS` 使用 `BaseException` 类型标注，但集合实际都是 `Exception` 子类，边界过宽且易误导。

## Code to Remove

- `app/services/account_classification/auto_classify_service.py:1`：移除条件导入分支（可删/可减复杂度 LOC 估算：~4-10）。
- `app/services/account_classification/orchestrator.py:21`：异常集合类型标注收敛为 `Exception`（可删/可减复杂度 LOC 估算：~0-4）。

## Simplification Recommendations

1. 类型导入路径只保留一个事实来源
   - Current: 为了“类型在哪里”引入分支。
   - Proposed: 运行时直接 import 实际定义处；类型检查不需要额外分支。

2. 异常边界与真实语义一致
   - Current: `BaseException` 过宽。
   - Proposed: `Exception` 更贴合业务/依赖错误边界。

## YAGNI Violations

- 为“可能的导入路径差异”保留条件分支（缺少明确收益）。

## Final Assessment

- 可删/可减复杂度估算：~4-14（已落地，主要是删条件分支与收敛类型边界）
- Complexity: Medium -> Lower
- Recommended action: Proceed（本轮不改 DSL 执行与分类行为，仅做等价简化）

