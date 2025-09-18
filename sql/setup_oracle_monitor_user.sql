-- =============================================
-- Oracle 监控用户权限设置脚本
-- 鲸落 - 数据同步管理平台
-- =============================================

-- 1. 创建监控用户
-- 注意：请将 'YourStrongPassword123!' 替换为强密码
CREATE USER monitor_user IDENTIFIED BY "YourStrongPassword123!";

-- 2. 设置默认表空间
ALTER USER monitor_user DEFAULT TABLESPACE USERS;

-- 3. 设置临时表空间
ALTER USER monitor_user TEMPORARY TABLESPACE TEMP;

-- 4. 设置配额
ALTER USER monitor_user QUOTA UNLIMITED ON USERS;

-- 5. 授予连接权限
GRANT CREATE SESSION TO monitor_user;

-- 6. 授予DBA视图查询权限
GRANT SELECT ON DBA_USERS TO monitor_user;
GRANT SELECT ON DBA_ROLES TO monitor_user;
GRANT SELECT ON DBA_ROLE_PRIVS TO monitor_user;
GRANT SELECT ON DBA_SYS_PRIVS TO monitor_user;
GRANT SELECT ON DBA_TAB_PRIVS TO monitor_user;
GRANT SELECT ON DBA_COL_PRIVS TO monitor_user;
GRANT SELECT ON DBA_PROXY_USERS TO monitor_user;

-- 7. 授予表空间相关权限
GRANT SELECT ON DBA_TS_QUOTAS TO monitor_user;
GRANT SELECT ON USER_TS_QUOTAS TO monitor_user;

-- 8. 授予对象相关权限
GRANT SELECT ON DBA_TABLES TO monitor_user;
GRANT SELECT ON DBA_INDEXES TO monitor_user;
GRANT SELECT ON DBA_OBJECTS TO monitor_user;

-- 7. 授予V$视图查询权限（可选，用于性能监控）
GRANT SELECT ON V$SESSION TO monitor_user;
GRANT SELECT ON V$INSTANCE TO monitor_user;
GRANT SELECT ON V$DATABASE TO monitor_user;

-- 9. 创建同义词（可选，简化查询）
CREATE SYNONYM monitor_user.dba_users FOR SYS.DBA_USERS;
CREATE SYNONYM monitor_user.dba_roles FOR SYS.DBA_ROLES;
CREATE SYNONYM monitor_user.dba_role_privs FOR SYS.DBA_ROLE_PRIVS;
CREATE SYNONYM monitor_user.dba_sys_privs FOR SYS.DBA_SYS_PRIVS;
CREATE SYNONYM monitor_user.dba_tab_privs FOR SYS.DBA_TAB_PRIVS;
CREATE SYNONYM monitor_user.dba_col_privs FOR SYS.DBA_COL_PRIVS;
CREATE SYNONYM monitor_user.dba_proxy_users FOR SYS.DBA_PROXY_USERS;
CREATE SYNONYM monitor_user.dba_ts_quotas FOR SYS.DBA_TS_QUOTAS;
CREATE SYNONYM monitor_user.user_ts_quotas FOR SYS.USER_TS_QUOTAS;
CREATE SYNONYM monitor_user.dba_tables FOR SYS.DBA_TABLES;
CREATE SYNONYM monitor_user.dba_indexes FOR SYS.DBA_INDEXES;
CREATE SYNONYM monitor_user.dba_objects FOR SYS.DBA_OBJECTS;

-- 10. 验证权限设置
SELECT 'Oracle 监控用户权限设置完成' AS 状态 FROM DUAL;

