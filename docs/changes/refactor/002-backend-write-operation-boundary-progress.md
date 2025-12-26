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
- 进行中：写入口统一纳入事务边界（`safe_route_call`）与其他域分层迁移（W4/W5）
- 下一步：确认事务边界策略 + commit 分布审计（Phase W0），并回归验证写接口行为不变（W1），再按域推进 W4

## Checklist

### Phase W0：前置决策与审计

- [ ] 确认事务边界策略（`safe_route_call` 统一 commit vs 其他方案）
- [ ] 扫描 `db.session.commit()` 分布，按“允许/禁止”分组并固化到文档
- [ ] 列出未被 `safe_route_call` 包裹的写接口清单（如存在）

### Phase W1：form_service 事务迁移

- [x] `BaseResourceService.upsert()` 移除 `commit()`，改为 `flush()`
- [x] `after_save()` / 子流程内移除 `commit()`（如 tags 同步）
- [ ] 回归验证：写接口行为不变（单测/手工关键路径）

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

- [ ] Instances：create/update/delete/restore
- [ ] Credentials：create/update/delete
- [ ] Users：create/update/delete
- [ ] AccountClassifications：相关写接口（最后）

### Phase W5：清理与收尾

- [ ] 清理：routes/services/form_service 内的直写 `db.session.*`
- [ ] 文档：`docs/standards/backend/` 补充写操作分层规范
- [ ] 门禁：引入写操作边界扫描（commit/add/delete）并作为 CI/本地检查项

## 变更记录

- 2025-12-26：创建 `002-backend-write-operation-boundary-progress.md`，并重写方案文档对齐最新规范。
- 2025-12-26：Tags 落地 write 样板：`TagsRepository` 增加写方法；新增 `TagWriteService`；tags 写路由收敛到 write service。
