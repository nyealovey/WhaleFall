# SQL Server 密码策略禁用说明

## 概述

本文档说明了为什么在鲸落系统中禁用 SQL Server 监控用户的密码策略，以及如何配置。

## 背景

SQL Server 默认启用密码策略，要求密码满足以下条件：
- 至少包含大写字母
- 至少包含小写字母  
- 至少包含数字
- 至少包含特殊字符
- 密码长度至少8位
- 密码不能包含用户名
- 密码不能是常见弱密码

对于监控账户，这些策略可能会带来以下问题：
1. **密码复杂度要求过高** - 监控账户通常使用固定密码，复杂策略可能导致密码难以记忆
2. **密码过期问题** - 监控账户密码过期会导致系统无法正常工作
3. **维护成本高** - 需要定期更新密码，增加运维复杂度

## 解决方案

在 `sql/setup_sqlserver_monitor_user.sql` 脚本中，我们禁用了密码策略：

```sql
CREATE LOGIN [monitor_user] WITH PASSWORD = 'YourStrongPassword123!', 
    CHECK_POLICY = OFF, 
    CHECK_EXPIRATION = OFF;
```

### 参数说明

- `CHECK_POLICY = OFF` - 禁用 Windows 密码策略检查
- `CHECK_EXPIRATION = OFF` - 禁用密码过期检查

## 安全考虑

虽然禁用了密码策略，但我们仍然采取以下安全措施：

### 1. 强密码要求
- 使用复杂密码：`YourStrongPassword123!`
- 包含大小写字母、数字和特殊字符
- 密码长度超过8位

### 2. 最小权限原则
- 只授予监控所需的最小权限
- 不授予管理员权限
- 限制数据库访问范围

### 3. 网络安全
- 限制登录来源IP
- 使用加密连接
- 定期审查访问日志

### 4. 定期维护
- 定期更换密码
- 监控异常登录
- 审查权限设置

## 使用方法

### 1. 创建监控用户
```bash
sqlcmd -S server -U sa -P password -i sql/setup_sqlserver_monitor_user.sql
```

### 2. 验证设置
```sql
-- 检查密码策略设置
SELECT name, is_policy_checked, is_expiration_checked 
FROM sys.sql_logins 
WHERE name = 'monitor_user';
```

### 3. 手动更新密码策略（如果需要）
```sql
-- 禁用密码策略
ALTER LOGIN [monitor_user] WITH CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;

-- 启用密码策略（不推荐）
ALTER LOGIN [monitor_user] WITH CHECK_POLICY = ON, CHECK_EXPIRATION = ON;
```

## 注意事项

1. **生产环境** - 在生产环境中，建议使用更复杂的密码
2. **定期审查** - 定期检查监控账户的使用情况
3. **备份恢复** - 确保密码安全存储，避免丢失
4. **合规要求** - 某些行业可能有特殊的密码策略要求

## 相关文件

- `sql/setup_sqlserver_monitor_user.sql` - SQL Server 监控用户创建脚本
- `docs/database/DATABASE_PERMISSIONS_OVERVIEW.md` - 数据库权限概览
- `app/services/sync_adapters/sqlserver_sync_adapter.py` - SQL Server 同步适配器

## 更新历史

- 2025-01-22 - 初始版本，添加密码策略禁用说明
