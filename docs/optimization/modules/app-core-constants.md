# Module: `app/core/constants`

## Simplification Analysis

### Core Purpose

提供全局常量（字符串/Enum/状态集合等），避免业务代码散落魔法值；并作为 Shared Kernel 被各层复用。

### Unnecessary Complexity Found

- `app/core/constants/http_headers.py:10`：`CSRF_HEADER_NAMES` 仅被本文件索引使用，多一层间接并未带来复用价值（可直接内联为常量字符串）。
- `app/core/constants/http_headers.py:16`：`HttpHeaders` 维护了大量 header 常量，但仓库内仅使用了少数（`CONTENT_TYPE/AUTHORIZATION/USER_AGENT/X_CSRF_TOKEN/X_FORWARDED_PROTO/X_FORWARDED_SSL`），其余为纯 YAGNI 负担。
- `app/core/constants/http_headers.py:87`：嵌套 `ContentType` 常量集合在仓库内无引用，属于“顺手补全”的过度抽象。

### Code to Remove

- `app/core/constants/http_headers.py:10`（已删除）- `CSRF_HEADER_NAMES` 的间接层
- `app/core/constants/http_headers.py:22`（已删除）- `HttpHeaders` 内未使用的 header 常量块
- `app/core/constants/http_headers.py:87`（已删除）- `HttpHeaders.ContentType` 全部内容
- Estimated LOC reduction: ~96 LOC（`http_headers.py` 由 115 行降至 19 行；git diff: -101/+5）

### Simplification Recommendations

1. 收敛 `HttpHeaders` 到“仅保留当前代码路径使用的 header 名称”
   - Current: 一个“百科全书式”的 header 列表（多数无引用）
   - Proposed: 只保留实际引用的 6 个常量；其余按需再加
   - Impact: 明显降低认知负担；减少维护面；净删 ~96 LOC

### YAGNI Violations

- `HttpHeaders.ContentType`：未被引用，且与当前需求无关；保留只会制造“可能有用”的错觉。
- 未使用的 header 常量：在未有调用方/测试覆盖/真实需求之前，属于典型 YAGNI。

### Final Assessment

Total potential LOC reduction: ~96 LOC（已落地）
Complexity score: Low
Recommended action: 已极简；后续如新增真实用例再增量补常量即可

