# Flask-RESTX OpenAPI API 全量迁移进度

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-26
> 更新: 2025-12-26
> 范围: 同 `004-flask-restx-openapi-migration-plan.md`
> 关联: `004-flask-restx-openapi-migration-plan.md`

关联方案: `004-flask-restx-openapi-migration-plan.md`

---

## 1. 当前状态(摘要)

- 未开始. 先完成 Phase 0 的最小闭环, 再按域推进迁移.

## 2. Checklist

### Phase 0: 基础设施与最小闭环

- [ ] 新增 `app/api/**` 目录与 `/api/v1` blueprint
- [ ] RestX `Api` 基础配置与 docs/spec 路由
- [ ] envelope/error 的 RestX Model
- [ ] OpenAPI 导出脚本与最小校验

### Phase 1: 低风险域验证

- [ ] 迁移 health 或只读域到 RestX Resource
- [ ] 增加最小 HTTP 契约测试(200/4xx)

### Phase 2: 核心业务域迁移

- [ ] instances
- [ ] tags
- [ ] credentials
- [ ] accounts

### Phase 3: 全量覆盖与文档完善

- [ ] 覆盖所有 `/api` 端点到 RestX
- [ ] 补齐关键 model 的 description/example
- [ ] 增加"认证/CSRF 使用说明"文档入口

### Phase 4: 下线旧 API 与清理

- [ ] 移除旧 `*/api/*` 路由实现或按策略返回 410/301
- [ ] 移除迁移期兼容分支与 feature flag

## 3. 变更记录(按日期追加)

- 2025-12-26: 创建 plan/progress 文档, 待开始实施.

