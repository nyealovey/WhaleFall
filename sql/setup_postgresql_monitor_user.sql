-- =============================================
-- PostgreSQL 监控用户权限设置脚本
-- 鲸落 - 数据同步管理平台
-- =============================================

-- 1. 创建监控用户
-- 注意：请将 'YourStrongPassword123!' 替换为强密码
CREATE USER monitor_user WITH PASSWORD 'YourStrongPassword123!';

-- 2. 授予连接权限
GRANT CONNECT ON DATABASE postgres TO monitor_user;

-- 3. 授予系统表查询权限（最低权限）
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_auth_members TO monitor_user;

-- 4. 授予information_schema查询权限（仅需要的表）
GRANT SELECT ON information_schema.table_privileges TO monitor_user;
GRANT SELECT ON information_schema.role_usage_grants TO monitor_user;
GRANT SELECT ON information_schema.role_routine_grants TO monitor_user;

-- 5. 为所有现有数据库授予连接权限
DO $$
DECLARE
    db_name TEXT;
BEGIN
    FOR db_name IN SELECT datname FROM pg_database WHERE datistemplate = false
    LOOP
        EXECUTE 'GRANT CONNECT ON DATABASE ' || quote_ident(db_name) || ' TO monitor_user';
    END LOOP;
END $$;

-- 6. 验证权限设置
SELECT 'PostgreSQL 监控用户权限设置完成' AS 状态;

-- 显示当前用户权限
SELECT 
    'pg_roles' AS 表名,
    'SELECT' AS 权限,
    '角色和用户信息查询' AS 用途
UNION ALL
SELECT 
    'pg_auth_members' AS 表名,
    'SELECT' AS 权限,
    '角色成员关系查询' AS 用途
UNION ALL
SELECT 
    'information_schema.table_privileges' AS 表名,
    'SELECT' AS 权限,
    '表权限信息查询' AS 用途
UNION ALL
SELECT 
    'information_schema.role_usage_grants' AS 表名,
    'SELECT' AS 权限,
    '使用权限信息查询' AS 用途
UNION ALL
SELECT 
    'information_schema.role_routine_grants' AS 表名,
    'SELECT' AS 权限,
    '例程权限信息查询' AS 用途;

-- 测试权限
SELECT '连接测试' AS 测试项目, version() AS 结果;
SELECT 'pg_roles表测试' AS 测试项目, COUNT(*) AS 可访问的角色数量 FROM pg_roles;
SELECT 'pg_auth_members表测试' AS 测试项目, COUNT(*) AS 可访问的角色成员数量 FROM pg_auth_members;
SELECT 'information_schema.table_privileges测试' AS 测试项目, COUNT(*) AS 可访问的表权限数量 FROM information_schema.table_privileges;
SELECT 'information_schema.role_usage_grants测试' AS 测试项目, COUNT(*) AS 可访问的使用权限数量 FROM information_schema.role_usage_grants;
SELECT 'information_schema.role_routine_grants测试' AS 测试项目, COUNT(*) AS 可访问的例程权限数量 FROM information_schema.role_routine_grants;

-- 显示数据库连接权限
SELECT 
    datname AS 数据库名,
    'CONNECT' AS 权限,
    '数据库连接' AS 用途
FROM pg_database 
WHERE datistemplate = false
ORDER BY datname;

-- 安全建议
SELECT '安全建议:' AS 建议;
SELECT '1. 使用强密码并定期更换' AS 建议;
SELECT '2. 启用SSL/TLS加密连接' AS 建议;
SELECT '3. 定期审查权限设置' AS 建议;
SELECT '4. 启用PostgreSQL审计日志' AS 建议;
SELECT '5. 考虑启用行级安全策略' AS 建议;
SELECT '6. 仅授予必要的系统表查询权限，遵循最小权限原则' AS 建议;
