# 同步会话管理数据库架构

## 概述

本文档描述了鲸落V4中同步会话管理功能的数据库架构设计，包括表结构、关系、索引和约束。

## 表结构

### 1. 同步会话表 (sync_sessions)

#### 表定义
```sql
CREATE TABLE sync_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(36) UNIQUE NOT NULL,
    sync_type ENUM('scheduled', 'manual_batch') NOT NULL,
    sync_category ENUM('account', 'capacity', 'config', 'other') NOT NULL DEFAULT 'account',
    status ENUM('running', 'completed', 'failed', 'cancelled') NOT NULL DEFAULT 'running',
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    total_instances INTEGER DEFAULT 0,
    successful_instances INTEGER DEFAULT 0,
    failed_instances INTEGER DEFAULT 0,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 字段说明
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY | 主键，自增 |
| session_id | VARCHAR(36) | UNIQUE NOT NULL | 会话唯一标识符（UUID） |
| sync_type | ENUM | NOT NULL | 同步类型：scheduled=定时任务，manual_batch=手动批量 |
| sync_category | ENUM | NOT NULL DEFAULT 'account' | 同步分类：account=账户，capacity=容量，config=配置，other=其他 |
| status | ENUM | NOT NULL DEFAULT 'running' | 会话状态：running=运行中，completed=已完成，failed=失败，cancelled=已取消 |
| started_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 开始时间 |
| completed_at | DATETIME | NULL | 完成时间 |
| total_instances | INTEGER | DEFAULT 0 | 总实例数 |
| successful_instances | INTEGER | DEFAULT 0 | 成功实例数 |
| failed_instances | INTEGER | DEFAULT 0 | 失败实例数 |
| created_by | INTEGER | NULL | 创建用户ID |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

### 2. 同步实例记录表 (sync_instance_records)

#### 表定义
```sql
CREATE TABLE sync_instance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(36) NOT NULL,
    instance_id INTEGER NOT NULL,
    instance_name VARCHAR(255),
    sync_category ENUM('account', 'capacity', 'config', 'other') NOT NULL DEFAULT 'account',
    status ENUM('pending', 'running', 'completed', 'failed') NOT NULL DEFAULT 'pending',
    started_at DATETIME,
    completed_at DATETIME,
    accounts_synced INTEGER DEFAULT 0,
    accounts_created INTEGER DEFAULT 0,
    accounts_updated INTEGER DEFAULT 0,
    accounts_deleted INTEGER DEFAULT 0,
    error_message TEXT,
    sync_details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sync_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE
);
```

#### 字段说明
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY | 主键，自增 |
| session_id | VARCHAR(36) | NOT NULL | 关联的同步会话ID |
| instance_id | INTEGER | NOT NULL | 数据库实例ID |
| instance_name | VARCHAR(255) | NULL | 实例名称（冗余字段，便于查询） |
| sync_category | ENUM | NOT NULL DEFAULT 'account' | 同步分类 |
| status | ENUM | NOT NULL DEFAULT 'pending' | 实例同步状态：pending=等待中，running=运行中，completed=已完成，failed=失败 |
| started_at | DATETIME | NULL | 开始时间 |
| completed_at | DATETIME | NULL | 完成时间 |
| accounts_synced | INTEGER | DEFAULT 0 | 同步的账户总数 |
| accounts_created | INTEGER | DEFAULT 0 | 新增的账户数量 |
| accounts_updated | INTEGER | DEFAULT 0 | 更新的账户数量 |
| accounts_deleted | INTEGER | DEFAULT 0 | 删除的账户数量 |
| error_message | TEXT | NULL | 错误信息 |
| sync_details | JSON | NULL | 同步详情（JSON格式） |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### 3. 更新后的同步数据表 (sync_data)

#### 新增字段
```sql
ALTER TABLE sync_data ADD COLUMN session_id VARCHAR(36);
ALTER TABLE sync_data ADD COLUMN sync_category VARCHAR(20);
```

#### 字段说明
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| session_id | VARCHAR(36) | NULL | 关联的同步会话ID |
| sync_category | VARCHAR(20) | NULL | 同步分类 |

## 索引设计

### 1. 同步会话表索引
```sql
-- 主键索引（自动创建）
CREATE INDEX idx_sync_sessions_session_id ON sync_sessions(session_id);
CREATE INDEX idx_sync_sessions_sync_type ON sync_sessions(sync_type);
CREATE INDEX idx_sync_sessions_sync_category ON sync_sessions(sync_category);
CREATE INDEX idx_sync_sessions_status ON sync_sessions(status);
CREATE INDEX idx_sync_sessions_created_at ON sync_sessions(created_at);
```

### 2. 同步实例记录表索引
```sql
-- 主键索引（自动创建）
CREATE INDEX idx_sync_instance_records_session_id ON sync_instance_records(session_id);
CREATE INDEX idx_sync_instance_records_instance_id ON sync_instance_records(instance_id);
CREATE INDEX idx_sync_instance_records_sync_category ON sync_instance_records(sync_category);
CREATE INDEX idx_sync_instance_records_status ON sync_instance_records(status);
CREATE INDEX idx_sync_instance_records_created_at ON sync_instance_records(created_at);
```

### 3. 同步数据表索引
```sql
-- 新增字段索引
CREATE INDEX idx_sync_data_session_id ON sync_data(session_id);
CREATE INDEX idx_sync_data_sync_category ON sync_data(sync_category);
```

## 外键关系

### 1. 同步会话表
- 无外键约束（独立表）

### 2. 同步实例记录表
- `session_id` → `sync_sessions.session_id` (CASCADE DELETE)
- `instance_id` → `instances.id` (CASCADE DELETE)

### 3. 同步数据表
- `instance_id` → `instances.id` (现有关系)
- `task_id` → `tasks.id` (现有关系)
- `session_id` → `sync_sessions.session_id` (软关联，无外键约束)

## 数据完整性约束

### 1. 检查约束
```sql
-- 同步会话表
ALTER TABLE sync_sessions ADD CONSTRAINT chk_sync_sessions_status
CHECK (status IN ('running', 'completed', 'failed', 'cancelled'));

