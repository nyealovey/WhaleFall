-- =============================================
-- SQL Server 监控用户权限设置脚本
-- 鲸落 - 数据同步管理平台
-- =============================================

-- 1. 创建监控用户登录账户
-- 注意：请将 'YourStrongPassword123!' 替换为强密码
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'monitor_user')
BEGIN
    CREATE LOGIN [monitor_user] WITH PASSWORD = 'YourStrongPassword123!';
    PRINT '监控用户登录账户创建成功';
END
ELSE
BEGIN
    PRINT '监控用户登录账户已存在';
END

-- 2. 授予服务器级权限
-- 连接权限
IF NOT EXISTS (SELECT * FROM sys.server_permissions WHERE grantee_principal_id = USER_ID('monitor_user') AND permission_name = 'CONNECT SQL')
BEGIN
    GRANT CONNECT SQL TO [monitor_user];
    PRINT '已授予连接权限';
END

-- 查看服务器级定义权限
IF NOT EXISTS (SELECT * FROM sys.server_permissions WHERE grantee_principal_id = USER_ID('monitor_user') AND permission_name = 'VIEW ANY DEFINITION')
BEGIN
    GRANT VIEW ANY DEFINITION TO [monitor_user];
    PRINT '已授予查看服务器级定义权限';
END

-- 注意：移除了VIEW SERVER STATE权限，因为代码中未使用

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
                    PRINT ''为新数据库 ' + @db_name + ' 自动创建监控用户'';
                END';
    
    EXEC sp_executesql @sql;
    
    -- 授予数据库级权限
    SET @sql = 'USE [' + @db_name + ']; 
                GRANT VIEW DEFINITION TO [monitor_user];
                PRINT ''为新数据库 ' + @db_name + ' 自动授予查看定义权限'';
                ';
    
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
    -- 为数据库创建用户
    SET @sql = 'USE [' + @db_name + ']; 
                IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = ''monitor_user'')
                BEGIN
                    CREATE USER [monitor_user] FOR LOGIN [monitor_user];
                    PRINT ''为数据库 ' + @db_name + ' 创建用户成功'';
                END';
    
    EXEC sp_executesql @sql;
    
    -- 授予数据库级权限
    SET @sql = 'USE [' + @db_name + ']; 
                GRANT VIEW DEFINITION TO [monitor_user];
                PRINT ''为数据库 ' + @db_name + ' 授予查看定义权限'';
                ';
    
    EXEC sp_executesql @sql;
    
    FETCH NEXT FROM db_cursor INTO @db_name;
END

CLOSE db_cursor;
DEALLOCATE db_cursor;

-- 4. 验证权限设置
PRINT '=============================================';
PRINT '权限设置完成，开始验证...';

-- 测试连接权限
SELECT '连接测试' AS 测试项目, @@VERSION AS 结果;

-- 测试服务器级权限
SELECT '服务器级权限测试' AS 测试项目, COUNT(*) AS 可访问的服务器主体数量 FROM sys.server_principals;

-- 测试数据库级权限
SELECT '数据库级权限测试' AS 测试项目, COUNT(*) AS 可访问的数据库数量 FROM sys.databases;

-- 测试权限查询
SELECT '权限查询测试' AS 测试项目, COUNT(*) AS 可访问的服务器权限数量 FROM sys.server_permissions;

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
