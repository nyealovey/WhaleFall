# 002 后端写操作分层重构 - 进度

> 状态：Draft
> 负责人：WhaleFall Team
> 创建：2025-12-26
> 更新：2025-12-26
> 范围：后端写操作（Create/Update/Delete）的分层边界与事务管理
> 关联：方案文档：[002-backend-write-operation-boundary-plan](002-backend-write-operation-boundary-plan.md)
>
> 开始日期：2025-12-26
> 最后更新：2025-12-26

## 当前状态

- 已完成：重写方案文档（对齐 `docs/standards/changes-standards.md`）
- 已完成（Phase W1 部分）：form_service 移除内部 `commit()`（改为 `flush()`），并清理 tags 同步子流程内的 `commit()`
- 已完成（Phase W2/W3 - Tags）：新增 `TagsRepository` 写操作方法与 `TagWriteService`，并将 tags 写接口收敛到 write service
- 已完成（Phase W4 - Instances）：新增 `InstanceWriteService` + 扩展 `InstancesRepository` 写方法；instances create/update/delete/restore 收敛到 write service；instances batch service 移除内部 `commit()`
- 已完成（Phase W4 - Credentials）：新增 `CredentialWriteService` + 扩展 `CredentialsRepository` 写方法；credentials create/update/delete 收敛到 write service；移除 routes 内直写 `db.session.*`
- 已完成（Phase W4 - Users）：新增 `UserWriteService` + 扩展 `UsersRepository` 写方法；users create/update/delete 收敛到 write service；移除 routes 内直写 `db.session.*`
- 已完成（Phase W4 - AccountClassifications）：新增 `AccountClassificationsWriteService` + 扩展 `AccountsClassificationsRepository` 写方法；移除 routes 内直写 `db.session.*`
- 已完成（Phase W5 部分）：`account_classification` 内部写仓库移除 `commit()`（改为 savepoint + flush），交由事务边界统一提交
- 已完成（Phase W5 部分）：`ConnectionTestService` 移除内部 `commit()`；新增 routes 写边界门禁脚本
- 已完成（Phase W5 部分）：`SyncSessionService` 移除内部 `commit()` / `rollback()`（改为 savepoint + flush），提交由事务边界统一处理
- 已完成（Phase W5 部分）：`accounts_sync` 移除内部 `commit()` / `rollback()`（改为 savepoint + flush），提交由事务边界统一处理
- 已完成（Phase W5）：清零 `app/services/**` 内 `db.session.commit()`（baseline=0），并移除关键 services 的内部事务提交
- 已完成（Phase W5）：form_service 内部 `rollback()` 改为 savepoint + flush（避免吞错后回滚整个请求事务）
- 已完成（Phase W5）：新增全局写操作边界门禁（commit allowlist + 组合门禁脚本）
- 已完成（Phase W5）：补充后端标准：写操作事务边界（Write Operation Boundary）
- 已完成（Phase W5）：新增 services `db.session.commit()` 漂移门禁（允许减少，禁止新增）

## Checklist

### Phase W0：前置决策与审计

- [x] 确认事务边界策略（routes 统一使用 `safe_route_call` commit/rollback；tasks/scripts/worker 入口自管事务）
- [x] 扫描 `db.session.commit()` 分布，按“允许/禁止”分组并固化到文档（见 `002-backend-write-operation-boundary-plan.md` 的 2.2）
- [x] 列出未被 `safe_route_call` 包裹的写接口清单（如存在）（已清零）

### Phase W1：form_service 事务迁移

- [x] `BaseResourceService.upsert()` 移除 `commit()`，改为 `flush()`
- [x] `after_save()` / 子流程内移除 `commit()`（如 tags 同步）
- [x] 回归验证：写接口行为不变（单测/手工关键路径）

### Phase W2：写操作 Repository 样板（Tags）

- [x] 新增 `TagsRepository.add()` / `delete()` / `sync_instance_tags()`
- [x] 迁移 `_delete_tag_record()` → Repository
- [x] 迁移 `_sync_tags()` → Repository
- [x] route 收敛：tags 写接口只调用 service

### Phase W3：写操作 Service 样板（Tags）

- [x] 新增 `TagWriteService.create()` / `update()` / `delete()` / `batch_delete()`
- [x] 补齐：校验 + 调用 Repository + 审计/缓存失效
- [x] route 改为调用 `TagWriteService`

### Phase W4：扩展到其他域

- [x] Instances：create/update/delete/restore
- [x] Credentials：create/update/delete
- [x] Users：create/update/delete
- [x] AccountClassifications：相关写接口（最后）

### Phase W5：清理与收尾

- [x] 清理：services/form_service 内的 `db.session.commit()` / `rollback()` 等事务控制（routes 已清零）
- [x] 文档：`docs/standards/backend/` 补充写操作分层规范
- [x] 门禁（routes）：新增 `scripts/ci/db-session-route-write-guard.sh`，禁止 routes 直写 `db.session.*`
- [x] 门禁（services baseline）：新增 `scripts/ci/db-session-commit-services-drift-guard.sh`，禁止新增 `db.session.commit()`
- [x] 门禁（全局）：引入写操作边界扫描（commit/add/delete）并作为 CI/本地检查项（最终目标：services 0 命中）

## 变更记录

- 2025-12-26：创建 `002-backend-write-operation-boundary-progress.md`，并重写方案文档对齐最新规范。
- 2025-12-26：Tags 落地 write 样板：`TagsRepository` 增加写方法；新增 `TagWriteService`；tags 写路由收敛到 write service。
- 2025-12-26：Instances 落地写操作分层：新增 `InstanceWriteService`；instances create/update/delete/restore 收敛到 write service；instances batch service 移除内部 `commit()`。
- 2025-12-26：Credentials 落地写操作分层：新增 `CredentialWriteService`；credentials create/update/delete 收敛到 write service；补齐写入口 `safe_route_call` 覆盖并清零未包裹清单。
- 2025-12-26：Users 落地写操作分层：新增 `UserWriteService`；users create/update/delete 收敛到 write service；移除 routes 内直写 `db.session.*`。
- 2025-12-26：AccountClassifications 落地写操作分层：新增 `AccountClassificationsWriteService`；移除 routes 内直写 `db.session.*`。
- 2025-12-26：AccountClassificationService 写仓库移除内部 `commit()` / `rollback()`，改为 savepoint + flush，并交由事务边界统一提交。
- 2025-12-26：ConnectionTestService 移除内部 `commit()`；新增 routes 写边界门禁脚本。
- 2025-12-26：SyncSessionService 移除内部 `commit()` / `rollback()`，改为 savepoint + flush，并交由事务边界统一提交。
- 2025-12-26：accounts_sync 写链路移除内部 `commit()` / `rollback()`，改为 savepoint + flush，并交由事务边界统一提交。
- 2025-12-26：新增 services `db.session.commit()` 漂移门禁脚本，允许逐步减少、禁止新增。
- 2025-12-26：清零 `app/services/**` 内 `db.session.commit()`；分区/聚合/容量同步等链路改为 flush/savepoint，并补齐 tasks 入口 commit。
- 2025-12-26：新增全局 commit allowlist 门禁与组合门禁脚本：`scripts/ci/db-session-commit-allowlist-guard.sh`、`scripts/ci/db-session-write-boundary-guard.sh`。
- 2025-12-26：补充后端标准文档：`docs/standards/backend/write-operation-boundary.md`。
