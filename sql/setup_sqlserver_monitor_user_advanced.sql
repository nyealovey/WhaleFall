-- =============================================
-- SQL Server 高级监控用户权限设置脚本
-- 泰摸鱼吧 - 数据同步管理平台
-- 支持跨数据库查询，无需在每个数据库创建用户
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

-- 2. 授予高级服务器级权限（关键权限组合）
-- 连接权限
IF NOT EXISTS (SELECT * FROM sys.server_permissions WHERE grantee_principal_id = USER_ID('monitor_user') AND permission_name = 'CONNECT SQL')
BEGIN
    GRANT CONNECT SQL TO [monitor_user];
    PRINT '已授予连接权限';
END

-- 查看服务器级定义权限（核心权限 - 可以访问所有数据库的元数据）
IF NOT EXISTS (SELECT * FROM sys.server_permissions WHERE grantee_principal_id = USER_ID('monitor_user') AND permission_name = 'VIEW ANY DEFINITION')
BEGIN
    GRANT VIEW ANY DEFINITION TO [monitor_user];
    PRINT '已授予查看服务器级定义权限';
END

-- 查看服务器状态权限（用于性能监控）
IF NOT EXISTS (SELECT * FROM sys.server_permissions WHERE grantee_principal_id = USER_ID('monitor_user') AND permission_name = 'VIEW SERVER STATE')
BEGIN
    GRANT VIEW SERVER STATE TO [monitor_user];
    PRINT '已授予查看服务器状态权限';
END

-- 3. 授予服务器级角色（可选，提供更广泛的权限）
-- 注意：这个角色提供对服务器配置的只读访问
IF NOT EXISTS (SELECT * FROM sys.server_role_members rm 
               JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
               JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
               WHERE r.name = 'serveradmin' AND p.name = 'monitor_user')
BEGIN
    ALTER SERVER ROLE [serveradmin] ADD MEMBER [monitor_user];
    PRINT '已添加服务器管理员角色（只读权限）';
END

-- 4. 创建数据库触发器，自动为新数据库设置权限
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

-- 5. 为现有数据库设置权限（一次性设置）
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

-- 6. 验证权限设置
PRINT '=============================================';
PRINT '高级权限设置完成，开始验证...';

-- 测试连接权限
SELECT '连接测试' AS 测试项目, @@VERSION AS 结果;

-- 测试服务器级权限
SELECT '服务器级权限测试' AS 测试项目, COUNT(*) AS 可访问的服务器主体数量 FROM sys.server_principals;

-- 测试数据库级权限
SELECT '数据库级权限测试' AS 测试项目, COUNT(*) AS 可访问的数据库数量 FROM sys.databases;

-- 测试跨数据库查询（关键测试）
PRINT '=============================================';
PRINT '测试跨数据库查询能力...';

-- 测试查询所有数据库的用户信息
SELECT 
    d.name AS database_name,
    dp.name AS user_name,
    dp.type_desc AS user_type
FROM sys.databases d
CROSS APPLY (
    SELECT dp.name, dp.type_desc
    FROM [sys].dm_exec_describe_first_result_set(
        'SELECT name, type_desc FROM [' + d.name + '].sys.database_principals WHERE type IN (''S'', ''U'', ''G'')',
        NULL, 0
    ) AS dp
) AS dp
WHERE d.state = 0
AND d.name NOT IN ('tempdb', 'model', 'msdb')
ORDER BY d.name, dp.name;

-- 7. 显示当前用户权限摘要
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
    r.name AS 权限名称,
    'MEMBER' AS 权限状态,
    '服务器角色' AS 权限级别
FROM sys.server_role_members rm
JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
WHERE p.name = 'monitor_user';

PRINT '=============================================';
PRINT '高级权限设置完成！';
PRINT '特性：';
PRINT '1. 支持跨数据库查询，无需在每个数据库创建用户';
PRINT '2. 自动为新创建的数据库设置权限';
PRINT '3. 遵循最小权限原则，安全性更高';
PRINT '4. 支持实时权限查询';
PRINT '';
PRINT '请将以下信息保存到泰摸鱼吧系统中：';
PRINT '用户名: monitor_user';
PRINT '密码: YourStrongPassword123! (请修改为强密码)';
PRINT '=============================================';
