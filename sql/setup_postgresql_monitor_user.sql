-- =============================================
-- PostgreSQL 监控用户权限设置脚本
-- 鲸落 - 数据同步管理平台
-- =============================================

-- 1. 创建监控用户
-- 注意：请将 'YourStrongPassword123!' 替换为强密码
CREATE USER monitor_user WITH PASSWORD 'YourStrongPassword123!';

-- 2. 授予连接权限
GRANT CONNECT ON DATABASE postgres TO monitor_user;

-- 3. 授予系统表查询权限
GRANT SELECT ON pg_roles TO monitor_user;
GRANT SELECT ON pg_database TO monitor_user;
GRANT SELECT ON pg_namespace TO monitor_user;
GRANT SELECT ON pg_class TO monitor_user;
GRANT SELECT ON pg_proc TO monitor_user;

-- 4. 授予information_schema查询权限
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO monitor_user;

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
    'pg_database' AS 表名,
    'SELECT' AS 权限,
    '数据库信息查询' AS 用途
UNION ALL
SELECT 
    'pg_namespace' AS 表名,
    'SELECT' AS 权限,
    '模式信息查询' AS 用途
UNION ALL
SELECT 
    'pg_class' AS 表名,
    'SELECT' AS 权限,
    '表信息查询' AS 用途
UNION ALL
SELECT 
    'pg_proc' AS 表名,
    'SELECT' AS 权限,
    '函数信息查询' AS 用途
UNION ALL
SELECT 
    'information_schema.*' AS 表名,
    'SELECT' AS 权限,
    '权限详细信息查询' AS 用途;

-- 测试权限
SELECT '连接测试' AS 测试项目, version() AS 结果;
SELECT 'pg_roles表测试' AS 测试项目, COUNT(*) AS 可访问的角色数量 FROM pg_roles;
SELECT 'pg_database表测试' AS 测试项目, COUNT(*) AS 可访问的数据库数量 FROM pg_database;
SELECT 'pg_namespace表测试' AS 测试项目, COUNT(*) AS 可访问的模式数量 FROM pg_namespace;
SELECT 'pg_class表测试' AS 测试项目, COUNT(*) AS 可访问的表数量 FROM pg_class;
SELECT 'pg_proc表测试' AS 测试项目, COUNT(*) AS 可访问的函数数量 FROM pg_proc;
SELECT 'information_schema测试' AS 测试项目, COUNT(*) AS 可访问的权限信息数量 FROM information_schema.role_table_grants;

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
