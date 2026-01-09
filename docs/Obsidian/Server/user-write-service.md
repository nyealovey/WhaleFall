---
title: User Write Service(用户写操作/最后管理员保护)
aliases:
  - user-write-service
  - users-write-service
tags:
  - server
  - server/users
  - services
  - diagram
  - decision-table
status: draft
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: app/services/users/user_write_service.py
related:
  - docs/plans/2026-01-09-services-top38-docs.md
  - docs/reports/2026-01-08-services-complexity-report.md
  - "[[standards/doc/service-layer-documentation-standards]]"
---

# User Write Service(用户写操作/最后管理员保护)

> [!note] 本文目标
> 说明用户 create/update/delete 的编排与约束，重点是“系统至少需要一位活跃管理员”的防御逻辑（last admin guard），以及 username 唯一性冲突的 message_key 约定。

## 1. 概览(Overview)

入口：

- `UserWriteService.create(payload)`（`app/services/users/user_write_service.py:48`）
- `UserWriteService.update(user_id, payload)`（`app/services/users/user_write_service.py:74`）
- `UserWriteService.delete(user_id, operator_id=None)`（`app/services/users/user_write_service.py:100`）

约束：

- 用户名唯一（冲突时抛 `ConflictError(message_key="USERNAME_EXISTS")`）。
- 不能删除自己的账户。`app/services/users/user_write_service.py:104`
- 不能删除最后一个管理员账户（delete 时通过 count 判断）。`app/services/users/user_write_service.py:109`
- update 时禁止把最后一个活跃管理员变为非管理员或停用。`app/services/users/user_write_service.py:126`

## 2. 依赖与边界(Dependencies)

| 类型 | 组件 | 用途 | 失败语义(摘要) |
| --- | --- | --- | --- |
| Repo | `UsersRepository` | add/get/delete | 不存在 -> NotFoundError |
| Payload | `parse_payload` + `validate_or_raise` | 归一化 + 校验 | 校验失败 -> ValidationError |
| Role | `UserRole` | ADMIN 判定 | last admin guard |

## 3. 事务与失败语义(Transaction + Failure Semantics)

- 不 commit（由 route 层提交）。
- create/update：SQLAlchemyError -> `ValidationError("保存失败")`。`app/services/users/user_write_service.py:68`
- delete：
  - 不能删除自己 -> `ValidationError`。`app/services/users/user_write_service.py:104`
  - 不能删除最后管理员 -> `ValidationError`。`app/services/users/user_write_service.py:109`

## 4. 主流程图(Flow)

```mermaid
flowchart TB
    A["update(user_id, payload)"] --> B["_get_or_error(user_id)"]
    B --> C["parse_payload(payload, preserve_raw_fields=['password'])"]
    C --> D["validate_or_raise(UserUpdatePayload)"]
    D --> E["_ensure_username_unique(username)"]
    E --> F["_ensure_last_admin(user, {role:parsed.role,is_active:parsed.is_active})"]
    F --> G["apply fields + set_password if provided"]
    G --> H["repository.add(user)"]
    H --> I["return user"]
```

## 5. 时序图(Sequence)

```mermaid
sequenceDiagram
    autonumber
    participant Route as "Route"
    participant Svc as "UserWriteService"
    participant Repo as "UsersRepository"
    participant ORM as "User.query"

    Route->>Svc: delete(target_user_id, operator_id)
    Svc->>Repo: get_by_id(target_user_id)
    alt delete self
        Svc-->>Route: ValidationError
    else admin user
        Svc->>ORM: count admins
        alt last admin
            Svc-->>Route: ValidationError
        else ok
            Svc->>Repo: delete(user)
            Svc-->>Route: UserDeleteOutcome
        end
    end
```

## 6. 决策表/规则表(Decision Table)

### 6.1 last admin guard（update 时）

| 当前用户 | 目标状态 | 是否允许 |
| --- | --- | --- |
| 非管理员 | 任意 | 允许（不走 guard） |
| 管理员 | 仍为活跃管理员 | 允许 |
| 管理员 | 变为非管理员或停用 | 仅当存在其他活跃管理员时允许，否则拒绝 |

实现位置：`app/services/users/user_write_service.py:126`、`app/services/users/user_write_service.py:123`。

## 7. 兼容/防御/回退/适配逻辑

已清理（2026-01-09）：

- DI 收敛：`UserWriteService` 构造函数不再 `repository or UsersRepository()` 自行创建仓储，由 route/form handler 统一注入。
- payload 收敛：create/update 不再使用 `payload or {}` 兜底，直接 `parse_payload(payload, ...)`。
- 入参收敛：update 强约束 `is_active` 必传，不再做 `target_is_active` 回填；`_is_target_state_admin` 不再把缺省 is_active 视为 True。

| 位置(文件:行号)                                      | 类型  | 描述                         | 触发条件       | 清理条件/期限              |
| ---------------------------------------------- | --- | -------------------------- | ---------- | --------------------- |
| `app/services/users/user_write_service.py:107` | 防御  | delete 时使用 count 防止删除最后管理员 | 系统仅 1 位管理员 | 若引入更复杂 RBAC，可替换为策略引擎 |

## 8. 可观测性(Logs + Metrics)

- create/update/delete：`log_info`（module=`users`）`app/services/users/user_write_service.py:139`
- 冲突：`ConflictError(message_key=USERNAME_EXISTS)` 便于 UI 定位错误原因

## 9. 测试与验证(Tests)

最小验证命令：

- `uv run pytest -m unit tests/unit/services/test_user_write_service.py`

关键用例：

- username 重名 -> `message_key == USERNAME_EXISTS`
- last admin：停用/降权最后一个管理员会被拒绝
