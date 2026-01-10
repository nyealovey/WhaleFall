---
title: Users Read Services(用户列表/统计)
aliases:
  - users-read-services
  - users-list-service
  - users-stats-service
tags:
  - reference
  - reference/service
  - service
  - service/users
  - services
  - diagram
status: draft
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: app/services/users/users_list_service.py
related:
  - "[[API/users-api-contract]]"
  - "[[reference/service/user-write-service]]"
  - "[[standards/doc/service-layer-documentation-standards]]"
---

# Users Read Services(用户列表/统计)

> [!note] 本文目标
> 说明 UsersListService/UsersStatsService 的读路径与输出字段口径.

## 1. 概览(Overview)

覆盖文件:

- `app/services/users/users_list_service.py`
- `app/services/users/users_stats_service.py`
- repository: `app/repositories/users_repository.py`

核心入口:

- `UsersListService.list_users(filters) -> PaginatedResult[UserListItem]`
- `UsersStatsService.get_stats() -> dict[str, int]`

## 2. 事务与失败语义(Transaction + Failure Semantics)

- 读服务, 不做 commit.
- service 不捕获异常; DB/not found 由 repo/route 层处理.

## 3. 主流程图(Flow)

```mermaid
flowchart TB
    A["GET /api/v1/users"] --> L["UsersListService.list_users(filters)"]
    L --> R1["repo.list_users(filters)"]
    R1 --> DTO1["UserListItem[] (created_at=%Y-%m-%d)"]
    DTO1 --> Out1["PaginatedResult"]

    B["GET /api/v1/users/stats"] --> S["UsersStatsService.get_stats()"]
    S --> R2["repo.fetch_stats()"]
    R2 --> Out2["{total,active,...}"]
```

## 4. 兼容/防御/回退/适配逻辑

| 位置(文件:行号) | 类型 | 描述 | 触发条件 | 清理条件/期限 |
| --- | --- | --- | --- | --- |
| `app/services/users/users_list_service.py:20` | 防御 | `repository or UsersRepository()` 兜底 | 调用方未注入 | 若统一 DI, 改为强制注入 |
| `app/services/users/users_stats_service.py:17` | 防御 | `repository or UsersRepository()` 兜底 | 调用方未注入 | 同上 |
| `app/services/users/users_list_service.py:30` | 兼容 | created_at None -> null | 历史数据缺 created_at | 若 schema 强约束, 可收敛 |

## 5. 测试与验证(Tests)

最小验证命令:

- `uv run pytest -m unit tests/unit/routes/test_api_v1_users_contract.py`
