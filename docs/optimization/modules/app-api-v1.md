# Module: `app/api/v1`

## Simplification Analysis

### Core Purpose

对外 API v1（Flask-RESTX）路由层：
- 只承载路由、OpenAPI 文档（restx_models/models）、参数解析与封套输出
- 业务编排与数据访问复用 `services/` + `repositories/`
- 错误封套统一通过 `WhaleFallApi.handle_error()` + AppError 体系输出

### Unnecessary Complexity Found

- 多个 namespace 曾重复定义完全相同的“请求体读取”逻辑（JSON dict 或 form）
  - 已收敛为 `app/api/v1/resources/base.py:22` 的 `get_raw_payload()`
  - 影响：减少样板重复；后续调整 payload 读取策略无需多点同步

### Code to Remove

- 已落地：
  - `app/api/v1/resources/base.py:22`：新增 `get_raw_payload()` 单入口
  - 删除各 namespace 的 `_get_raw_payload()` 并统一复用
- Estimated LOC reduction: ~23 LOC（仅代码净删；本模块当前变更 `git diff` 统计：-51 +28）

### Simplification Recommendations

1. 统一“请求体读取”入口
   - Current: 每个 namespace 各写一份 `_get_raw_payload`
   - Proposed: `app/api/v1/resources/base.py:get_raw_payload`
   - Impact: 删除样板重复；降低 drift 风险；不改变接口行为

### YAGNI Violations

- “每个 namespace 复制一份 payload 读取逻辑”没有当前收益，只会增加维护点。

### Final Assessment

Total potential LOC reduction: ~23 LOC（已落地）
Complexity score: Low（主要是样板重复）
Recommended action: 先做重复删除；避免大规模重构 query parser/模型定义导致行为风险
