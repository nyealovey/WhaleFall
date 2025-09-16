-- Oracle授权语句 - 为MONITOR用户授予访问sys.user$表的权限
-- 执行前请确保以SYS或SYSTEM用户身份连接

-- 1. 授予MONITOR用户访问sys.user$表的权限
-- 注意：此授权将允许访问所有列，包括敏感信息如密码字段
-- 建议在应用代码中只查询需要的字段：user#, name, type#, ptime, ctime, account_status, expiry_date, created
GRANT SELECT ON sys.user$ TO monitor;

-- 验证权限是否授予成功
SELECT 'MONITOR用户权限验证' as status FROM dual;

-- 检查MONITOR用户是否有访问sys.user$的权限
SELECT COUNT(*) as user_count FROM sys.user$ WHERE ROWNUM <= 1;

-- 检查MONITOR用户是否可以查询PTIME字段
SELECT name, ctime, ptime FROM sys.user$ WHERE ROWNUM <= 1;

-- 检查MONITOR用户是否可以查询所有需要的字段
SELECT user#, name, type#, ptime FROM sys.user$ WHERE ROWNUM <= 1;