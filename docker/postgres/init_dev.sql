-- 泰摸鱼吧开发环境数据库初始化脚本
-- 创建时间: 2024-12-19
-- 描述: 开发环境PostgreSQL数据库初始化

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "auto_explain";

-- 创建数据库用户（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'taifish_readonly') THEN
        CREATE ROLE taifish_readonly;
    END IF;
END
$$;

-- 设置只读用户权限
GRANT CONNECT ON DATABASE taifish_dev TO taifish_readonly;
GRANT USAGE ON SCHEMA public TO taifish_readonly;

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
GRANT CONNECT ON DATABASE taifish_dev TO taifish_monitor;
GRANT USAGE ON SCHEMA public TO taifish_monitor;

-- 设置数据库参数优化（开发环境）
ALTER DATABASE taifish_dev SET timezone TO 'Asia/Shanghai';
ALTER DATABASE taifish_dev SET log_statement TO 'mod';
ALTER DATABASE taifish_dev SET log_min_duration_statement TO 1000;
ALTER DATABASE taifish_dev SET log_line_prefix TO '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

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
    -- 这个函数会在表创建后使用
    -- 现在只是创建函数定义
    RETURN 0;
END;
$$ LANGUAGE plpgsql;

-- 创建性能监控函数
CREATE OR REPLACE FUNCTION get_slow_queries(threshold_ms INTEGER DEFAULT 1000)
RETURNS TABLE (
    query TEXT,
    calls BIGINT,
    total_time DOUBLE PRECISION,
    mean_time DOUBLE PRECISION,
    max_time DOUBLE PRECISION,
    min_time DOUBLE PRECISION,
    stddev_time DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pg_stat_statements.query,
        pg_stat_statements.calls,
        pg_stat_statements.total_exec_time,
        pg_stat_statements.mean_exec_time,
        pg_stat_statements.max_exec_time,
        pg_stat_statements.min_exec_time,
        pg_stat_statements.stddev_exec_time
    FROM pg_stat_statements
    WHERE pg_stat_statements.mean_exec_time > threshold_ms
    ORDER BY pg_stat_statements.mean_exec_time DESC;
END;
$$ LANGUAGE plpgsql;

-- 创建数据库性能统计函数
CREATE OR REPLACE FUNCTION get_database_stats()
RETURNS TABLE (
    metric TEXT,
    value TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'Database Size'::TEXT, pg_size_pretty(pg_database_size(current_database()))::TEXT
    UNION ALL
    SELECT 'Total Connections'::TEXT, (SELECT count(*) FROM pg_stat_activity)::TEXT
    UNION ALL
    SELECT 'Active Connections'::TEXT, (SELECT count(*) FROM pg_stat_activity WHERE state = 'active')::TEXT
    UNION ALL
    SELECT 'Idle Connections'::TEXT, (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle')::TEXT
    UNION ALL
    SELECT 'Cache Hit Ratio'::TEXT, 
           round(
               (sum(blks_hit) * 100.0 / (sum(blks_hit) + sum(blks_read)))::numeric, 2
           )::TEXT
    FROM pg_stat_database WHERE datname = current_database()
    UNION ALL
    SELECT 'Total Queries'::TEXT, (SELECT sum(calls) FROM pg_stat_statements)::TEXT
    UNION ALL
    SELECT 'Slow Queries (>1s)'::TEXT, 
           (SELECT count(*) FROM pg_stat_statements WHERE mean_exec_time > 1000)::TEXT;
END;
$$ LANGUAGE plpgsql;

-- 创建表性能统计函数
CREATE OR REPLACE FUNCTION get_table_performance()
RETURNS TABLE (
    schemaname TEXT,
    tablename TEXT,
    size TEXT,
    row_count BIGINT,
    index_count INTEGER,
    last_vacuum TIMESTAMP,
    last_analyze TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.schemaname::TEXT,
        t.tablename::TEXT,
        pg_size_pretty(pg_total_relation_size(t.schemaname||'.'||t.tablename))::TEXT,
        t.n_tup_ins + t.n_tup_upd + t.n_tup_del as row_count,
        (SELECT count(*) FROM pg_indexes WHERE tablename = t.tablename)::INTEGER,
        t.last_vacuum,
        t.last_analyze
    FROM pg_stat_user_tables t
    ORDER BY pg_total_relation_size(t.schemaname||'.'||t.tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- 设置数据库连接限制（开发环境）
ALTER DATABASE taifish_dev SET max_connections TO 100;

-- 创建连接池配置建议
COMMENT ON DATABASE taifish_dev IS '泰摸鱼吧开发数据库 - 建议使用连接池，最大连接数100';

-- 完成初始化
DO $$
BEGIN
    -- 如果logs表存在，插入初始化日志
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'logs') THEN
        INSERT INTO logs (level, module, message, details, source)
        VALUES ('INFO', 'database', '数据库初始化完成', 'PostgreSQL开发环境初始化脚本执行完成', 'system_operation')
        ON CONFLICT DO NOTHING;
    END IF;
END
$$;
