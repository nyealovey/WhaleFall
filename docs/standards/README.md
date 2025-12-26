# 规范标准

本目录存放 WhaleFall 的规范标准（MUST/SHOULD/MAY），用于约束“如何写代码、如何改 UI、如何维护契约”。  
规范文档的结构与维护方式以 `documentation-standards.md` 为准。

## 索引

### 总则

- [文档结构与编写规范](./documentation-standards.md)
- [半角字符与全角字符禁用规范](./halfwidth-character-standards.md)
- [变更文档（docs/changes）规范](./changes-standards.md)
- [编码规范](./coding-standards.md)
- [Git 工作流与分支规范](./git-workflow-standards.md)
- [命名规范](./naming-standards.md)
- [术语与用词标准](./terminology.md)
- [新增功能交付标准](./new-feature-delivery-standard.md)
- [版本更新与版本漂移控制](./version-update-guide.md)

### 后端

- [后端标准索引](./backend/README.md)
- [API 响应封套（JSON Envelope）](./backend/api-response-envelope.md)
- [错误消息字段统一（error/message）](./backend/error-message-schema-unification.md)
- [配置与密钥（Settings/.env/env.example）](./backend/configuration-and-secrets.md)
- [数据库迁移（Alembic/Flask-Migrate）](./backend/database-migrations.md)
- [敏感数据处理（脱敏/加密/导出）](./backend/sensitive-data-handling.md)
- [任务与调度（APScheduler）](./backend/task-and-scheduler.md)

### UI

- [UI 标准索引](./ui/README.md)
- [按钮层级与状态](./ui/button-hierarchy-guidelines.md)
- [关闭按钮（btn-close）可访问名称](./ui/close-button-accessible-name-guidelines.md)
- [界面色彩与视觉疲劳控制](./ui/color-guidelines.md)
- [高风险操作二次确认](./ui/danger-operation-confirmation-guidelines.md)
- [设计 Token 治理（CSS Variables）](./ui/design-token-governance-guidelines.md)
- [前端模块化（modules）规范](./ui/javascript-module-standards.md)
- [GridWrapper 性能与日志](./ui/grid-wrapper-performance-logging-guidelines.md)
- [Grid.js 列表页迁移标准](./ui/gridjs-migration-standard.md)
- [分页与排序参数规范](./ui/pagination-sorting-parameter-guidelines.md)
