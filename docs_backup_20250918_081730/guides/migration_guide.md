# 数据库同步模型迁移指南

## 概述

本指南将帮助您从旧的同步数据模型迁移到新的优化同步模型。新模型提供更好的性能、更清晰的权限结构和更完善的变更追踪功能。

## 迁移前准备

### 1. 备份数据

```bash
# 备份现有数据库
pg_dump -h localhost -U username -d taifish_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 或使用SQLite
cp userdata/taifish_dev.db userdata/taifish_dev_backup_$(date +%Y%m%d_%H%M%S).db
```

### 2. 检查现有数据

```sql
-- 检查现有同步数据表
SELECT table_name FROM information_schema.tables
WHERE table_name LIKE '%sync%' OR table_name LIKE '%account%';

-- 检查数据量
SELECT COUNT(*) FROM sync_data;
SELECT COUNT(*) FROM accounts;
```

### 3. 停止相关服务

```bash
# 停止定时任务
pkill -f "python.*scheduler"

# 停止Web应用
pkill -f "python.*app.py"
```

## 迁移步骤

### 步骤1: 创建新表结构

#### PostgreSQL

```bash
# 执行迁移脚本
psql -h localhost -U username -d taifish_db -f sql/create_optimized_sync_tables.sql
```

#### SQLite

```bash
# 执行迁移脚本
sqlite3 userdata/taifish_dev.db < sql/create_optimized_sync_tables_sqlite.sql
```

### 步骤2: 数据迁移

创建数据迁移脚本：

```python
#!/usr/bin/env python3
"""
数据迁移脚本：从旧模型迁移到新模型
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.account_change_log import AccountChangeLog

def migrate_sync_data():
    """迁移同步数据"""
    app = create_app()

    with app.app_context():
        # 获取现有同步数据
        old_sync_data = db.session.execute("""
            SELECT instance_id, db_type, session_id, sync_time, status, message, error_message
            FROM sync_data
            ORDER BY sync_time DESC
        """).fetchall()

        print(f"找到 {len(old_sync_data)} 条同步记录")

        # 迁移到新表
        for record in old_sync_data:
            # 这里需要根据实际的数据结构进行映射
            # 由于新模型结构不同，可能需要重新同步数据
            pass

def migrate_account_data():
    """迁移账户数据"""
    app = create_app()

    with app.app_context():
        # 获取现有账户数据
        old_accounts = db.session.execute("""
            SELECT id, instance_id, username, db_type, created_at, updated_at
            FROM accounts
        """).fetchall()

        print(f"找到 {len(old_accounts)} 个账户")

        # 迁移到新表
        for account in old_accounts:
            new_account = CurrentAccountSyncData(
                instance_id=account.instance_id,
                db_type=account.db_type,
                username=account.username,
                last_sync_time=account.created_at or datetime.utcnow(),
                last_change_type="add",
                is_deleted=False
            )
            db.session.add(new_account)

        db.session.commit()
        print("账户数据迁移完成")

if __name__ == "__main__":
    migrate_account_data()
```

### 步骤3: 验证迁移结果

```sql
-- 检查新表数据
SELECT COUNT(*) FROM current_account_sync_data;
SELECT COUNT(*) FROM account_change_log;

-- 检查数据完整性
SELECT db_type, COUNT(*) as count
FROM current_account_sync_data
GROUP BY db_type;

-- 检查索引
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename IN ('current_account_sync_data', 'account_change_log');
```

### 步骤4: 更新应用配置

确保应用使用新的模型：

```python
# 在 app/__init__.py 中确保新路由已注册
from app.routes.instance_accounts import instance_accounts_bp
app.register_blueprint(instance_accounts_bp, url_prefix="/instance_accounts")
```

### 步骤5: 测试新功能

```bash
# 运行测试脚本
python test_optimized_sync_models.py

# 启动应用并测试UI
python app.py
```

## 权限数据映射

### MySQL权限映射

```python
# 旧模型 -> 新模型
old_permissions = {
    "global_privileges": ["SELECT", "INSERT"],
    "database_privileges": {"testdb": ["SELECT"]}
}

new_account = CurrentAccountSyncData(
    global_privileges=old_permissions["global_privileges"],
    database_privileges=old_permissions["database_privileges"],
    type_specific={}  # 其他特定字段
)
```

### PostgreSQL权限映射

