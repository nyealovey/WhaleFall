# 后端写操作分层重构方案（Repository / Service 边界 + 事务策略）

> 状态：Draft
> 负责人：WhaleFall Team
> 创建：2025-12-25
> 更新：2025-12-25
> 范围：后端写操作（Create/Update/Delete）的分层边界与事务管理
> 关联：`docs/changes/refactor/001-backend-repository-serializer-boundary-plan.md`

---

## 1. 动机与范围

### 1.1 动机

`001-backend-repository-serializer-boundary-plan.md` 已完成只读链路的分层重构（`routes → services → repositories`），但写操作存在以下问题：

1. **事务边界混乱**：`safe_route_call` 统一 commit 与 `form_service.upsert()` 内部 commit 并存，部分场景出现双重 commit。
2. **写操作散落**：`db.session.add/delete/commit` 分布在 routes、services、form_service、tasks 多处，边界不清晰。
3. **form_service 定位模糊**：既做校验、又做持久化、又做关联同步，职责过重且与 Repository 模式重叠。
4. **关联关系维护不统一**：标签同步、权限同步等逻辑散落在 `after_save()` 钩子或 route 内。

### 1.2 范围

本方案聚焦：

- 写操作的 Repository 职责定义（与只读 Repository 的差异）
- 事务边界策略（统一 commit 位置）
- `form_service` 的定位与渐进迁移路径
- 关联关系维护、审计日志、缓存失效的收敛位置

### 1.3 不变约束

- 行为不变：现有 API 的输入输出契约保持稳定。
- 事务语义不变：单个请求内的原子性保证不降级。
- 性能门槛：写操作响应时间不因分层增加而显著劣化。

---

## 2. 现状分析

### 2.1 当前写操作的事务模式

| 模式 | 位置 | commit 时机 | 示例 |
|------|------|-------------|------|
| A | `safe_route_call` | 业务函数成功后统一 commit | 大部分 route |
| B | `BaseResourceService.upsert()` | service 内部 commit | form_service |
| C | `after_save()` 钩子 | 保存后再次 commit | `_sync_tags()` |
| D | tasks | 任务内部自行 commit | `accounts_sync_tasks.py` |

**问题**：模式 A + B 并存时，`safe_route_call` 的 commit 实际上是空操作（数据已被 form_service commit）；模式 C 在 `after_save()` 内再次 commit，若失败则前序数据已落库，无法回滚。

### 2.2 `db.session.commit()` 分布（证据）

```text
app/services/form_service/resource_service.py:173  # BaseResourceService.upsert()
app/services/form_service/instance_service.py:225  # _sync_tags() 内部
app/tasks/accounts_sync_tasks.py:239               # 任务完成时
app/tasks/capacity_aggregation_tasks.py:605        # 任务完成时
app/tasks/capacity_collection_tasks.py:484         # 任务完成时
app/tasks/log_cleanup_tasks.py:53                  # 清理任务
scripts/security/scrub_unified_logs.py:99          # 脚本
scripts/password/reset_admin_password.py:64        # 脚本
```

### 2.3 form_service 现有职责

`BaseResourceService` 提供的能力：

- `sanitize()`：数据清理
- `validate()`：校验
- `assign()`：赋值到模型
- `after_save()`：保存后钩子（关联同步、日志）
- `upsert()`：主流程（含 `db.session.add()` + `db.session.commit()`）

**问题**：form_service 同时承担了 Validator、Service、Repository 的职责，与只读重构的分层模式不一致。

---

## 3. 目标架构

### 3.1 分层职责（写操作扩展）

#### Routes（`app/routes/**`）

- 只做：参数解析/权限校验/调用 service/返回 `jsonify_unified_*`
- 不做：
  - 不直接操作 `db.session`（禁止 `add/delete/commit`）
  - 不做数据校验（交给 service 或 validator）

#### Services（`app/services/**`）

