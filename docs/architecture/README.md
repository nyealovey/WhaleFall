# 架构设计

> 状态: Draft

本目录承载架构设计说明, 分层边界, 关键数据流与 ADR (Architecture Decision Records).

## 索引

- [project-structure.md](./project-structure.md): 项目目录结构与模块说明 (代码落点索引)
- [spec.md](./spec.md): 架构规范与设计背景 (为什么/怎么设计)
- [developer-entrypoint.md](./developer-entrypoint.md): global developer entry diagrams (C4 L1/L2/L3)
- [module-dependency-graph.md](./module-dependency-graph.md): 模块依赖与分层边界 (高层视角)
- [cross-cutting-capabilities.md](./cross-cutting-capabilities.md): cross-cutting capabilities (auth/RBAC, observability/error envelope, DB adapter canonical schema)
- [identity-access.md](./identity-access.md): identity & access for API v1 (auth/users/CSRF/RBAC)
- [observability-ops.md](./observability-ops.md): observability & ops for API v1 (health/history logs/cache/admin)
- [common-options.md](./common-options.md): common options for API v1 (instances/databases/database types)
- [domain-first-api-restructure.md](./domain-first-api-restructure.md): Domain-first API/Directory restructure proposal (draft)
- [accounts-permissions-domain.md](./accounts-permissions-domain.md): accounts/permissions domain diagrams for developers (sync + ledgers)
- [instances-domain.md](./instances-domain.md): instances domain diagrams for developers (CRUD + sync-capacity)
- [credentials-connections-domain.md](./credentials-connections-domain.md): credentials + connections domain diagrams for developers (crypto + adapters)
- [capacity-partitions-domain.md](./capacity-partitions-domain.md): capacity + partitions domain diagrams for developers (collection + DDL)
- [databases-ledger-domain.md](./databases-ledger-domain.md): databases ledger domain diagrams for developers (ledgers + trends + tags filter)
- [scheduler-domain.md](./scheduler-domain.md): scheduler domain diagrams for developers (APScheduler + job lifecycle)
- [classification-domain.md](./classification-domain.md): classification domain diagrams for developers (rules + auto-classify)
- [tags-domain.md](./tags-domain.md): tags domain diagrams for developers (CRUD + bulk assign/remove)
- [files-exports.md](./files-exports.md): files exports/downloads (csv safety + templates)
- [dashboard-domain.md](./dashboard-domain.md): dashboard read APIs (overview/status/charts)
- [flows/README.md](./flows/README.md): 关键流程图 (Mermaid)
- [architecture-review.md](./architecture-review.md): 架构评审入口 (索引/约定, 具体报告见 `docs/reports/`)
- [adr/README.md](./adr/README.md): ADR 索引
