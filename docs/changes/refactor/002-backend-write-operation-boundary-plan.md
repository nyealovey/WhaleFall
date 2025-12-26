# 后端写操作分层重构方案（Repository / Service 边界 + 事务策略）

> 状态：Draft
> 负责人：WhaleFall Team
> 创建：2025-12-25
> 更新：2025-12-26
> 范围：后端写操作（Create/Update/Delete）的分层边界与事务管理
> 关联：规范：[changes-standards](../../standards/changes-standards.md)；前置：[001-backend-repository-serializer-boundary-plan](001-backend-repository-serializer-boundary-plan.md)；进度：[002-backend-write-operation-boundary-progress](002-backend-write-operation-boundary-progress.md)

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
| A | `safe_route_call` | 业务函数成功后统一 commit | `app/utils/route_safety.py` |
| B | form_service（`upsert`） | service 内部 commit | `app/services/form_service/resource_service.py` |
| C | form_service（子流程/钩子） | 保存后阶段性 commit | `app/services/form_service/instance_service.py` |
| D | 其他 services（同步/聚合等） | service 内部阶段性 commit | `app/services/**` |
| E | routes（少量遗留） | route 内显式 commit | `app/routes/**` |
| F | tasks / worker / scripts | 入口处自行 commit | `app/tasks/**`、`scripts/**` |

**问题**：

- 模式 A + B 并存时，`safe_route_call` 的 commit 变为“空操作”（数据可能已被 form_service 提前落库）。
- 模式 C/D/E 造成“事务边界不透明”：内部阶段性 commit 后，即便后续逻辑失败，也无法回滚到请求开始时的状态。
- 入口不一致导致规则难以门禁：无法简单回答“哪里允许 commit，哪里禁止 commit”。

### 2.2 `db.session.commit()` 分布（证据）

> 说明：以下为 2025-12-26 的仓库扫描摘要；完整清单可用 `rg -n "db\\.session\\.commit\\(" app scripts` 生成。