- 只做：
  - 业务编排（调用 repository、协调多个实体）
  - 数据校验（或委托给独立 Validator）
  - 审计日志记录
  - 缓存失效触发
- 不做：
  - 不直接拼 Query（交给 repository）
  - 不做 `db.session.commit()`（交给 route 层的 `safe_route_call` 或显式事务管理器）
- 输入输出：
  - 输入：已规范化的参数对象（dataclass/TypedDict）
  - 输出：领域结果对象（ORM 实体、DTO、或 `ServiceResult`）

#### Repositories（`app/repositories/**`）

- 只做：
  - 读：Query 组装与 DB 读取（已有）
  - 写：`db.session.add()` / `db.session.delete()` / `db.session.flush()`（新增）
  - 关联关系维护（如 `instance.tags.append(tag)`）
- 不做：
  - 不 `commit()`（由上层统一管理）
  - 不做业务校验（只做数据存在性检查）
  - 不做序列化

#### form_service（渐进迁移）

- 短期保留：复杂表单流程（sanitize → validate → assign → save）
- 渐进迁移：
  - 持久化逻辑迁移到 Repository
  - 校验逻辑迁移到 Service 或独立 Validator
  - 移除内部 `db.session.commit()`，改为 `flush()` + 依赖上层 commit

### 3.2 事务边界策略（ADR 决策点）

**推荐方案：`safe_route_call` 统一 commit**

```
route
  └─ safe_route_call(func)
       ├─ func() 执行业务逻辑
       │    ├─ service.create/update/delete()
       │    │    └─ repository.add/delete/flush()
       │    └─ 返回结果
       ├─ 成功 → db.session.commit()
       └─ 失败 → db.session.rollback()
```

**约束**：

- Repository 只做 `add/delete/flush`，禁止 `commit`
- Service 只做编排，禁止 `commit`
- form_service 迁移后移除内部 `commit`，改为 `flush`
- tasks 保持独立事务管理（不走 `safe_route_call`）

### 3.3 依赖方向（写操作扩展）

允许：
- `routes → services`
- `services → repositories`
- `repositories → models/db`（含 `add/delete/flush`）
- `services → validators`（可选）

禁止：
- `repositories → commit()`
- `services → commit()`
- `routes → repositories`（必须经过 service）
- `routes → db.session`（禁止直接操作）

---

## 4. 写操作 Repository 规范

### 4.1 职责边界

| 操作 | Repository 可做 | Repository 禁止 |
|------|-----------------|-----------------|
| 读取 | `query.filter().all()` | - |
| 新增 | `db.session.add(entity)` | `db.session.commit()` |
| 删除 | `db.session.delete(entity)` | `db.session.commit()` |
| 刷新 | `db.session.flush()` | `db.session.commit()` |
| 关联 | `entity.tags.append(tag)` | 业务校验 |
| 预加载 | `selectinload/joinedload` | - |

### 4.2 方法命名约定

```python
class TagsRepository:
    # 读操作（已有模式）
    def list_tags(self, filters: TagListFilters) -> Pagination[Tag]: ...
    def get_by_id(self, tag_id: int) -> Tag | None: ...
    def get_by_name(self, name: str) -> Tag | None: ...

    # 写操作（新增）
    def add(self, tag: Tag) -> Tag: ...          # db.session.add + flush
    def delete(self, tag: Tag) -> None: ...      # db.session.delete
    def sync_instance_tags(self, instance: Instance, tags: list[Tag]) -> None: ...
```

### 4.3 返回值约定

- `add()` 返回实体（flush 后可获取 ID）
- `delete()` 返回 `None`
- 批量操作返回受影响的实体列表或计数

---

## 5. form_service 迁移策略

### 5.1 短期（保持兼容）

- 保留 `BaseResourceService` 及其子类
- 移除 `upsert()` 内的 `db.session.commit()`，改为 `db.session.flush()`
- 依赖 `safe_route_call` 统一 commit

