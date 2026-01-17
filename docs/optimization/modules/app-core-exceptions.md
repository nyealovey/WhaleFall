# Module: `app/core/exceptions.py`

## Simplification Analysis

### Core Purpose

定义统一业务异常（Shared Kernel）：提供语义字段（category/severity/message_key/extra）并由边界层做 HTTP 映射与响应封套。

### Unnecessary Complexity Found

- 未发现可“删减而不引入行为风险”的过度抽象；结构已足够扁平，且被大量服务层引用。
- `app/core/exceptions.py:19`：`ExceptionMetadata` 为轻量数据结构；虽可进一步扁平化为类属性常量，但收益很小且可能影响现有日志/映射依赖（不建议为删而删）。

### Code to Remove

- N/A（本模块当前以稳定为先，不做删减）
- Estimated LOC reduction: 0

### Simplification Recommendations

1. 保持现状（Already minimal）
   - Current: 统一异常基类 + 少量语义子类
   - Proposed: 不改
   - Impact: 避免影响 `app/infra/error_mapping.py` 与各服务层的错误口径

### YAGNI Violations

- 未发现明显 YAGNI（各异常类型在服务层有明确使用场景，例如 `ValidationError/NotFoundError/DatabaseError` 等）。

### Final Assessment

Total potential LOC reduction: 0
Complexity score: Low
Recommended action: Already minimal（仅在出现真实新增/重复异常类型时再考虑合并/删减）

