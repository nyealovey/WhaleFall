-- =============================================
-- Oracle 查询性能优化建议
-- 泰摸鱼吧 - 数据同步管理平台
-- =============================================

-- 1. 为常用查询创建索引
-- 这些索引将显著提升批量查询的性能

-- DBA_ROLE_PRIVS 表索引
CREATE INDEX idx_dba_role_privs_grantee ON dba_role_privs(grantee);
CREATE INDEX idx_dba_role_privs_granted_role ON dba_role_privs(granted_role);

-- DBA_SYS_PRIVS 表索引  
CREATE INDEX idx_dba_sys_privs_grantee ON dba_sys_privs(grantee);
CREATE INDEX idx_dba_sys_privs_privilege ON dba_sys_privs(privilege);

-- DBA_TS_QUOTAS 表索引
CREATE INDEX idx_dba_ts_quotas_username ON dba_ts_quotas(username);
CREATE INDEX idx_dba_ts_quotas_tablespace ON dba_ts_quotas(tablespace_name);

-- DBA_TABLES 表索引（用于对象权限查询）
CREATE INDEX idx_dba_tables_owner ON dba_tables(owner);
CREATE INDEX idx_dba_tables_tablespace ON dba_tables(tablespace_name);

-- DBA_INDEXES 表索引（用于对象权限查询）
CREATE INDEX idx_dba_indexes_owner ON dba_indexes(owner);
CREATE INDEX idx_dba_indexes_tablespace ON dba_indexes(tablespace_name);

-- 2. 复合索引优化
-- 为多条件查询创建复合索引

-- 用户+角色复合索引
CREATE INDEX idx_dba_role_privs_grantee_role ON dba_role_privs(grantee, granted_role);

-- 用户+权限复合索引
CREATE INDEX idx_dba_sys_privs_grantee_priv ON dba_sys_privs(grantee, privilege);

-- 3. 统计信息更新
-- 确保Oracle优化器有最新的统计信息
BEGIN
    DBMS_STATS.GATHER_SCHEMA_STATS('SYS');
    DBMS_STATS.GATHER_SCHEMA_STATS('SYSTEM');
END;
/

-- 4. 查询优化建议
-- 使用以下优化后的查询模式

-- 批量查询用户角色（优化后）
-- 原查询：N次单独查询
-- 优化后：1次批量查询
SELECT grantee, granted_role
FROM dba_role_privs
WHERE grantee IN (:username_0, :username_1, :username_2, ...)
ORDER BY grantee, granted_role;

-- 批量查询系统权限（优化后）
SELECT grantee, privilege
FROM dba_sys_privs  
WHERE grantee IN (:username_0, :username_1, :username_2, ...)
ORDER BY grantee, privilege;

-- 批量查询表空间权限（优化后）
SELECT username, tablespace_name,
       CASE
           WHEN max_bytes = -1 THEN 'UNLIMITED'
           ELSE 'QUOTA'
       END as privilege
FROM dba_ts_quotas
WHERE username IN (:username_0, :username_1, :username_2, ...)
ORDER BY username, tablespace_name;

-- 5. 性能监控查询
-- 用于监控查询性能

-- 查看索引使用情况
SELECT index_name, table_name, column_name, column_position
FROM user_ind_columns
WHERE table_name IN ('DBA_ROLE_PRIVS', 'DBA_SYS_PRIVS', 'DBA_TS_QUOTAS')
ORDER BY table_name, index_name, column_position;

-- 查看表统计信息
SELECT table_name, num_rows, blocks, avg_row_len, last_analyzed
FROM user_tables
WHERE table_name IN ('DBA_ROLE_PRIVS', 'DBA_SYS_PRIVS', 'DBA_TS_QUOTAS')
ORDER BY table_name;

-- 6. 性能测试查询
-- 用于测试优化效果

-- 测试批量角色查询性能
SET TIMING ON;
SELECT COUNT(*) as role_count
FROM dba_role_privs
WHERE grantee IN (SELECT username FROM dba_users WHERE ROWNUM <= 100);
SET TIMING OFF;

-- 测试批量系统权限查询性能  
SET TIMING ON;
SELECT COUNT(*) as sys_priv_count
FROM dba_sys_privs
WHERE grantee IN (SELECT username FROM dba_users WHERE ROWNUM <= 100);
SET TIMING OFF;

-- 7. 安全建议
-- 确保监控用户有适当的权限

-- 检查监控用户权限
SELECT privilege, admin_option
FROM dba_sys_privs
WHERE grantee = 'MONITOR_USER'
ORDER BY privilege;

-- 检查监控用户角色
SELECT granted_role, admin_option  
FROM dba_role_privs
WHERE grantee = 'MONITOR_USER'
ORDER BY granted_role;

-- 8. 性能优化总结
-- 优化前：N+1查询问题，每个用户4-5次查询
-- 优化后：批量查询，总共5次查询（1次用户+4次权限）
-- 预期性能提升：80%以上（取决于用户数量）

SELECT 'Oracle查询性能优化建议执行完成' AS 状态 FROM DUAL;