```python
# 修改前
def upsert(self, payload, resource=None):
    ...
    db.session.add(instance)
    db.session.commit()  # ← 移除
    self.after_save(instance, data)
    return ServiceResult.ok(instance)

# 修改后
def upsert(self, payload, resource=None):
    ...
    db.session.add(instance)
    db.session.flush()  # ← 改为 flush（获取 ID）
    self.after_save(instance, data)
    return ServiceResult.ok(instance)
```

### 5.2 中期（渐进迁移）

- 简单 CRUD：直接用 `Repository + Service`，不经过 form_service
- 复杂表单：保留 form_service，但内部调用 Repository 做持久化

```python
# 迁移后的 TagFormService
class TagFormService(BaseResourceService[Tag]):
    def __init__(self):
        self._repository = TagsRepository()

    def assign(self, tag: Tag, data: MutablePayloadDict) -> None:
        tag.name = data["name"]
        tag.display_name = data["display_name"]
        ...

    def after_save(self, tag: Tag, data: MutablePayloadDict) -> None:
        # 关联同步也交给 repository
        self._repository.sync_category(tag, data.get("category"))
```

### 5.3 长期（可选）

- 评估是否完全废弃 form_service，统一到 `Service + Repository` 模式
- 若保留，重命名为 `FormOrchestrator` 以明确其"编排"职责

---

## 6. 分阶段计划

### Phase W0：前置决策与审计

- [ ] 确认事务边界策略（本方案推荐 `safe_route_call` 统一 commit）
- [ ] 审计现有 `db.session.commit()` 分布，标记需要迁移的位置
- [ ] 确认 form_service 定位（短期保留 + 渐进迁移）

### Phase W1：form_service 事务迁移

- [ ] `BaseResourceService.upsert()` 移除 `commit()`，改为 `flush()`
- [ ] `after_save()` 钩子内移除 `commit()`（如 `_sync_tags()`）
- [ ] 验证：现有写操作 API 行为不变

### Phase W2：写操作 Repository 样板（以 Tags 为例）

- [ ] 新增 `TagsRepository.add()` / `delete()` / `sync_instance_tags()`
- [ ] 迁移 `_delete_tag_record()` 从 route 到 Repository
- [ ] 迁移 `_sync_tags()` 从 form_service 到 Repository
- [ ] 收敛 route：`create_tag` / `update_tag` / `delete` 只调 service

### Phase W3：写操作 Service 样板

- [ ] 新增 `TagWriteService.create()` / `update()` / `delete()`
- [ ] 职责：校验 + 调用 Repository + 审计日志
- [ ] route 改为调用 `TagWriteService`

### Phase W4：扩展到其他域

按优先级迁移：

1. Instances（`create_instance` / `delete_instance` / `restore_instance`）
2. Credentials（`create_credential` / `update_credential` / `delete_credential`）
3. Users（`create_user` / `update_user` / `delete_user`）
4. AccountClassifications（复杂度高，建议最后）

### Phase W5：清理与收尾

- [ ] 移除 form_service 内的直接 `db.session` 操作（已迁移到 Repository）
- [ ] 更新文档：`docs/standards/backend/` 补充写操作分层规范
- [ ] 门禁：检测 route 内是否存在 `db.session.add/delete/commit`

---

## 7. 验收指标

### 7.1 行为不变

- 现有写操作 API 的输入输出契约保持稳定
- 单元测试 / 契约测试全部通过

### 7.2 边界清晰

- Route 内无 `db.session.add/delete/commit`（门禁检测）
- Service 内无 `db.session.commit`
- Repository 内无 `db.session.commit`
- `commit` 只出现在 `safe_route_call` 和 tasks

### 7.3 可回退

- 每次 PR 只迁移 1 个域 / 1 个端点
- 问题出现时可直接 `git revert`

---

## 8. 风险与缓解