```text
# 允许：事务边界入口（保留）
app/utils/route_safety.py:146                              # safe_route_call（请求事务边界）
app/utils/database_batch_manager.py:150                    # batch manager（任务/批处理入口）
app/utils/logging/queue_worker.py:184                      # queue worker（任务入口）

app/tasks/log_cleanup_tasks.py:53                          # task 入口 commit（允许）
app/tasks/accounts_sync_tasks.py:239                       # task 入口 commit（允许）
app/tasks/accounts_sync_tasks.py:257                       # task 入口 commit（允许）
app/tasks/capacity_collection_tasks.py:484                 # task 入口 commit（允许）
app/tasks/capacity_collection_tasks.py:517                 # task 入口 commit（允许）
app/tasks/capacity_aggregation_tasks.py:605                # task 入口 commit（允许）
app/tasks/capacity_aggregation_tasks.py:669                # task 入口 commit（允许）

scripts/admin/security/scrub_unified_logs.py:99            # 运维脚本入口 commit（允许）
scripts/admin/password/reset_admin_password.py:64          # 运维脚本入口 commit（允许）

# 禁止：可复用的 services 层（需迁移到事务边界）
# （已清零）
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

## 6. 兼容/适配/回退策略

### 6.1 兼容/适配（form_service 作为过渡层）

- **对外契约不变**：写接口的参数/返回封套/错误口径不因为“分层/事务调整”而变化（如需变化，必须同 PR 更新调用方与测试）。
- **form_service 过渡保留**：短期允许继续使用 `BaseResourceService` 的 sanitize/validate/assign/after_save，但必须移除内部 `commit()`，改为 `flush()` 并依赖上层统一提交。
- **写链路样板先行**：先用 Tags 落地 `Repository(write) + WriteService` 样板，再按域扩展，避免全仓并行改动导致风险失控。
- **不引入双路径开关**：不在 routes 内保留 `if new: ... else: ...` 的双实现；每次 PR 粒度小，必要时直接回滚 PR。

### 6.2 回退策略（PR 级可回退）

- 每次 PR 只迁移 **1 个域 / 1～2 个端点**（或同一域的一组强耦合端点），保证 `git revert` 的回退影响面可控。
- 移除 form_service 内部 `commit()` 前，必须先确认对应写接口在成功路径上一定会走到事务边界（例如被 `safe_route_call` 包裹）；否则先改入口，再改 form_service。
- 回滚优先级：**先回滚 PR**（恢复到迁移前可用状态）→ 再补充根因分析与后续修复计划。

---

## 7. 分阶段计划

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

## 8. 验收指标

### 8.1 行为不变

- 现有写操作 API 的输入输出契约保持稳定
- 单元测试 / 契约测试全部通过

### 8.2 边界清晰

- Route 内无 `db.session.add/delete/commit`（门禁检测）
- Service 内无 `db.session.commit`
- Repository 内无 `db.session.commit`
- `commit` 只出现在事务边界入口（`safe_route_call`、tasks/worker、scripts）

### 8.3 可回退

- 每次 PR 只迁移 1 个域 / 1～2 个端点
- 问题出现时可直接 `git revert`

---

## 9. 验证与门禁

### 9.1 必跑命令（按 PR）

- 单元测试：`pytest -m unit`
- Ruff：`./scripts/ci/ruff-report.sh style`（或 `ruff check <paths>`）
- Pyright：`./scripts/ci/pyright-report.sh`（或 `make typecheck`）

### 9.2 写操作边界门禁（建议逐步引入）

- 扫描 `commit`：`rg -n "db\\.session\\.commit\\(" app scripts`
- 扫描 routes 直写：`rg -n "db\\.session\\.(add|delete|commit)\\(" app/routes`
- routes 门禁脚本：`./scripts/ci/db-session-route-write-guard.sh`
- services commit 漂移门禁：`./scripts/ci/db-session-commit-services-drift-guard.sh`
- 目标状态：`commit()` 只出现在**事务边界入口**（`safe_route_call`、tasks/worker、scripts），而不是可复用的 service/repository/form_service 方法内部。

### 9.3 Review Checklist（写操作 PR 必过）

- route 文件内无 `db.session.commit()`；写接口统一走事务边界（例如 `safe_route_call`）。
- service/repository/form_service 内无 `db.session.commit()`；如需获取主键/外键关系，使用 `flush()`。
- 关联同步（tags/permissions 等）不再在钩子里二次提交；失败可被事务边界回滚。

---

## 10. 风险与回滚

| 风险 | 场景 | 缓解 |
|------|------|------|
| 事务不一致 | 移除 form_service commit 后，safe_route_call 未正确 commit | 迁移前确认 route 使用 safe_route_call 包装 |
| flush 后 ID 未生成 | 某些场景依赖 commit 后的 ID | flush 即可获取 ID，无需 commit |
| after_save 失败 | 关联同步失败但主实体已 flush | 统一在 safe_route_call 内 rollback |
| tasks 事务冲突 | tasks 保持独立 commit，与 route 模式不同 | tasks 不走 safe_route_call，保持现状 |

回滚策略：

- 优先 `git revert` 回滚到迁移前状态（保持系统可用）。
- 回滚后补充：触发问题的端点/请求路径、异常堆栈、数据库一致性影响（是否出现“部分落库”）。

---

## 11. 与只读重构的关系

| 维度 | 只读重构（001） | 写操作重构（本方案） |
|------|-----------------|----------------------|
| Repository 职责 | Query 组装 | Query + add/delete/flush |
| 事务边界 | 无需关心 | 核心问题，统一到 safe_route_call |
| 序列化 | Flask-RESTX marshal | 不涉及 |
| 现有抽象 | 无 | form_service 需要迁移 |
| 依赖关系 | 可独立完成 | 建议在只读重构完成后启动 |

---

## 12. 清理计划

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
