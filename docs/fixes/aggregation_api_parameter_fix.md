# 聚合任务API参数错误修复

## 问题描述

聚合任务在执行过程中出现API参数错误：

```
SyncSessionService.complete_instance_sync() got an unexpected keyword argument 'success'
```

## 问题根源

在修复聚合任务卡住问题时，错误地使用了 `success` 参数调用 `complete_instance_sync()` 方法，但该方法不接受此参数。

### 错误的调用方式

**修复前**：
```python
# 成功情况
sync_session_service.complete_instance_sync(
    record.id, 
    success=True,  # ❌ 错误：该方法不接受 success 参数
    sync_details={...}
)

# 失败情况
sync_session_service.complete_instance_sync(
    record.id,
    success=False,  # ❌ 错误：该方法不接受 success 参数
    error_message=error_msg
)
```

### 正确的API签名

查看 `SyncSessionService.complete_instance_sync()` 方法的实际签名：

```python
def complete_instance_sync(
    self,
    record_id: int,
    accounts_synced: int = 0,
    accounts_created: int = 0,
    accounts_updated: int = 0,
    accounts_deleted: int = 0,
    sync_details: dict[str, Any] = None,
) -> bool:
```

对于失败情况，应该使用 `fail_instance_sync()` 方法：

```python
def fail_instance_sync(self, record_id: int, error_message: str, sync_details: dict[str, Any] = None) -> bool:
```

## 修复方案

### 1. 修复成功情况的调用

**修复后**：
```python
sync_session_service.complete_instance_sync(
    record.id,
    accounts_synced=1,  # 聚合任务使用1表示成功
    accounts_created=0,
    accounts_updated=0,
    accounts_deleted=0,
    sync_details={
        'total_aggregations': total_aggregations,
        'periods_processed': len(period_types)
    }
)
```

### 2. 修复失败情况的调用

**修复后**：
```python
sync_session_service.fail_instance_sync(
    record.id,
    error_message=error_msg
)
```

## 修复效果

### ✅ **解决API参数错误**
- 不再出现 `unexpected keyword argument 'success'` 错误
- 使用正确的API参数调用方法

### ✅ **正确的成功/失败处理**
- 成功时使用 `complete_instance_sync()` 方法
- 失败时使用 `fail_instance_sync()` 方法

### ✅ **聚合任务正常运行**
- 聚合任务能够正常执行，不再因为API错误而中断
- 实例记录状态能够正确更新

## 相关文件

- `app/tasks/database_size_aggregation_tasks.py` - 聚合定时任务
- `app/services/sync_session_service.py` - 同步会话服务

## 修复时间

2025-01-28

## 修复人员

AI Assistant
