# API action: business outcome failure vs exception (progress)

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-29
> 更新: 2025-12-29
> 范围: 同 `014-api-action-business-failure-vs-exception-plan.md`
> 关联: `014-api-action-business-failure-vs-exception-plan.md`

关联方案: `014-api-action-business-failure-vs-exception-plan.md`

---

## 1. 当前状态(摘要)

- 已落地:
  - 建立 `BaseResource.error_message(...)` 作为 action "业务结果失败"默认返回形态, 避免 `(Response, status)` 陷阱并简化封套输出.
  - capacity sync(`POST /api/v1/instances/<id>/actions/sync-capacity`) 将“连接失败/容量采集失败/采集为空”等预期失败改为"返回 error Response 不抛异常", 以允许提交已完成的 inventory 写入.
  - 单测补齐 failure contract: 验证 capacity 失败时不会 500, 且 inventory 仍被保留(不因 rollback 丢失).
  - 失败语义与事务边界标准已沉淀到 `docs/standards/backend/action-endpoint-failure-semantics.md`.

## 2. Checklist

### Phase 1: 规范落地(最小改动)

- [x] 新增 helper: `BaseResource.error_message(...)` 返回错误封套 `Response`(并设置 `response.status_code`)
- [x] capacity sync: 预期失败使用“返回 error Response”表达(不抛异常触发 rollback)
- [x] failure contract tests: 覆盖 connect 失败/采集为空/采集异常时的 message_code + 写入保留预期
- [x] 标准文档: action endpoint failure semantics(业务结果失败 vs 异常)与 `(Response, status)` 禁止项

### Phase 2: 扫描与门禁

- [x] v1 namespaces 扫描: 结果为空
  - `rg -n "return\\s+response\\s*,\\s*status" app/api/v1/namespaces`
  - `rg -n "\\(Response,\\s*status" app/api/v1/namespaces`
- [ ] 增加门禁(单测或 CI 脚本): 防止后续引入 `return response, status`/`(Response, status)` 形态
- [ ] 扩展 action 分类表: 覆盖全部 `/actions/*` 端点并补齐示例

## 3. 变更记录

- 2025-12-29: 初始化 progress 文档; 记录 action failure semantics 与 capacity sync failure contract 的落地进度.
