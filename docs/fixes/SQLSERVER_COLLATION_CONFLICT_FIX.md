# SQL Server 排序规则冲突修复

## 🔍 问题描述

在 SQL Server 权限同步过程中出现排序规则冲突错误：

```
Cannot resolve collation conflict between "Chinese_PRC_CI_AS" and "Latin1_General_100_CI_AS_KS_WS_SC" in UNION ALL operator occurring in SELECT statement column 7.
```

## 🔍 问题原因

在 UNION ALL 操作中，不同数据库的字符串字段使用了不同的排序规则：
- 某些数据库使用 `Chinese_PRC_CI_AS` 排序规则
- 某些数据库使用 `Latin1_General_100_CI_AS_KS_WS_SC` 排序规则

当这些字段在 UNION ALL 中合并时，SQL Server 无法自动解决排序规则冲突。

## 🔧 修复方案

### 1. 统一排序规则

为所有字符串字段添加统一的排序规则 `SQL_Latin1_General_CP1_CI_AS`：

```sql
-- 修复前
SELECT '{db}' AS db_name,
       permission_name,
       grantee_principal_id,
       major_id,
       minor_id,
       CASE 
           WHEN major_id = 0 THEN 'DATABASE'
           WHEN major_id > 0 AND minor_id = 0 THEN 'SCHEMA'
           WHEN major_id > 0 AND minor_id > 0 THEN 'OBJECT'
       END AS permission_scope,
       CASE 
           WHEN major_id = 0 THEN 'DATABASE'
           WHEN major_id > 0 AND minor_id = 0 THEN 
               (SELECT name FROM {quoted_db}.sys.schemas WHERE schema_id = major_id)
           WHEN major_id > 0 AND minor_id > 0 THEN 
               (SELECT name FROM {quoted_db}.sys.objects WHERE object_id = major_id)
       END AS object_name
FROM {quoted_db}.sys.database_permissions WHERE state = 'G'

-- 修复后
SELECT '{db}' AS db_name,
       permission_name COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_name,
       grantee_principal_id,
       major_id,
       minor_id,
       CASE 
           WHEN major_id = 0 THEN 'DATABASE'
           WHEN major_id > 0 AND minor_id = 0 THEN 'SCHEMA'
           WHEN major_id > 0 AND minor_id > 0 THEN 'OBJECT'
       END COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_scope,
       CASE 
           WHEN major_id = 0 THEN 'DATABASE'
           WHEN major_id > 0 AND minor_id = 0 THEN 
               (SELECT name FROM {quoted_db}.sys.schemas WHERE schema_id = major_id)
           WHEN major_id > 0 AND minor_id > 0 THEN 
               (SELECT name FROM {quoted_db}.sys.objects WHERE object_id = major_id)
       END COLLATE SQL_Latin1_General_CP1_CI_AS AS object_name
FROM {quoted_db}.sys.database_permissions WHERE state = 'G'
```

### 2. 修复的字段

- `permission_name` - 权限名称
- `permission_scope` - 权限作用范围
- `object_name` - 对象名称

### 3. 排序规则选择

选择 `SQL_Latin1_General_CP1_CI_AS` 的原因：
- 这是 SQL Server 的默认排序规则
- 兼容性最好
- 支持大多数字符集
- 在跨数据库查询中稳定性最好

## 🚀 实施步骤

### 第一步：修改权限查询SQL
1. 为所有字符串字段添加 `COLLATE SQL_Latin1_General_CP1_CI_AS`
2. 确保 UNION ALL 操作中所有字段排序规则一致

### 第二步：测试验证
1. 测试跨数据库权限查询
2. 验证排序规则冲突是否解决
3. 确保权限数据正确获取

### 第三步：部署更新
1. 部署修复后的代码
2. 监控错误日志
3. 确认问题解决

## 📊 预期效果

修复后的效果：
- ✅ 消除排序规则冲突错误
- ✅ 跨数据库查询正常工作
- ✅ 权限数据正确获取
- ✅ 系统稳定性提升

## 🔗 相关文件

- `app/services/sync_adapters/sqlserver_sync_adapter.py` - 主要修复文件
- `docs/fixes/SQLSERVER_COLLATION_CONFLICT_FIX.md` - 本文档

## 📝 更新历史

- 2025-01-22 - 初始分析，识别排序规则冲突问题
- 2025-01-22 - 实施修复，统一排序规则
