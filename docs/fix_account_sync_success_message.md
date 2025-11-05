# 对齐账户同步与容量同步的日志处理逻辑

## 背景
- 用户在实例详情页点击“同步账户”后，后端任务执行成功，但通知提示为失败。
- 容量同步（`sync-capacity`）在同一界面和日志链路中表现正常，可作为对照组。
- 核心目标：让**账户同步**的响应与日志结构与**容量同步**保持一致，避免前端得到不完整状态导致误判。

## 现象复现
1. 进入某实例详情页，点击“同步账户”。
2. `app/services/account_sync/account_sync_service.py` 返回 `{"success": True, ...}`，但缺少 `message`。
3. `app/routes/account_sync.py::_normalize_sync_result()` 生成默认信息，前端缺少明确的 `status/message` 组合，从日志流水也无法直接判断成功。
4. 前端根据返回值推断失败，展示红色提示；结构化日志中也没有类似容量同步的“任务完成”消息。

## 根因概述
- **返回体缺字段**：账户同步结果构造函数 `_build_result()` 未填充 `message`，而容量同步在服务层和路由层都额外提供了成功提示。
- **日志语义不统一**：容量同步会在 `sync_logger` 中写入阶段性日志（`phase=start|collection|completed`），并在路由层通过 `jsonify_unified_success` 再次补充成功消息；账户同步缺少终态日志。
- **前端依赖消息语义**：界面组合 `success/status/message` 决定提示样式；当缺少 message 或 status 不为 `completed` 时会回退到错误提示。

## 容量同步链路（对照）
| 层级 | 关键点 | 代码参考 |
| --- | --- | --- |
| 服务层 | `_collect_instance_capacity()` 构建包含 `success + message` 的结果，并记录阶段日志 | `app/services/database_sync/capacity_sync_service.py` |
| 路由层 | `jsonify_unified_success(data, message=...)` 再补充外层提示，并写入完成日志 | `app/routes/capacity.py:sync_instance_capacity` |
| 日志 | 使用 `get_sync_logger()`，输出 `module="capacity_sync"`、`phase`、`session_id` 等字段 | `app/tasks/capacity_collection_tasks.py` |

容量同步的结构化日志具备明确的开始、阶段、结束三种事件，便于统一消费。

## 对齐方案

### 1. 服务层补充 message + 阶段日志
文件：`app/services/account_sync/account_sync_service.py`

```python
def _build_result(self, summary: dict[str, dict[str, int]]) -> dict[str, Any]:
    # ... 统计新增、更新、移除数据 ...
    message = "、".join(parts) if parts else "账户同步完成"
    return {
        "success": True,
        "message": message,
        "synced_count": processed,
        "added_count": added + reactivated,
        "modified_count": updated,
        "removed_count": removed,
    }

def _emit_completion_log(..., result: dict[str, Any]) -> None:
    message = result.get("message") or result.get("error") or "账户同步完成"
    log_kwargs = {
        "module": "account_sync",
        "operation": "sync_accounts",
        "phase": "completed" if result.get("success", True) else "error",
        "instance_id": instance.id,
        "instance_name": instance.name,
        "session_id": session_id,
        "sync_type": sync_type,
        "synced_count": result.get("synced_count", 0),
        "added_count": result.get("added_count", 0),
        "modified_count": result.get("modified_count", 0),
        "removed_count": result.get("removed_count", 0),
        "message": message,
    }
    if result.get("success", True):
        self.sync_logger.info("实例账户同步完成", **log_kwargs)
    else:
        self.sync_logger.error("实例账户同步失败", **log_kwargs)
```

要点：
- `_build_result()` 负责构造带 `message` 的结果；`_emit_completion_log()` 统一输出成功/失败终态日志。
- `sync_accounts()/ _sync_with_existing_session()` 在结束时调用 `_emit_completion_log()`，与容量同步保持相同的日志字段。

### 2. 路由层包装统一响应
文件：`app/routes/account_sync.py`

```python
if is_success:
    return jsonify_unified_success(
        data={"result": normalized},
        message=normalized["message"],
    )

return jsonify_unified_error_message(
    failure_message,
    extra={"result": normalized, "instance_id": instance.id},
)
```

同时在 `_normalize_sync_result` 中保留：
```python
normalized["status"] = "completed" if is_success else "failed"
```

这样成功路径与容量同步保持完全一致的返回格式：

```json
{
  "success": true,
  "message": "同步 12 个账户、新增 2 个",
  "status": "completed",
  "data": { ... }
}
```

### 3. 日志标准化清单
为保证消费端不再特殊处理账户同步，建议遵循以下字段约定（与容量同步一致）：
- `module`: 固定使用 `"account_sync"`。
- `phase`: 可取 `start|connection|inventory|collection|completed|error`，与容量同步的阶段语义对齐。
- `session_id` / `instance_id` / `instance_name`: 保持原有写法。
- 失败时仍然写入 `phase="error"` 并附 `error` 字段，成功时确保最后一条 `phase="completed"`。

### 4. 前端展示策略
- 以 `success` 或 `status === "completed"` 为成功依据，避免通过 `message` 文案判定。
- 使用 `message` 仅做展示文本，默认兜底为“账户同步完成”。
- 建议复用容量同步的提示组件，保持 UI 行为一致。

## 验证步骤
1. 本地运行账户同步任务（可通过详情页或 `sync_accounts(manual_run=True)`）。
2. 查看返回体，确认包含 `success=true`、`status="completed"` 与详细 `message`。
3. 检查 `sync_logs` 或结构化日志输出，确认存在 `phase="completed"` 的账户同步日志。
4. 页面刷新后前端展示绿色成功提示。
5. 在报错场景（模拟连接失败）检查日志与提示同样按约定显示。

## 推广建议
- 将上述字段规范记录到 `docs/development/logging.md`（若已存在类似文档则更新）。
- 后续新增同步类任务（如权限同步、慢日志同步等）均按照“服务层 message + 路由层统一响应 + 阶段日志”模式实现。
- 在自动化测试中增加对 `message` / `status` 字段的断言，防止回归。
