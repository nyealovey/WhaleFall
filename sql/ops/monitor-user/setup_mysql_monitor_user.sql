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

-- 4. 授予全局查询权限（MySQL 8.4 需要）
GRANT SELECT ON *.* TO 'monitor_user'@'%';

-- 5. 授予SHOW VIEW权限（用于查看视图信息）
GRANT SHOW VIEW ON *.* TO 'monitor_user'@'%';

-- 6. 授予PROCESS权限（用于查看进程信息）
GRANT PROCESS ON *.* TO 'monitor_user'@'%';

-- 7. 授予REPLICATION CLIENT权限（用于查看复制状态）
GRANT REPLICATION CLIENT ON *.* TO 'monitor_user'@'%';

-- 8. 授予SHOW DATABASES权限（确保能查看所有数据库）
GRANT SHOW DATABASES ON *.* TO 'monitor_user'@'%';

-- 9. 刷新权限
FLUSH PRIVILEGES;

-- 10. 验证权限设置
SELECT 'MySQL 监控用户权限设置完成' AS 状态;

-- 显示当前用户权限
SHOW GRANTS FOR 'monitor_user'@'%';

-- 测试权限
SELECT '连接测试' AS 测试项目, @@VERSION AS 结果;
SELECT 'SHOW DATABASES测试' AS 测试项目, '请手动执行 SHOW DATABASES; 命令' AS 说明;
SELECT '全局SELECT权限测试' AS 测试项目, COUNT(*) AS 可访问的数据库数量 FROM information_schema.SCHEMATA;
SELECT 'information_schema.tables测试' AS 测试项目, COUNT(*) AS 可访问的表数量 FROM information_schema.tables;
SELECT '用户数据库表测试' AS 测试项目, COUNT(*) AS 可访问的用户表数量 FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys');
SELECT '数据库大小查询测试' AS 测试项目, '请手动执行数据库大小查询' AS 说明;

-- 显示权限摘要
SELECT 
    'SHOW DATABASES' AS 权限,
    '查看所有数据库列表' AS 用途
UNION ALL
SELECT 
    'SELECT ON *.*' AS 权限,
    '全局查询权限，访问所有数据库和表' AS 用途
UNION ALL
SELECT 
    'SHOW VIEW' AS 权限,
    '查看视图信息' AS 用途
UNION ALL
SELECT 
    'PROCESS' AS 权限,
    '查看进程信息' AS 用途
UNION ALL
SELECT 
    'REPLICATION CLIENT' AS 权限,
    '查看复制状态' AS 用途;

-- 安全建议
SELECT '安全建议:' AS 建议;
SELECT '1. 将 % 替换为具体的IP地址或IP段' AS 建议;
SELECT '2. 使用强密码并定期更换' AS 建议;
SELECT '3. 启用SSL/TLS加密连接' AS 建议;
SELECT '4. 定期审查权限设置' AS 建议;
SELECT '5. 启用MySQL审计日志' AS 建议;
SELECT '6. 仅授予必要的查询权限，遵循最小权限原则' AS 建议;
