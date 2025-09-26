-- =============================================
-- MySQL 监控用户权限设置脚本
-- 鲸落 - 数据同步管理平台
-- =============================================

-- 1. 创建监控用户
-- 注意：请将 'YourStrongPassword123!' 替换为强密码
-- 注意：请将 '%' 替换为具体的IP地址或IP段，如 '192.168.1.%'

CREATE USER IF NOT EXISTS 'monitor_user'@'%' IDENTIFIED BY 'YourStrongPassword123!';

-- 2. 授予连接权限
GRANT USAGE ON *.* TO 'monitor_user'@'%';

-- 3. 授予SHOW DATABASES权限（用于查看所有数据库）
GRANT SHOW DATABASES ON *.* TO 'monitor_user'@'%';

-- 4. 授予mysql.user表查询权限（最低权限）
GRANT SELECT ON mysql.user TO 'monitor_user'@'%';

-- 5. 授予information_schema数据库查询权限（用于数据库大小监控）
GRANT SELECT ON information_schema.* TO 'monitor_user'@'%';

-- 6. 授予performance_schema数据库查询权限（用于性能监控）
GRANT SELECT ON performance_schema.* TO 'monitor_user'@'%';

-- 7. 授予mysql数据库查询权限（用于系统信息）
GRANT SELECT ON mysql.* TO 'monitor_user'@'%';

-- 8. 授予sys数据库查询权限（用于系统信息）
GRANT SELECT ON sys.* TO 'monitor_user'@'%';

-- 9. 刷新权限
FLUSH PRIVILEGES;

-- 10. 验证权限设置
SELECT 'MySQL 监控用户权限设置完成' AS 状态;

-- 显示当前用户权限
SHOW GRANTS FOR 'monitor_user'@'%';

-- 测试权限
SELECT '连接测试' AS 测试项目, @@VERSION AS 结果;
SELECT 'SHOW DATABASES测试' AS 测试项目, '请手动执行 SHOW DATABASES; 命令' AS 说明;
SELECT 'mysql.user表测试' AS 测试项目, COUNT(*) AS 可访问的用户数量 FROM mysql.user;
SELECT 'information_schema测试' AS 测试项目, COUNT(*) AS 可访问的数据库数量 FROM information_schema.SCHEMATA;
SELECT 'performance_schema测试' AS 测试项目, COUNT(*) AS 可访问的表数量 FROM performance_schema.tables LIMIT 1;
SELECT 'mysql数据库测试' AS 测试项目, COUNT(*) AS 可访问的表数量 FROM mysql.tables LIMIT 1;
SELECT 'sys数据库测试' AS 测试项目, COUNT(*) AS 可访问的表数量 FROM sys.tables LIMIT 1;

-- 显示权限摘要
SELECT 
    'SHOW DATABASES' AS 权限,
    '查看所有数据库列表' AS 用途
UNION ALL
SELECT 
    'mysql.user' AS 权限,
    '用户信息查询' AS 用途
UNION ALL
SELECT 
    'information_schema.*' AS 权限,
    '数据库大小监控' AS 用途
UNION ALL
SELECT 
    'performance_schema.*' AS 权限,
    '性能监控数据' AS 用途
UNION ALL
SELECT 
    'mysql.*' AS 权限,
    '系统信息查询' AS 用途
UNION ALL
SELECT 
    'sys.*' AS 权限,
    '系统信息查询' AS 用途;

-- 安全建议
SELECT '安全建议:' AS 建议;
SELECT '1. 将 % 替换为具体的IP地址或IP段' AS 建议;
SELECT '2. 使用强密码并定期更换' AS 建议;
SELECT '3. 启用SSL/TLS加密连接' AS 建议;
SELECT '4. 定期审查权限设置' AS 建议;
SELECT '5. 启用MySQL审计日志' AS 建议;
SELECT '6. 仅授予必要的查询权限，遵循最小权限原则' AS 建议;
