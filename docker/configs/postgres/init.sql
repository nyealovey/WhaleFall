-- 鲸落 - PostgreSQL初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 设置时区
SET timezone = 'UTC';

-- 创建数据库（如果不存在）
-- 注意：数据库已经在环境变量中创建

-- 设置连接参数
ALTER DATABASE taifish_dev SET timezone TO 'UTC';
ALTER DATABASE taifish_dev SET log_statement TO 'all';
ALTER DATABASE taifish_dev SET log_min_duration_statement TO 1000;

-- 创建用户（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'taifish_user') THEN
        CREATE ROLE taifish_user WITH LOGIN PASSWORD 'taifish_pass';
    END IF;
END
$$;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE taifish_dev TO taifish_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO taifish_user;

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO taifish_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO taifish_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO taifish_user;

-- 创建索引优化
-- 这些将在Flask-Migrate创建表后自动创建

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL数据库初始化完成！';
    RAISE NOTICE '数据库: taifish_dev';
    RAISE NOTICE '用户: taifish_user';
    RAISE NOTICE '时区: UTC';
END
$$;