ALTER TABLE sync_sessions ADD CONSTRAINT chk_sync_sessions_sync_type
CHECK (sync_type IN ('scheduled', 'manual_batch'));

ALTER TABLE sync_sessions ADD CONSTRAINT chk_sync_sessions_sync_category
CHECK (sync_category IN ('account', 'capacity', 'config', 'other'));

-- 同步实例记录表
ALTER TABLE sync_instance_records ADD CONSTRAINT chk_sync_instance_records_status
CHECK (status IN ('pending', 'running', 'completed', 'failed'));

ALTER TABLE sync_instance_records ADD CONSTRAINT chk_sync_instance_records_sync_category
CHECK (sync_category IN ('account', 'capacity', 'config', 'other'));
```

### 2. 非空约束
- `sync_sessions.session_id`：NOT NULL
- `sync_sessions.sync_type`：NOT NULL
- `sync_sessions.sync_category`：NOT NULL
- `sync_sessions.status`：NOT NULL
- `sync_sessions.started_at`：NOT NULL
- `sync_instance_records.session_id`：NOT NULL
- `sync_instance_records.instance_id`：NOT NULL
- `sync_instance_records.sync_category`：NOT NULL
- `sync_instance_records.status`：NOT NULL

## 数据关系图

```
sync_sessions (1) ←→ (N) sync_instance_records
     ↓
sync_data (软关联)
     ↓
instances (1) ←→ (N) sync_instance_records
```

## 查询优化建议

### 1. 常用查询模式
```sql
-- 获取会话及其所有实例记录
SELECT s.*, r.*
FROM sync_sessions s
LEFT JOIN sync_instance_records r ON s.session_id = r.session_id
WHERE s.session_id = ?;

-- 获取最近的会话列表
SELECT * FROM sync_sessions
ORDER BY created_at DESC
LIMIT ?;

-- 获取特定类型的会话
SELECT * FROM sync_sessions
WHERE sync_type = ? AND sync_category = ?
ORDER BY created_at DESC;

-- 获取会话统计信息
SELECT
    sync_type,
    sync_category,
    status,
    COUNT(*) as count
FROM sync_sessions
GROUP BY sync_type, sync_category, status;
```

### 2. 性能优化
- 使用复合索引优化多条件查询
- 定期清理过期的会话记录
- 使用分页查询避免大量数据加载
- 考虑使用视图简化复杂查询

## 数据迁移策略

### 1. 创建新表
```sql
-- 执行 create_sync_sessions_tables.sql
-- 创建 sync_sessions 和 sync_instance_records 表
```

### 2. 更新现有表
```sql
-- 执行 update_sync_data_table.sql
-- 为 sync_data 表添加新字段
```

### 3. 数据迁移
- 现有数据无需迁移
- 新功能从零开始记录
- 保持向后兼容性

## 维护建议

### 1. 定期清理
```sql
-- 清理30天前的已完成会话
DELETE FROM sync_sessions
WHERE status IN ('completed', 'failed', 'cancelled')
AND completed_at < DATE('now', '-30 days');

-- 清理相关的实例记录（级联删除）
-- 注意：需要先清理 sync_instance_records，再清理 sync_sessions
```

### 2. 性能监控
- 监控表大小和增长趋势
- 检查索引使用情况
- 分析查询性能
- 优化慢查询

### 3. 数据备份
- 定期备份关键表
- 考虑数据归档策略
- 测试恢复流程

## 扩展性考虑

### 1. 水平扩展
- 考虑按时间分表
- 使用读写分离
- 实现数据分片

### 2. 功能扩展
- 预留字段支持新功能
- 灵活的JSON字段存储
- 可扩展的枚举值

### 3. 性能扩展
- 添加更多索引
- 使用缓存层
- 实现异步处理
