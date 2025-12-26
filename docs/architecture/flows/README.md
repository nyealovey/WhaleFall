# WhaleFall 运行流转图索引

> 状态：Active
> 负责人：WhaleFall Team
> 创建：2025-12-01
> 更新：2025-12-26
> 范围：关键运行链路索引（Mermaid）
> 关联：../spec.md；../project-structure.md

本索引用于汇总核心业务链路文档，便于按场景快速跳转。

1. **标准 CRUD 流程** → [whalefall-standard-crud-flows.md](./whalefall-standard-crud-flows.md)  
   包含：用户、实例、账户分类、分类规则、凭据等常规模块的增删改查链路。
2. **批量操作 CRUD** → [whalefall-crud-bulk-flows.md](./whalefall-crud-bulk-flows.md)  
   包含：标签批量分配/移除、实例批量导入/删除等高风险批量链路。
3. **数据采集 & 容量聚合** → [whalefall-data-sync-flows.md](./whalefall-data-sync-flows.md)  
   包含：账户/容量采集、容量聚合、数据同步计划等链路与故障排查提示。
4. **测试 & 自动分类流程** → [whalefall-testing-classification-flows.md](./whalefall-testing-classification-flows.md)  
   包含：连接测试、批量测试、参数校验、账户自动分类等流程。
5. **前端展示数据链路** → [whalefall-frontend-display-flows.md](./whalefall-frontend-display-flows.md)  
   包含：容量统计、分区指标等前端视图与后台 API 的映射关系。

> 新增/变更流程请直接在相应文档补充；若涉及 API 契约（响应封套/错误口径/分页参数），请同步更新相关标准：
> - [API 响应封套](../../standards/backend/api-response-envelope.md)
> - [错误消息字段统一](../../standards/backend/error-message-schema-unification.md)
> - [分页与排序参数规范](../../standards/ui/pagination-sorting-parameter-guidelines.md)
