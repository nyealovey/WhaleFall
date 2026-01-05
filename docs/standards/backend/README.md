# 后端标准

本目录定义后端对外/对内契约的强约束标准（例如返回结构、错误消息口径、兼容与迁移边界）。

## 索引

- [API 响应封套（JSON Envelope）](./api-response-envelope.md)
- [API 命名与路径规范 (REST Resource Naming)](./api-naming-standards.md)
- [错误消息字段统一（error/message）](./error-message-schema-unification.md)
- [请求 payload 解析与 schema 校验](./request-payload-and-schema-validation.md)
- [Action endpoint failure semantics (business failure vs exception)](./action-endpoint-failure-semantics.md)
- [写操作事务边界（Write Operation Boundary）](./write-operation-boundary.md)
- [配置与密钥（Settings/.env/env.example）](./configuration-and-secrets.md)
- [数据库迁移（Alembic/Flask-Migrate）](./database-migrations.md)
- [敏感数据处理（脱敏/加密/导出）](./sensitive-data-handling.md)
- [任务与调度（APScheduler）](./task-and-scheduler.md)
