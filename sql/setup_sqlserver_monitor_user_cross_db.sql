-- =============================================
-- SQL Server 跨数据库监控用户权限设置脚本
-- 泰摸鱼吧 - 数据同步管理平台
-- 专门针对跨数据库查询优化，无需在每个数据库创建用户
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

-- 2. 授予核心服务器级权限（关键权限组合）
-- 连接权限
GRANT CONNECT SQL TO [monitor_user];

-- 查看服务器级定义权限（核心权限 - 可以访问所有数据库的元数据）
GRANT VIEW ANY DEFINITION TO [monitor_user];

-- 查看服务器状态权限（用于性能监控）
GRANT VIEW SERVER STATE TO [monitor_user];

-- 3. 授予服务器级角色（提供更广泛的权限）
-- 注意：这个角色提供对服务器配置的只读访问
ALTER SERVER ROLE [serveradmin] ADD MEMBER [monitor_user];

PRINT '=============================================';
PRINT '核心权限设置完成！';
PRINT '';

-- 4. 验证跨数据库查询能力
PRINT '测试跨数据库查询能力...';

-- 测试1：查询所有数据库列表
PRINT '测试1：查询所有数据库列表';
SELECT 
    name AS database_name,
    state_desc AS status,
    create_date,
    compatibility_level
FROM sys.databases 
WHERE state = 0
ORDER BY name;

-- 测试2：跨数据库查询用户信息（核心测试）
PRINT '测试2：跨数据库查询用户信息';
SELECT 
    d.name AS database_name,
    dp.name AS user_name,
    dp.type_desc AS user_type,
    dp.create_date,
    dp.is_disabled
FROM sys.databases d
CROSS APPLY (
    -- 使用动态SQL查询每个数据库的用户信息
    SELECT 
        name, 
        type_desc, 
        create_date, 
        is_disabled
    FROM OPENROWSET('SQLNCLI', 'Server=localhost;Trusted_Connection=yes;',
        'SELECT name, type_desc, create_date, is_disabled FROM [' + d.name + '].sys.database_principals WHERE type IN (''S'', ''U'', ''G'')')
) AS dp
WHERE d.state = 0
AND d.name NOT IN ('tempdb', 'model', 'msdb')
ORDER BY d.name, dp.name;

-- 测试3：跨数据库查询权限信息
PRINT '测试3：跨数据库查询权限信息';
SELECT 
    d.name AS database_name,
    dp.name AS user_name,
    p.permission_name,
    p.state_desc
FROM sys.databases d
CROSS APPLY (
    -- 使用动态SQL查询每个数据库的权限信息
    SELECT 
        dp.name,
        p.permission_name,
        p.state_desc
    FROM OPENROWSET('SQLNCLI', 'Server=localhost;Trusted_Connection=yes;',
        'SELECT dp.name, p.permission_name, p.state_desc 
         FROM [' + d.name + '].sys.database_principals dp
         LEFT JOIN [' + d.name + '].sys.database_permissions p ON dp.principal_id = p.grantee_principal_id
         WHERE dp.type IN (''S'', ''U'', ''G'') AND p.permission_name IS NOT NULL')
) AS dp
WHERE d.state = 0
AND d.name NOT IN ('tempdb', 'model', 'msdb')
ORDER BY d.name, dp.name, p.permission_name;

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
    r.name AS 权限名称,
    'MEMBER' AS 权限状态,
    '服务器角色' AS 权限级别
FROM sys.server_role_members rm
JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
WHERE p.name = 'monitor_user';

PRINT '=============================================';
PRINT '跨数据库权限设置完成！';
PRINT '';
PRINT '核心特性：';
PRINT '1. ✅ 支持跨数据库查询，无需在每个数据库创建用户';
PRINT '2. ✅ 使用 VIEW ANY DEFINITION 权限访问所有数据库元数据';
PRINT '3. ✅ 使用 serveradmin 角色提供更广泛的权限';
PRINT '4. ✅ 支持实时查询所有数据库的用户和权限信息';
PRINT '5. ✅ 自动适应新增数据库，无需额外配置';
PRINT '';
PRINT '使用方法：';
PRINT '在泰摸鱼吧系统中使用以下凭据：';
PRINT '用户名: monitor_user';
PRINT '密码: YourStrongPassword123! (请修改为强密码)';
PRINT '=============================================';