```python
# 角色属性映射
role_attributes = []
if account.is_superuser:
    role_attributes.append("SUPERUSER")
if account.can_create_db:
    role_attributes.append("CREATEDB")
if account.can_create_role:
    role_attributes.append("CREATEROLE")

new_account = CurrentAccountSyncData(
    predefined_roles=account.predefined_roles or [],
    role_attributes=role_attributes,
    database_privileges_pg=account.database_privileges or {},
    tablespace_privileges=account.tablespace_privileges or []
)
```

### SQL Server权限映射

```python
new_account = CurrentAccountSyncData(
    server_roles=account.server_roles or [],
    server_permissions=account.server_permissions or [],
    database_roles=account.database_roles or {},
    database_permissions=account.database_permissions or {}
)
```

### Oracle权限映射

```python
new_account = CurrentAccountSyncData(
    oracle_roles=account.roles or [],
    system_privileges=account.system_privileges or [],
    tablespace_privileges_oracle=account.tablespace_privileges or []
    # 注意：移除了表空间配额字段
)
```

## 回滚计划

如果迁移过程中出现问题，可以按以下步骤回滚：

### 1. 停止新功能

```python
# 在 app/__init__.py 中注释掉新路由
# app.register_blueprint(instance_accounts_bp, url_prefix="/instance_accounts")
```

### 2. 恢复数据

```bash
# 恢复数据库备份
psql -h localhost -U username -d taifish_db < backup_20250114_120000.sql

# 或恢复SQLite
cp userdata/taifish_dev_backup_20250114_120000.db userdata/taifish_dev.db
```

### 3. 删除新表

```sql
-- 删除新表（谨慎操作）
DROP TABLE IF EXISTS account_change_log;
DROP TABLE IF EXISTS current_account_sync_data;
```

## 性能优化建议

### 1. 索引优化

```sql
-- 根据查询模式添加复合索引
CREATE INDEX idx_current_account_instance_dbtype_username
ON current_account_sync_data(instance_id, db_type, username);

CREATE INDEX idx_change_log_username_time
ON account_change_log(username, change_time DESC);
```

### 2. 数据清理

```sql
-- 定期清理旧的变更日志（保留最近30天）
DELETE FROM account_change_log
WHERE change_time < NOW() - INTERVAL '30 days';

-- 清理已删除的账户（可选）
DELETE FROM current_account_sync_data
WHERE is_deleted = true
AND deleted_time < NOW() - INTERVAL '90 days';
```

### 3. 查询优化

```python
# 使用索引优化的查询
accounts = CurrentAccountSyncData.query.filter_by(
    instance_id=instance_id,
    db_type=db_type,
    is_deleted=False
).order_by(CurrentAccountSyncData.last_sync_time.desc()).all()
```

## 监控和维护

### 1. 性能监控

```sql
-- 监控表大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE tablename IN ('current_account_sync_data', 'account_change_log');

-- 监控索引使用情况
SELECT
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname IN ('current_account_sync_data', 'account_change_log');
```

### 2. 数据一致性检查

```python
def check_data_consistency():
    """检查数据一致性"""
    app = create_app()

    with app.app_context():
        # 检查孤立的变更日志
        orphaned_logs = db.session.execute("""
            SELECT cl.id FROM account_change_log cl
            LEFT JOIN current_account_sync_data ca
            ON cl.instance_id = ca.instance_id
            AND cl.db_type = ca.db_type
            AND cl.username = ca.username
            WHERE ca.id IS NULL
        """).fetchall()

        if orphaned_logs:
            print(f"发现 {len(orphaned_logs)} 条孤立的变更日志")

        # 检查重复的账户记录
        duplicates = db.session.execute("""
            SELECT instance_id, db_type, username, COUNT(*)
            FROM current_account_sync_data
            GROUP BY instance_id, db_type, username
            HAVING COUNT(*) > 1
        """).fetchall()

        if duplicates:
            print(f"发现 {len(duplicates)} 组重复的账户记录")
```

## 常见问题

### Q1: 迁移后数据不完整怎么办？

A: 检查数据映射逻辑，确保所有字段都正确映射。可以重新运行同步任务来补充数据。

### Q2: 查询性能变慢了？

A: 检查索引是否正确创建，根据实际查询模式调整索引策略。

### Q3: UI显示异常？

A: 检查API接口是否正常，查看浏览器控制台错误信息。

### Q4: 权限变更检测不准确？

A: 检查权限数据格式，确保与数据库类型匹配。

## 联系支持

如果在迁移过程中遇到问题，请：

1. 查看应用日志文件
2. 运行诊断脚本
3. 联系技术支持团队

---

**作者**: AI Assistant
**更新时间**: 2025-01-14
**版本**: 4.0.0
