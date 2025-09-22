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

-- 3. 授予mysql.user表查询权限（最低权限）
GRANT SELECT ON mysql.user TO 'monitor_user'@'%';

-- 4. 刷新权限
FLUSH PRIVILEGES;

-- 5. 验证权限设置
SELECT 'MySQL 监控用户权限设置完成' AS 状态;

-- 显示当前用户权限
SHOW GRANTS FOR 'monitor_user'@'%';

-- 测试权限
SELECT '连接测试' AS 测试项目, @@VERSION AS 结果;
SELECT 'mysql.user表测试' AS 测试项目, COUNT(*) AS 可访问的用户数量 FROM mysql.user;

-- 显示权限摘要
SELECT 
    'mysql.user' AS 表名,
    'SELECT' AS 权限,
    '用户信息查询' AS 用途;

-- 安全建议
SELECT '安全建议:' AS 建议;
SELECT '1. 将 % 替换为具体的IP地址或IP段' AS 建议;
SELECT '2. 使用强密码并定期更换' AS 建议;
SELECT '3. 启用SSL/TLS加密连接' AS 建议;
SELECT '4. 定期审查权限设置' AS 建议;
SELECT '5. 启用MySQL审计日志' AS 建议;
SELECT '6. 仅授予mysql.user表查询权限，遵循最小权限原则' AS 建议;
