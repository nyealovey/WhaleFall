# SyncInstanceRecord 使用指南

## 概述

`SyncInstanceRecord` 模型现在支持多种同步类型，并具有智能的成功/失败判断逻辑。

## 支持的同步类型

### 1. 账户同步 (account)
- **成功条件**: `items_synced > 0` 且包含账户数据
- **数据检查**: `sync_details` 中包含账户相关信息
  - `account_count`, `account_types`, `account_list`, `accounts`, `user_count`, `admin_count`, `account_data`, `permissions`, `account_details`, `sync_result`, `account_info`

### 2. 容量同步 (capacity)
- **成功条件**: `items_synced > 0` 且包含容量数据
- **数据检查**: `sync_details` 中包含容量相关信息
  - `total_size_mb`, `database_count`, `avg_size_mb`, `max_size_mb`, `min_size_mb`, `capacity_data`

### 3. 聚合统计 (aggregation)
- **成功条件**: `items_synced > 0` 且包含聚合数据
- **数据检查**: `sync_details` 中包含聚合相关信息
  - `aggregation_count`, `period_type`, `calculated_at`, `aggregation_data`, `statistics_generated`

### 4. 配置同步 (config)
- **成功条件**: `items_synced > 0` 且包含配置数据
- **数据检查**: `sync_details` 中包含配置相关信息
  - `config_count`, `config_items`, `config_data`, `settings`, `configuration`, `config_details`, `sync_config`

### 5. 其他类型 (other)
- **成功条件**: `items_synced > 0`
- **数据检查**: 至少同步到数据

## 使用示例

### 创建同步记录

```python
# 账户同步
account_record = SyncInstanceRecord(
    session_id="session-123",
    instance_id=1,
    instance_name="MySQL实例",
    sync_category="account"
)

# 容量同步
capacity_record = SyncInstanceRecord(
    session_id="session-456",
    instance_id=2,
    instance_name="PostgreSQL实例",
    sync_category="capacity"
)

# 聚合统计
aggregation_record = SyncInstanceRecord(
    session_id="session-789",
    instance_id=3,
    instance_name="Oracle实例",
    sync_category="aggregation"
)
```

### 完成同步

```python
# 账户同步完成
account_record.complete_sync(
    items_synced=100,      # 同步了100个账户
    items_created=5,       # 新增5个
    items_updated=90,      # 更新90个
    items_deleted=5,       # 删除5个
    sync_details={"account_types": ["user", "admin"]}
)

# 容量同步完成
capacity_record.complete_sync(
    items_synced=50,       # 同步了50个数据库
    items_created=2,       # 新增2个
    items_updated=45,      # 更新45个
    items_deleted=3,       # 删除3个
    sync_details={
        "total_size_mb": 1024,
        "database_count": 50,
        "avg_size_mb": 20.48
    }
)

# 聚合统计完成
aggregation_record.complete_sync(
    items_synced=4,        # 生成了4个聚合记录
    items_created=4,       # 新增4个
    items_updated=0,       # 更新0个
    items_deleted=0,       # 删除0个
    sync_details={
        "aggregation_count": 4,
        "period_type": "daily",
        "calculated_at": "2024-01-01T00:00:00Z"
    }
)
```

### 判断同步状态

```python
# 检查是否成功
if account_record.is_successful():
    print("账户同步成功")
else:
    print(f"账户同步失败: {account_record.get_failure_reason()}")

# 检查是否失败
if capacity_record.is_failed():
    print(f"容量同步失败: {capacity_record.get_failure_reason()}")

```

### 获取同步摘要

```python
summary = account_record.get_sync_summary()
print(f"""
同步摘要:
- 状态: {summary['status']}
- 是否成功: {summary['is_successful']}
- 是否失败: {summary['is_failed']}
- 失败原因: {summary['failure_reason']}
- 同步分类: {summary['sync_category_display']}
- 同步数量: {summary['items_synced']}
- 执行时间: {summary['duration_seconds']}秒
""")
```

### 查询记录

```python
# 查询成功的记录
successful_records = SyncInstanceRecord.get_successful_records(limit=10)

# 查询失败的记录
failed_records = SyncInstanceRecord.get_failed_records(limit=10)

# 按分类查询
capacity_records = SyncInstanceRecord.get_records_by_category("capacity")

# 按实例和分类查询
instance_capacity_records = SyncInstanceRecord.get_records_by_instance_and_category(
    instance_id=1, 
    sync_category="capacity"
)

# 获取失败统计
stats = SyncInstanceRecord.get_failure_statistics()
print(f"总记录数: {stats['total_records']}")
print(f"成功率: {stats['success_rate']:.2f}%")
print(f"失败率: {stats['failure_rate']:.2f}%")
print(f"失败原因统计: {stats['failure_reasons']}")
```

## 失败原因说明

### 账户同步失败
- `items_synced=0`: 未同步到任何账户数据
- 无有效账户数据: `sync_details` 中缺少账户相关信息

### 容量同步失败
- `items_synced=0`: 未同步到任何容量数据
- 无有效容量数据: `sync_details` 中缺少容量相关信息

### 聚合统计失败
- `items_synced=0`: 未生成任何聚合数据
- 无有效聚合数据: `sync_details` 中缺少聚合相关信息

### 配置同步失败
- `items_synced=0`: 未同步到任何配置数据
- 无有效配置数据: `sync_details` 中缺少配置相关信息

