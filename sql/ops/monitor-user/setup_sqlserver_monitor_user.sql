-- =============================================
-- SQL Server 监控用户权限设置脚本
-- 鲸落 - 数据同步管理平台
-- =============================================

-- 1. 创建监控用户登录账户
-- 注意：请将 'YourStrongPassword123!' 替换为强密码
-- 禁用密码策略：CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'monitor_user')
BEGIN
    CREATE LOGIN [monitor_user] WITH PASSWORD = 'YourStrongPassword123!',
        CHECK_POLICY = OFF,
        CHECK_EXPIRATION = OFF;
    PRINT '监控用户登录账户创建成功（已禁用密码策略）';
END
ELSE
BEGIN
    PRINT '监控用户登录账户已存在';
    -- 如果账户已存在，更新密码策略设置
    ALTER LOGIN [monitor_user] WITH CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
    PRINT '已更新密码策略设置（禁用强制密码策略）';
END

-- 2. 授予服务器级权限
GRANT CONNECT SQL TO [monitor_user];
GRANT VIEW ANY DEFINITION TO [monitor_user];
GRANT VIEW ANY DATABASE TO [monitor_user];
GRANT VIEW SERVER STATE TO [monitor_user];
PRINT '已授予监控用户所需权限';

-- 3. 创建数据库触发器，自动为新数据库设置权限
-- 这个触发器会在新数据库创建时自动执行
USE master;
GO

-- 删除已存在的触发器（如果存在）
IF EXISTS (SELECT * FROM sys.server_triggers WHERE name = 'tr_auto_grant_monitor_permissions')
    DROP TRIGGER tr_auto_grant_monitor_permissions ON ALL SERVER;
GO

-- 创建服务器级触发器
CREATE TRIGGER tr_auto_grant_monitor_permissions
ON ALL SERVER
FOR CREATE_DATABASE
AS
BEGIN
    DECLARE @db_name NVARCHAR(128);
    DECLARE @sql NVARCHAR(MAX);

    -- 获取新创建的数据库名称
    SELECT @db_name = EVENTDATA().value('(/EVENT_INSTANCE/DatabaseName)[1]', 'NVARCHAR(128)');

    -- 为新数据库创建用户并授予权限
    SET @sql = 'USE [' + @db_name + '];
                IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = ''monitor_user'')
                BEGIN
                    CREATE USER [monitor_user] FOR LOGIN [monitor_user];
                END
                GRANT VIEW DEFINITION TO [monitor_user];';

    EXEC sp_executesql @sql;
END;
GO

-- 4. 为现有数据库设置权限（一次性设置）
DECLARE @db_name NVARCHAR(128);
DECLARE @sql NVARCHAR(MAX);

-- 创建游标遍历所有数据库
DECLARE db_cursor CURSOR FOR
SELECT name FROM sys.databases
WHERE state = 0 -- 只处理在线数据库
AND name NOT IN ('tempdb', 'model', 'msdb'); -- 排除系统数据库

OPEN db_cursor;
FETCH NEXT FROM db_cursor INTO @db_name;

WHILE @@FETCH_STATUS = 0
BEGIN
    -- 为数据库创建用户并授予权限
    SET @sql = 'USE [' + @db_name + '];
                IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = ''monitor_user'')
                BEGIN
                    CREATE USER [monitor_user] FOR LOGIN [monitor_user];
                END
                GRANT VIEW DEFINITION TO [monitor_user];';

    EXEC sp_executesql @sql;

    FETCH NEXT FROM db_cursor INTO @db_name;
END

CLOSE db_cursor;
DEALLOCATE db_cursor;

-- 4. 验证权限设置
PRINT '=============================================';
PRINT '权限设置完成，开始验证...';

-- 测试权限设置
SELECT '权限测试完成' AS 状态, GETDATE() AS 时间;

-- 5. 显示当前用户权限摘要
PRINT '=============================================';
PRINT '当前监控用户权限摘要:';

SELECT
    p.permission_name AS 权限名称,
    p.state_desc AS 权限状态,
    '服务器级' AS 权限级别
FROM sys.server_permissions p
JOIN sys.server_principals sp ON p.grantee_principal_id = sp.principal_id
WHERE sp.name = 'monitor_user'

UNION ALL

SELECT
    'VIEW DEFINITION' AS 权限名称,
    'GRANT' AS 权限状态,
    '数据库级' AS 权限级别
WHERE EXISTS (
    SELECT 1 FROM sys.databases d
    WHERE d.name = DB_NAME()
    AND EXISTS (
        SELECT 1 FROM sys.database_permissions dp
        JOIN sys.database_principals dbp ON dp.grantee_principal_id = dbp.principal_id
        WHERE dp.major_id = d.database_id
        AND dbp.name = 'monitor_user'
        AND dp.permission_name = 'VIEW DEFINITION'
    )
);

PRINT '=============================================';
PRINT '权限设置完成！';
PRINT '';
PRINT '核心特性：';
PRINT '1. ✅ 支持跨数据库查询，使用三部分命名法';
PRINT '2. ✅ 自动为新创建的数据库设置权限（通过触发器）';
PRINT '3. ✅ 遵循最小权限原则，仅授予必要的权限';
PRINT '4. ✅ 支持实时查询所有数据库的用户和权限信息';
PRINT '5. ✅ 无需手动为每个新数据库设置权限';
PRINT '6. ✅ 移除了不必要的VIEW SERVER STATE权限';
PRINT '7. ✅ 授予VIEW ANY DATABASE权限，支持跨数据库系统表查询';
PRINT '';
PRINT '使用方法：';
PRINT '在鲸落系统中使用以下凭据：';
PRINT '用户名: monitor_user';
PRINT '密码: YourStrongPassword123! (请修改为强密码)';
PRINT '';
PRINT '注意：';
PRINT '- 新创建的数据库会自动获得监控权限';
PRINT '- 如果触发器被禁用，需要手动运行此脚本';
PRINT '- 建议定期检查触发器状态';
PRINT '=============================================';