| 风险 | 场景 | 缓解 |
|------|------|------|
| 事务不一致 | 移除 form_service commit 后，safe_route_call 未正确 commit | 迁移前确认 route 使用 safe_route_call 包装 |
| flush 后 ID 未生成 | 某些场景依赖 commit 后的 ID | flush 即可获取 ID，无需 commit |
| after_save 失败 | 关联同步失败但主实体已 flush | 统一在 safe_route_call 内 rollback |
| tasks 事务冲突 | tasks 保持独立 commit，与 route 模式不同 | tasks 不走 safe_route_call，保持现状 |

---

## 9. 与只读重构的关系

| 维度 | 只读重构（001） | 写操作重构（本方案） |
|------|-----------------|----------------------|
| Repository 职责 | Query 组装 | Query + add/delete/flush |
| 事务边界 | 无需关心 | 核心问题，统一到 safe_route_call |
| 序列化 | Flask-RESTX marshal | 不涉及 |
| 现有抽象 | 无 | form_service 需要迁移 |
| 依赖关系 | 可独立完成 | 建议在只读重构完成后启动 |

---

## 10. 清理计划

迁移完成后需要清理：

- [ ] form_service 内的 `db.session.commit()` 调用
- [ ] route 内的 `db.session.add/delete` 调用
- [ ] `after_save()` 钩子内的 `db.session.commit()` 调用
- [ ] 更新 `docs/standards/backend/` 补充写操作分层规范

---

## 附录 A：写操作端点清单（待迁移）

### Tags

- `POST /tags/api/create` → `TagWriteService.create()`
- `POST /tags/api/edit/<tag_id>` → `TagWriteService.update()`
- `POST /tags/api/delete/<tag_id>` → `TagWriteService.delete()`
- `POST /tags/api/batch_delete` → `TagWriteService.batch_delete()`

### Instances

- `POST /instances/api/create` → `InstanceWriteService.create()`
- `POST /instances/api/<instance_id>/delete` → `InstanceWriteService.delete()`
- `POST /instances/api/<instance_id>/restore` → `InstanceWriteService.restore()`
- `POST /instances/api/<instance_id>/edit` → `InstanceWriteService.update()`

### Credentials

- `POST /credentials/api/create` → `CredentialWriteService.create()`
- `PUT /credentials/api/<credential_id>` → `CredentialWriteService.update()`
- `DELETE /credentials/api/<credential_id>` → `CredentialWriteService.delete()`

### Users

- `POST /users/api/users` → `UserWriteService.create()`
- `PUT /users/api/users/<user_id>` → `UserWriteService.update()`
- `DELETE /users/api/users/<user_id>` → `UserWriteService.delete()`

### AccountClassifications

- `POST /accounts/classifications/api/classifications` → `ClassificationWriteService.create()`
- `PUT /accounts/classifications/api/classifications/<id>` → `ClassificationWriteService.update()`
- `DELETE /accounts/classifications/api/classifications/<id>` → `ClassificationWriteService.delete()`
- `POST /accounts/classifications/api/rules` → `RuleWriteService.create()`
- `PUT /accounts/classifications/api/rules/<id>` → `RuleWriteService.update()`
- `DELETE /accounts/classifications/api/rules/<id>` → `RuleWriteService.delete()`

### Scheduler

- `PUT /scheduler/api/jobs/<job_id>` → `SchedulerJobWriteService.update()`
- `POST /scheduler/api/jobs/<job_id>/pause` → `SchedulerJobWriteService.pause()`
- `POST /scheduler/api/jobs/<job_id>/resume` → `SchedulerJobWriteService.resume()`
- `POST /scheduler/api/jobs/<job_id>/run` → `SchedulerJobWriteService.run()`

### Cache

- `POST /cache/api/clear/*` → `CacheService.clear_*()`

### Sync

- `POST /accounts/api/sync-all` → `AccountsSyncService.sync_all()`
- `POST /accounts/api/instances/<id>/sync` → `AccountsSyncService.sync_instance()`
- `POST /databases/api/instances/<id>/sync-capacity` → `CapacitySyncService.sync()`
