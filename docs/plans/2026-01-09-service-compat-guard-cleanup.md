# Service Compatibility/Guard Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按 `docs/Obsidian/Server/*` 的“清理条件”收敛/移除遗留兜底逻辑（兼容/防御/回退/适配），让服务层语义更强、更可测，并减少 silent fallback。

**Architecture:** 以“测试先行”的方式（RED→GREEN→REFACTOR）逐个 service 清理：先补齐单元测试锁定期望语义，再修改实现与调用方，最后同步更新对应 service 文档中的第 7 节清单，确保文档与代码一致。

**Tech Stack:** Flask + SQLAlchemy + pytest（`-m unit`），Obsidian Markdown（service docs）。

---

## Task 1: SyncSessionService 清理返回 False 兜底

**Files:**
- Modify: `app/services/sync_session_service.py`
- Test: `tests/unit/services/test_sync_session_service_cleanup.py`
- Modify: `docs/Obsidian/Server/sync-session-service.md`

**Step 1: 写 failing tests（record 不存在/写入异常语义）**
- 断言 `start_instance_sync/complete_instance_sync/fail_instance_sync` 在 record 不存在时抛 `NotFoundError`（不再 `return False`）。
- 断言 `start_instance_sync` 在写入异常时抛出异常（不再吞并 `return False`）。

**Step 2: 运行测试确认 RED**
- Run: `uv run pytest -m unit tests/unit/services/test_sync_session_service_cleanup.py -q`
- Expected: 新增用例失败（当前实现仍 return False）。

**Step 3: 最小实现让测试变绿**
- 将 start/complete/fail 的“record 不存在”分支改为抛 `NotFoundError`。
- 将 start 的异常分支由“记录日志 + return False”改为“记录日志 + raise”。
- 同步调整所有调用方（tasks/services）去掉 `if ...: commit` 的 bool 依赖，改为“成功即继续，失败抛出由上层捕获”。

**Step 4: 运行 unit tests 确认 GREEN**
- Run: `uv run pytest -m unit tests/unit/services/test_sync_session_service_cleanup.py -q`
- Expected: PASS

**Step 5: 更新文档第 7 节**
- 将 “record 不存在返回 False” 的条目移除/改为强约束描述，并补充新的失败语义。

---

## Task 2: Partition 管理清理未来批量/索引创建遗留

**Files:**
- Modify: `app/services/partition_management_service.py`
- Modify: `app/services/partition/partition_read_service.py`
- Modify: `app/tasks/partition_management_tasks.py`
- Test: `tests/unit/services/test_partition_management_service_cleanup.py`
- Test: `tests/unit/services/test_partition_read_service_missing_partitions.py`（如新增）
- Modify: `docs/Obsidian/Server/partition-services.md`

**Step 1: 写 failing tests（不再对每个分区显式建索引）**
- 断言 `create_partition` 不再执行包含 `CREATE INDEX` 的 SQL（依赖父表 partitioned indexes）。

**Step 2: 写 failing tests（移除 months_ahead=3 的“未来分区缺失”预期）**
- 断言缺失分区检查只覆盖“当前月 + 下个月”（避免长期 warning 且前端无批量创建入口）。

**Step 3: 运行测试确认 RED**
- Run: `uv run pytest -m unit tests/unit/services/test_partition_management_service_cleanup.py -q`
- Run: `uv run pytest -m unit tests/unit/services/test_partition_read_service_missing_partitions.py -q`

**Step 4: 最小实现让测试变绿**
- `PartitionManagementService.create_partition` 移除 `_create_partition_indexes` 调用/实现。
- `PartitionReadService._resolve_missing_partitions` 与 `partition_management_tasks.get_partition_management_status` 的 required months 从 3 收敛到 2（当前 + 下月）。

**Step 5: 更新文档第 7 节**
- 删除/调整 “execute(CREATE INDEX IF NOT EXISTS …)” 描述与流程图。
- 明确未来分区检查策略已收敛（不再要求 3 个月）。

---

## Task 3: 校验 tags/user write service 清理结论未回退

**Files:**
- Verify only: `app/services/tags/tag_write_service.py`
- Verify only: `app/services/users/user_write_service.py`

**Step 1: 快速回归检查**
- 确认不再存在 `repository or XxxRepository()` 与 `payload or {}` 的 service 层兜底。
- 确认 user “最后管理员保护”仍保留。