-- 显示当前用户权限
SELECT 
    'DBA_USERS' AS 视图名,
    'SELECT' AS 权限,
    '用户信息查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_ROLES' AS 视图名,
    'SELECT' AS 权限,
    '角色信息查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_ROLE_PRIVS' AS 视图名,
    'SELECT' AS 权限,
    '角色权限查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_SYS_PRIVS' AS 视图名,
    'SELECT' AS 权限,
    '系统权限查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_TAB_PRIVS' AS 视图名,
    'SELECT' AS 权限,
    '表权限查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_COL_PRIVS' AS 视图名,
    'SELECT' AS 权限,
    '列权限查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_PROXY_USERS' AS 视图名,
    'SELECT' AS 权限,
    '代理用户查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_TS_QUOTAS' AS 视图名,
    'SELECT' AS 权限,
    '表空间配额查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'USER_TS_QUOTAS' AS 视图名,
    'SELECT' AS 权限,
    '用户表空间配额查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_TABLES' AS 视图名,
    'SELECT' AS 权限,
    '表信息查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_INDEXES' AS 视图名,
    'SELECT' AS 权限,
    '索引信息查询' AS 用途
FROM DUAL
UNION ALL
SELECT 
    'DBA_OBJECTS' AS 视图名,
    'SELECT' AS 权限,
    '对象信息查询' AS 用途
FROM DUAL;

-- 测试权限
SELECT '连接测试' AS 测试项目, banner AS 结果 FROM v$version WHERE rownum = 1;
SELECT 'DBA_USERS表测试' AS 测试项目, COUNT(*) AS 可访问的用户数量 FROM dba_users;
SELECT 'DBA_ROLES表测试' AS 测试项目, COUNT(*) AS 可访问的角色数量 FROM dba_roles;
SELECT 'DBA_ROLE_PRIVS表测试' AS 测试项目, COUNT(*) AS 可访问的角色权限数量 FROM dba_role_privs;
SELECT 'DBA_SYS_PRIVS表测试' AS 测试项目, COUNT(*) AS 可访问的系统权限数量 FROM dba_sys_privs;
SELECT 'DBA_TAB_PRIVS表测试' AS 测试项目, COUNT(*) AS 可访问的表权限数量 FROM dba_tab_privs;
SELECT 'DBA_COL_PRIVS表测试' AS 测试项目, COUNT(*) AS 可访问的列权限数量 FROM dba_col_privs;
SELECT 'DBA_PROXY_USERS表测试' AS 测试项目, COUNT(*) AS 可访问的代理用户数量 FROM dba_proxy_users;
SELECT 'DBA_TS_QUOTAS表测试' AS 测试项目, COUNT(*) AS 可访问的表空间配额数量 FROM dba_ts_quotas;
SELECT 'USER_TS_QUOTAS表测试' AS 测试项目, COUNT(*) AS 可访问的用户表空间配额数量 FROM user_ts_quotas;
SELECT 'DBA_TABLES表测试' AS 测试项目, COUNT(*) AS 可访问的表数量 FROM dba_tables;
SELECT 'DBA_INDEXES表测试' AS 测试项目, COUNT(*) AS 可访问的索引数量 FROM dba_indexes;
SELECT 'DBA_OBJECTS表测试' AS 测试项目, COUNT(*) AS 可访问的对象数量 FROM dba_objects;

-- 显示V$视图权限（如果已授予）
SELECT 'V$SESSION表测试' AS 测试项目, COUNT(*) AS 可访问的会话数量 FROM v$session;
SELECT 'V$INSTANCE表测试' AS 测试项目, COUNT(*) AS 可访问的实例信息数量 FROM v$instance;
SELECT 'V$DATABASE表测试' AS 测试项目, COUNT(*) AS 可访问的数据库信息数量 FROM v$database;

-- 显示用户信息
SELECT 
    username AS 用户名,
    account_status AS 账户状态,
    created AS 创建时间,
    expiry_date AS 过期时间,
    profile AS 配置文件
FROM dba_users 
WHERE username = 'MONITOR_USER';

-- 安全建议
SELECT '安全建议:' AS 建议 FROM DUAL;
SELECT '1. 使用强密码并定期更换' AS 建议 FROM DUAL;
SELECT '2. 启用SSL/TLS加密连接' AS 建议 FROM DUAL;
SELECT '3. 定期审查权限设置' AS 建议 FROM DUAL;
SELECT '4. 启用Oracle审计日志' AS 建议 FROM DUAL;
SELECT '5. 考虑启用虚拟专用数据库(VPD)' AS 建议 FROM DUAL;
SELECT '6. 限制监控账户的登录来源IP' AS 建议 FROM DUAL;
