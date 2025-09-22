# PostgreSQL 枚举类型不存在错误修复

## 🔍 问题描述

定时任务执行时出现 PostgreSQL 枚举类型不存在的错误：

```
(psycopg.errors.UndefinedObject) type "sync_record_category_enum" does not exist
```

## 🔍 问题原因

模型定义中使用了 PostgreSQL 枚举类型，但数据库初始化脚本中使用的是 CHECK 约束：

### 模型定义（错误）：
```python
sync_category = db.Column(
    db.Enum("account", "capacity", "config", "other", name="sync_record_category_enum"),
    nullable=False,
    default="account",
)
```

### 数据库脚本（正确）：
```sql
sync_category VARCHAR(20) NOT NULL DEFAULT 'account' CHECK (sync_category IN ('account', 'capacity', 'config', 'other'))
```

## 🔧 修复方案

### 1. 修改模型定义

将枚举类型改为字符串类型，与数据库脚本保持一致：

```python
# 修复前
sync_category = db.Column(
    db.Enum("account", "capacity", "config", "other", name="sync_record_category_enum"),
    nullable=False,
    default="account",
)

# 修复后
sync_category = db.Column(
    db.String(20),
    nullable=False,
    default="account",
)
```

### 2. 修复的文件

- `app/models/sync_instance_record.py` - 同步实例记录模型
- `app/models/sync_session.py` - 同步会话模型

### 3. 修复的字段

#### SyncInstanceRecord 模型：
- `sync_category` - 同步分类
- `status` - 状态

#### SyncSession 模型：
- `sync_type` - 同步类型
- `sync_category` - 同步分类
- `status` - 状态

## 🚀 实施步骤

### 第一步：修改模型定义
1. 将所有 `db.Enum` 改为 `db.String`
2. 移除枚举类型名称参数
3. 保持字段长度和约束

### 第二步：测试验证
1. 测试模型创建和查询
2. 验证数据插入和更新
3. 确保与数据库脚本一致

### 第三步：部署更新
1. 部署修复后的代码
2. 监控定时任务执行
3. 确认错误解决

## 📊 预期效果

修复后的效果：
- ✅ 消除枚举类型不存在错误
- ✅ 定时任务正常执行
- ✅ 模型与数据库脚本一致
- ✅ 数据约束仍然有效（通过 CHECK 约束）

## 🔗 相关文件

- `app/models/sync_instance_record.py` - 同步实例记录模型
- `app/models/sync_session.py` - 同步会话模型
- `sql/init_postgresql.sql` - 数据库初始化脚本

## 📝 更新历史

- 2025-01-22 - 初始分析，识别枚举类型不存在问题
- 2025-01-22 - 实施修复，将枚举类型改为字符串类型
