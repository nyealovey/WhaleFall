# 同步类型枚举更新文档

## 概述

本次更新将账户同步分类从原有的混合命名方式统一为4个清晰的英文类型，提高了代码的可读性和维护性。

## 更新内容

### 1. 新的同步类型定义

| 中文名称 | 英文名称 | 描述 | 使用场景 |
|---------|---------|------|---------|
| 手动单台 | `MANUAL_SINGLE` | 用户手动触发单个数据库实例的账户同步 | 实例详情页面直接同步 |
| 手动批量 | `MANUAL_BATCH` | 用户手动触发多个数据库实例的批量账户同步 | 同步记录页面批量同步 |
| 手动任务 | `MANUAL_TASK` | 用户手动执行预定义的任务 | 任务管理界面手动执行 |
| 定时任务 | `SCHEDULED_TASK` | 系统按预定时间自动执行的定时任务 | APScheduler自动触发 |

### 2. 代码更新范围

#### 2.1 常量定义 (`app/constants.py`)
- 新增 `SyncType` 枚举类
- 定义了4个同步类型的常量值
- 更新了 `__all__` 导出列表

#### 2.2 数据模型 (`app/models/sync_session.py`)
- 更新 `SyncSession` 模型中的 `sync_type` 枚举定义
- 更新了构造函数和文档字符串

#### 2.3 路由处理 (`app/routes/account_sync.py`)
- 更新了同步记录页面的类型过滤逻辑
- 修改了批量同步的 `sync_type` 参数

#### 2.4 模板显示 (`app/templates/accounts/sync_records.html`)
- 更新了同步类型筛选下拉框
- 更新了同步类型显示标签和图标
- 修改了重试按钮的显示条件

#### 2.5 服务层更新
- `AccountSyncService`: 更新了方法文档和参数说明
- `SyncSessionService`: 更新了创建会话的方法文档
- `DatabaseService`: 添加了 `sync_type` 参数支持
- `tasks.py`: 更新了定时任务的同步类型

### 3. 数据库迁移

#### 3.1 迁移脚本
- `sql/update_sync_type_enum.sql`: PostgreSQL版本
- `sql/update_sync_type_enum_sqlite.sql`: SQLite版本
- `scripts/update_sync_type_enum.py`: Python迁移脚本

#### 3.2 数据更新映射
```sql
-- 旧值 -> 新值
'scheduled' -> 'scheduled_task'
'manual' -> 'manual_single'
'batch' -> 'manual_batch'
'task' -> 'manual_task'
```

### 4. 向后兼容性

本次更新保持了向后兼容性：
- 现有的同步记录仍然可以正常显示
- 新的枚举值可以正确处理旧数据
- 迁移脚本会自动更新现有数据

## 使用方法

### 1. 执行数据库迁移

```bash
# 使用Python脚本（推荐）
python scripts/update_sync_type_enum.py

# 或使用SQL脚本
sqlite3 userdata/taifish_dev.db < sql/update_sync_type_enum_sqlite.sql
```

### 2. 验证更新结果

```sql
-- 检查sync_sessions表的sync_type值
SELECT DISTINCT sync_type FROM sync_sessions;

-- 检查sync_data表的sync_type值
SELECT DISTINCT sync_type FROM sync_data WHERE sync_type IS NOT NULL;
```

### 3. 在代码中使用新类型

```python
from app.constants import SyncType

# 创建手动单台同步
session = SyncSession(sync_type=SyncType.MANUAL_SINGLE.value)

# 创建手动批量同步
session = SyncSession(sync_type=SyncType.MANUAL_BATCH.value)

# 创建手动任务同步
session = SyncSession(sync_type=SyncType.MANUAL_TASK.value)

# 创建定时任务同步
session = SyncSession(sync_type=SyncType.SCHEDULED_TASK.value)
```

## 注意事项

1. **数据备份**: 执行迁移前请备份数据库
2. **测试环境**: 建议先在测试环境验证更新效果
3. **代码审查**: 确保所有相关代码都已更新
4. **文档更新**: 更新相关API文档和用户手册

## 影响范围

- ✅ 同步记录页面显示
- ✅ 同步类型筛选功能
- ✅ 批量同步操作
- ✅ 定时任务执行
- ✅ 单实例同步操作
- ✅ 数据库存储和查询

## 后续工作

1. 更新API文档中的同步类型说明
2. 更新用户手册中的功能说明
3. 监控生产环境中的同步操作
4. 收集用户反馈并优化

---

**更新时间**: 2024年12月
**版本**: v4.0
**负责人**: AI Assistant
