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

-- 6. 授予DBA视图查询权限（最低权限）
GRANT SELECT ON DBA_USERS TO monitor_user;
GRANT SELECT ON DBA_ROLES TO monitor_user;
GRANT SELECT ON DBA_ROLE_PRIVS TO monitor_user;
GRANT SELECT ON DBA_SYS_PRIVS TO monitor_user;

-- 7. 授予表空间相关权限
GRANT SELECT ON DBA_TS_QUOTAS TO monitor_user;

-- 注意：移除了以下不必要的权限：
-- - DBA_TAB_PRIVS, DBA_COL_PRIVS, DBA_PROXY_USERS (代码中未使用)
-- - USER_TS_QUOTAS (代码中未使用)
-- - DBA_TABLES, DBA_INDEXES, DBA_OBJECTS (代码中未使用)
-- - V$视图 (代码中未使用)

-- 8. 创建同义词（仅必要的）
CREATE SYNONYM monitor_user.dba_users FOR SYS.DBA_USERS;
CREATE SYNONYM monitor_user.dba_roles FOR SYS.DBA_ROLES;
CREATE SYNONYM monitor_user.dba_role_privs FOR SYS.DBA_ROLE_PRIVS;
CREATE SYNONYM monitor_user.dba_sys_privs FOR SYS.DBA_SYS_PRIVS;
CREATE SYNONYM monitor_user.dba_ts_quotas FOR SYS.DBA_TS_QUOTAS;

-- 9. 验证权限设置
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
    'DBA_TS_QUOTAS' AS 视图名,
    'SELECT' AS 权限,
    '表空间配额查询' AS 用途
FROM DUAL;

-- 测试权限
SELECT '连接测试' AS 测试项目, banner AS 结果 FROM v$version WHERE rownum = 1;
SELECT 'DBA_USERS表测试' AS 测试项目, COUNT(*) AS 可访问的用户数量 FROM dba_users;
SELECT 'DBA_ROLES表测试' AS 测试项目, COUNT(*) AS 可访问的角色数量 FROM dba_roles;
SELECT 'DBA_ROLE_PRIVS表测试' AS 测试项目, COUNT(*) AS 可访问的角色权限数量 FROM dba_role_privs;
SELECT 'DBA_SYS_PRIVS表测试' AS 测试项目, COUNT(*) AS 可访问的系统权限数量 FROM dba_sys_privs;
SELECT 'DBA_TS_QUOTAS表测试' AS 测试项目, COUNT(*) AS 可访问的表空间配额数量 FROM dba_ts_quotas;

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
SELECT '7. 仅授予必要的DBA视图查询权限，遵循最小权限原则' AS 建议 FROM DUAL;
