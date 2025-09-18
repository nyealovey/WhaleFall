# 同步会话管理功能

## 概述

同步会话管理是泰摸鱼吧V4的新增核心功能，用于管理批量同步操作。该功能提供了统一的会话管理机制，支持定时任务同步和手动批量同步两种模式，并预留了未来扩展空间。

## 功能特性

### 1. 同步会话管理
- **会话创建**：为每次批量同步创建独立的会话记录
- **会话跟踪**：实时跟踪同步进度和状态
- **会话统计**：提供详细的同步统计信息
- **会话取消**：支持取消正在运行的同步会话

### 2. 实例记录管理
- **实例记录**：为每个数据库实例创建独立的同步记录
- **状态跟踪**：跟踪每个实例的同步状态（等待中、运行中、已完成、失败）
- **详细统计**：记录账户同步的详细统计信息
- **错误处理**：记录同步过程中的错误信息

### 3. 同步分类支持
- **账户同步**：`account` - 默认的账户同步分类
- **容量同步**：`capacity` - 为未来的数据库空间同步预留
- **配置同步**：`config` - 为未来的配置同步预留
- **其他同步**：`other` - 其他类型的同步操作

## 数据库架构

### 同步会话表 (sync_sessions)
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

### 同步实例记录表 (sync_instance_records)
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

## 核心组件

### 1. 数据模型
- **SyncSession**：同步会话模型
- **SyncInstanceRecord**：同步实例记录模型
- **SyncData**：更新后的同步数据模型（添加了session_id和sync_category字段）

### 2. 服务层
- **SyncSessionService**：同步会话管理服务
  - `create_session()`：创建同步会话
  - `add_instance_records()`：添加实例记录
  - `start_instance_sync()`：开始实例同步
  - `complete_instance_sync()`：完成实例同步
  - `fail_instance_sync()`：标记实例同步失败
  - `get_session_records()`：获取会话记录
  - `cancel_session()`：取消会话

### 3. 路由层
- **sync_sessions_bp**：同步会话管理蓝图
  - `GET /sync_sessions/`：同步会话管理页面
  - `GET /sync_sessions/api/sessions`：获取会话列表API
  - `GET /sync_sessions/api/sessions/<session_id>`：获取会话详情API
  - `POST /sync_sessions/api/sessions/<session_id>/cancel`：取消会话API
  - `GET /sync_sessions/api/statistics`：获取统计信息API

### 4. 前端界面
- **同步会话管理页面**：提供完整的会话管理界面
- **实时统计显示**：显示同步统计信息
- **会话详情查看**：查看会话的详细信息和实例记录
- **会话操作**：支持取消正在运行的会话

## 使用方式

### 1. 定时任务同步
定时任务会自动创建同步会话，记录所有同步操作：

```python
# 在 app/tasks.py 中的 sync_accounts() 函数
session = sync_session_service.create_session(
    sync_type='scheduled',
    sync_category='account',
    created_by=None  # 定时任务没有用户
)
```

### 2. 手动批量同步
用户手动触发的批量同步也会创建会话记录：

```python
# 在 app/routes/account_sync.py 中的 sync_all_accounts() 函数
session = sync_session_service.create_session(
    sync_type='manual_batch',
    sync_category='account',
    created_by=current_user.id
)
```

### 3. 查看同步会话
用户可以通过以下方式查看同步会话：
- 访问 `/sync_sessions/` 页面
- 通过主菜单的"数据库管理" > "同步会话管理"
- 查看实时统计和进度信息

## 向后兼容性

### 1. 保持现有功能
- 现有的 `SyncData` 表结构保持不变
- 现有的同步记录仍然可以正常显示
- 现有的API接口保持兼容

### 2. 增强功能
- 在 `SyncData` 表中添加了 `session_id` 和 `sync_category` 字段
- 新的同步操作会同时创建会话记录和传统的同步记录
- 提供了更详细的同步统计和跟踪功能

## 扩展性设计

### 1. 同步分类扩展
通过 `sync_category` 字段，可以轻松添加新的同步类型：
- 数据库空间同步
- 配置同步
- 权限同步
- 其他自定义同步

### 2. 会话管理扩展
会话管理架构支持：
- 多种同步类型
- 复杂的同步流程
- 异步同步操作
- 同步依赖管理

### 3. 统计和监控扩展
提供了丰富的统计信息：
- 实时进度跟踪
- 详细的错误记录
- 性能指标统计
- 历史数据分析

## 技术实现

### 1. 数据库设计
- 使用外键关联确保数据一致性
- 创建适当的索引优化查询性能
- 支持级联删除保持数据清洁

### 2. 服务层设计
- 使用服务层模式封装业务逻辑
- 提供统一的API接口
- 支持事务管理确保数据一致性

### 3. 前端设计
- 使用Bootstrap 5.3.2提供响应式界面
- 使用jQuery进行AJAX交互
- 提供实时更新和用户友好的操作界面

## 部署说明

### 1. 数据库迁移
需要执行以下SQL脚本：
- `sql/create_sync_sessions_tables.sql`：创建新的表结构
- `sql/update_sync_data_table.sql`：更新现有表结构

### 2. 代码部署
- 确保所有新的模型、服务、路由文件已部署
- 更新主应用的路由注册
- 更新前端模板文件

### 3. 配置检查
- 确保数据库连接正常
- 检查权限配置
- 验证定时任务配置

## 监控和维护

### 1. 日志记录
- 所有同步操作都有详细的日志记录
- 使用结构化日志便于分析和监控
- 支持错误追踪和问题诊断

### 2. 性能监控
- 监控同步会话的执行时间
- 跟踪数据库查询性能
- 分析同步成功率

### 3. 数据清理
- 定期清理过期的会话记录
- 归档历史同步数据
- 优化数据库性能

## 未来规划

### 1. 短期目标
- 完善错误处理和恢复机制
- 优化用户界面和用户体验
- 添加更多的统计和监控功能

### 2. 中期目标
- 实现数据库空间同步功能
- 添加配置同步功能
- 支持更复杂的同步流程

### 3. 长期目标
- 实现分布式同步
- 支持实时同步
- 提供高级分析和报告功能
