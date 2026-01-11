# Backend Layer Boundary Audit Progress (2026-01-11)
> 状态: Draft
> 负责人: team
> 创建: 2026-01-11
> 更新: 2026-01-11
> 关联: `docs/reports/2026-01-11-backend-layer-boundary-audit.md`
> 目标: 以分层标准为口径, 分阶段消除边界跨越并固化门禁

## 0. 当前状态(摘要)

- 现状报告已完成: `docs/reports/2026-01-11-backend-layer-boundary-audit.md`
- 写边界 guard 当前通过(仅证明 commit 位置受控, 不代表分层边界已满足)
- P0 主要问题: services/tasks/forms 边界漂移

## 1. 进度表(建议排期与验收口径)

说明:

- Owner/日期默认 TBD, 由团队填充.
- Verification 以可自动化的 `rg`/guard 为主, 便于 CI 固化.

| Phase | Priority | Deliverable | Scope | Owner | Status | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | P0 | 明确标准冲突与例外口径(Tasks/Utils/Types) | `docs/Obsidian/standards/backend/layer/**`, `docs/Obsidian/standards/backend/write-operation-boundary.md` | TBD | Done | reviewers sign-off + 更新 standards |
| 1 | P0 | Forms 去 DB/去跨层依赖 | `app/forms/**`, `app/views/**`, `app/services/**`, `app/repositories/**` | TBD | Done | `rg -n "from app\\.(models|services|repositories)|db\\.session|\\.query\\b" app/forms` == 0 |
| 2 | P0 | Tasks 变薄(禁止 query/execute) | `app/tasks/**` | TBD | Done | `rg -n "\\.query\\b|db\\.session\\.(query|execute)\\b" app/tasks` == 0 |
| 3 | P0 | Services 数据访问经 Repository(Instances/SyncSession) | `app/services/instances/instance_write_service.py`, `app/services/sync_session_service.py`, `app/repositories/**` | TBD | Done | `rg -n "\\.query\\b|db\\.session\\.(query|execute)\\b" <target services>` == 0 |
| 4 | P1 | API v1 去 models 依赖 | `app/api/v1/**` | TBD | TODO | `rg -n "from app\\.models|import app\\.models" app/api/v1` == 0 |
| 5 | P1 | 新增/强化 CI guards(分层门禁) | `scripts/ci/**` | TBD | TODO | 新 guard 全绿, 且在 CI 中启用 |
| 6 | P2 | Models 查询工具方法迁移到 Repositories | `app/models/**`, `app/repositories/**` | TBD | TODO | `rg -n "\\.query\\b|db\\.session\\b" app/models` 命中逐步下降 |

## 2. Checklist(按 Phase)

### Phase 0

- [x] 确认: Tasks 允许 `commit/rollback`, 禁止 query/execute/Model.query 与业务逻辑堆叠
- [x] 确认: Utils 中 `route_safety/queue_worker` 移出 utils, 放入 `app/infra/**`
- [x] 确认: Types 不允许 `TYPE_CHECKING` 引用 models, 统一改为 `Protocol`/弱类型并补充示例

### Phase 1

- [x] `app/forms/**` 不再 import `app.models/app.services/app.repositories`
- [x] `app/forms/**` 不再出现 `Model.query/db.session`
- [ ] 相关 UI 行为回归(表单加载/编辑/提交) (建议手动回归)

### Phase 2

- [x] `app/tasks/**` 不再出现 `.query`
- [ ] `capacity_*_tasks.py` 拆分为薄入口 + runner service
- [ ] 任务执行路径验证(手动触发 + scheduler)

### Phase 3

- [x] Instances 写服务: 删除 `Instance.query/Credential.query` 直用, 全部走 repository
- [x] SyncSession: 新建 repository 并迁移 `Instance.query/SyncInstanceRecord.query` 直用

### Phase 4

- [ ] API v1 namespaces 不再 import models
- [ ] 端点契约不变(或同步更新 API contract)

### Phase 5

- [ ] 新增 `forms-layer-guard.sh`
- [ ] 新增 `tasks-layer-guard.sh`
- [ ] 新增 `api-layer-guard.sh`
- [ ] (可选) 新增 `services-repository-enforcement-guard.sh`(先 warn 后 fail)

## 3. 变更记录(按日期追加)

- 2026-01-11: 创建 progress 文档, 填充建议 phases 与验收口径.
- 2026-01-11: 确认 Phase 0(部分): 事务边界与 worker 入口迁移到 `app/infra/**`(见 `app/infra/route_safety.py`, `app/infra/logging/queue_worker.py`).
- 2026-01-11: 确认 Phase 0(部分): tasks 允许 `commit/rollback`, 禁止 query/execute 与业务逻辑堆叠(见 `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md`).
- 2026-01-11: 确认 Phase 0(完成): types 禁止 `TYPE_CHECKING` 引用 models, 统一改用 `Protocol`/弱类型(见 `docs/Obsidian/standards/backend/layer/types-layer-standards.md`, `app/types/credentials.py`, `app/types/tags.py`).
- 2026-01-11: 完成 Phase 1: Forms 层移除 DB/跨层依赖, 表单 handler 迁移至 `app/views/form_handlers/**`, 并由 View 显式绑定 `service_class`.
- 2026-01-11: 完成 Phase 2: Tasks 层移除 `.query/db.session.query/execute`, 查询下沉到 `app/services/**`/`app/repositories/**`.
- 2026-01-11: 完成 Phase 3: `InstanceWriteService` 与 `SyncSessionService` 删除直用 `.query/db.session.query`, 下沉到 `app/repositories/**`.
