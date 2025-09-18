-- 鲸落数据库初始化脚本
-- 创建时间: 2024-09-12
-- 描述: 生产环境PostgreSQL数据库初始化

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建默认的postgres超级用户（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
        CREATE ROLE postgres WITH LOGIN SUPERUSER CREATEDB CREATEROLE;
    END IF;
END
$$;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- 创建数据库用户（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'taifish_readonly') THEN
        CREATE ROLE taifish_readonly;
    END IF;
END
$$;

-- 设置只读用户权限
GRANT CONNECT ON DATABASE taifish_prod TO taifish_readonly;
GRANT USAGE ON SCHEMA public TO taifish_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO taifish_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO taifish_readonly;

-- 设置默认权限，确保新创建的表也会给只读用户权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO taifish_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO taifish_readonly;

-- 创建监控用户
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'taifish_monitor') THEN
        CREATE ROLE taifish_monitor WITH LOGIN PASSWORD 'Monitor2024!';
    END IF;
END
$$;

-- 给监控用户基本权限
GRANT CONNECT ON DATABASE taifish_prod TO taifish_monitor;
GRANT USAGE ON SCHEMA public TO taifish_monitor;

-- 创建备份用户
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'taifish_backup') THEN
        CREATE ROLE taifish_backup WITH LOGIN PASSWORD 'Backup2024!';
    END IF;
END
$$;

-- 给备份用户权限
GRANT CONNECT ON DATABASE taifish_prod TO taifish_backup;
GRANT USAGE ON SCHEMA public TO taifish_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO taifish_backup;

-- 设置数据库参数优化
ALTER DATABASE taifish_prod SET timezone TO 'Asia/Shanghai';
ALTER DATABASE taifish_prod SET log_statement TO 'mod';
ALTER DATABASE taifish_prod SET log_min_duration_statement TO 1000;
ALTER DATABASE taifish_prod SET log_line_prefix TO '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- 创建函数：获取数据库大小
CREATE OR REPLACE FUNCTION get_database_size()
RETURNS TEXT AS $$
BEGIN
    RETURN pg_size_pretty(pg_database_size(current_database()));
END;
$$ LANGUAGE plpgsql;

-- 创建函数：获取表大小
CREATE OR REPLACE FUNCTION get_table_size(table_name TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pg_size_pretty(pg_total_relation_size(table_name::regclass));
END;
$$ LANGUAGE plpgsql;

-- 创建函数：清理旧日志
CREATE OR REPLACE FUNCTION cleanup_old_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM logs
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 创建索引优化函数
CREATE OR REPLACE FUNCTION create_performance_indexes()
RETURNS VOID AS $$
BEGIN
    -- 为常用查询创建索引
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_created_at ON logs(created_at);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_level ON logs(level);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_module ON logs(module);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_source ON logs(source);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_user_id ON logs(user_id);

    -- 复合索引
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_level_created_at ON logs(level, created_at);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_logs_module_level ON logs(module, level);

    -- 为账户表创建索引
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_instance_id ON accounts(instance_id);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_username ON accounts(username);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_accounts_is_active ON accounts(is_active);

    -- 为任务表创建索引
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_status ON tasks(status);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
END;
$$ LANGUAGE plpgsql;

-- 创建数据库统计视图
CREATE OR REPLACE VIEW database_stats AS
SELECT
    'Database Size' as metric,
    get_database_size() as value
UNION ALL
SELECT
    'Total Tables' as metric,
    count(*)::text as value
FROM information_schema.tables
WHERE table_schema = 'public'
UNION ALL
SELECT
    'Total Logs' as metric,
    count(*)::text as value
FROM logs
UNION ALL
SELECT
    'Total Accounts' as metric,
    count(*)::text as value
FROM accounts
UNION ALL
SELECT
    'Active Accounts' as metric,
    count(*)::text as value
FROM accounts
WHERE is_active = true;

-- 创建日志统计视图
CREATE OR REPLACE VIEW log_stats AS
SELECT
    level,
    module,
    source,
    COUNT(*) as count,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM logs
GROUP BY level, module, source
ORDER BY count DESC;

-- 创建用户活动统计视图
CREATE OR REPLACE VIEW user_activity_stats AS
SELECT
    u.username,
    u.role,
    u.is_active,
    u.last_login,
    COUNT(l.id) as log_count,
    MAX(l.created_at) as last_activity
FROM users u
LEFT JOIN logs l ON u.id = l.user_id
GROUP BY u.id, u.username, u.role, u.is_active, u.last_login
ORDER BY last_activity DESC NULLS LAST;

-- 创建定期清理任务（需要pg_cron扩展）
-- 注意：在生产环境中需要安装pg_cron扩展
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('cleanup-logs', '0 2 * * *', 'SELECT cleanup_old_logs(30);');

-- 创建数据库备份函数
CREATE OR REPLACE FUNCTION backup_database()
RETURNS TEXT AS $$
DECLARE
    backup_file TEXT;
    backup_cmd TEXT;
BEGIN
    backup_file := '/tmp/taifish_backup_' || to_char(NOW(), 'YYYYMMDD_HH24MISS') || '.sql';
    backup_cmd := 'pg_dump -h localhost -U taifish_user -d taifish_prod > ' || backup_file;

    -- 这里只是示例，实际备份需要系统级权限
    RETURN 'Backup command: ' || backup_cmd;
END;
$$ LANGUAGE plpgsql;

-- 设置数据库连接限制
ALTER DATABASE taifish_prod SET max_connections TO 200;

-- 创建连接池配置建议
COMMENT ON DATABASE taifish_prod IS '鲸落生产数据库 - 建议使用连接池，最大连接数200';

-- 完成初始化
INSERT INTO logs (level, module, message, details, source)
VALUES ('INFO', 'database', '数据库初始化完成', 'PostgreSQL生产环境初始化脚本执行完成', 'system_operation')
ON CONFLICT DO NOTHING;
