-- PostgreSQL 初始化脚本 v2.0
-- 鲸落 (Whalefall) 数据库初始化脚本
-- 基于当前 SQLAlchemy 模型结构生成
-- 支持 PostgreSQL 优化特性：SERIAL/IDENTITY、索引、约束、JSONB等
-- 确保幂等性：使用 CREATE TABLE IF NOT EXISTS 和 INSERT ... ON CONFLICT DO NOTHING

-- 设置时区和字符集
SET timezone = 'Asia/Shanghai';
SET client_encoding = 'UTF8';

-- 开始事务
BEGIN;

-- ============================================================================
-- 1. 用户管理模块
-- ============================================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 用户表索引
CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);

-- ============================================================================
-- 2. 数据库类型配置模块
-- ============================================================================

-- 数据库类型配置表
CREATE TABLE IF NOT EXISTS database_type_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    driver VARCHAR(50) NOT NULL,
    default_port INTEGER NOT NULL,
    default_schema VARCHAR(50) NOT NULL,
    connection_timeout INTEGER DEFAULT 30,
    description TEXT,
    icon VARCHAR(50) DEFAULT 'fa-database',
    color VARCHAR(20) DEFAULT 'primary',
    features TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_system BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 3. 凭据管理模块
-- ============================================================================

-- 凭据表
CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    credential_type VARCHAR(50) NOT NULL,
    db_type VARCHAR(50),
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    description TEXT,
    instance_ids JSONB,
    category_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 凭据表索引
CREATE INDEX IF NOT EXISTS ix_credentials_credential_type ON credentials(credential_type);
CREATE INDEX IF NOT EXISTS ix_credentials_db_type ON credentials(db_type);
CREATE INDEX IF NOT EXISTS ix_credentials_name ON credentials(name);

-- ============================================================================
-- 4. 实例管理模块
-- ============================================================================

-- 实例表
CREATE TABLE IF NOT EXISTS instances (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    db_type VARCHAR(50) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database_name VARCHAR(255),
    database_version VARCHAR(1000),
    main_version VARCHAR(20),
    detailed_version VARCHAR(50),
    environment VARCHAR(20) NOT NULL DEFAULT 'production',
    sync_count INTEGER NOT NULL DEFAULT 0,
    credential_id INTEGER REFERENCES credentials(id),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_connected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 实例表索引
CREATE UNIQUE INDEX IF NOT EXISTS ix_instances_name ON instances(name);
CREATE INDEX IF NOT EXISTS ix_instances_status ON instances(status);
CREATE INDEX IF NOT EXISTS ix_instances_db_type ON instances(db_type);
CREATE INDEX IF NOT EXISTS ix_instances_environment ON instances(environment);

-- ============================================================================
-- 5. 标签管理模块
-- ============================================================================

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    color VARCHAR(20) DEFAULT 'primary' NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 标签表索引
CREATE INDEX IF NOT EXISTS ix_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS ix_tags_category ON tags(category);

-- 实例标签关联表
CREATE TABLE IF NOT EXISTS instance_tags (
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (instance_id, tag_id)
);

-- ============================================================================
-- 6. 账户同步数据模块
-- ============================================================================

-- 基础同步数据表（抽象基类，不直接创建）
-- 账户当前状态同步数据表
CREATE TABLE IF NOT EXISTS current_account_sync_data (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    db_type VARCHAR(20) NOT NULL,
    session_id VARCHAR(36),
    sync_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'success',
    message TEXT,
    error_message TEXT,
    username VARCHAR(255) NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- MySQL权限字段
    global_privileges JSONB,
    database_privileges JSONB,
    
    -- PostgreSQL权限字段
    predefined_roles JSONB,
    role_attributes JSONB,
    database_privileges_pg JSONB,
    tablespace_privileges JSONB,
    
    -- SQL Server权限字段
    server_roles JSONB,
    server_permissions JSONB,
    database_roles JSONB,
    database_permissions JSONB,
    
    -- Oracle权限字段
    oracle_roles JSONB,
    system_privileges JSONB,
    tablespace_privileges_oracle JSONB,
    
    -- 通用扩展字段
    type_specific JSONB,
    last_classified_at TIMESTAMP WITH TIME ZONE,
    last_classification_batch_id VARCHAR(36)
);

-- 账户同步数据表索引
CREATE UNIQUE INDEX IF NOT EXISTS uq_current_account_sync ON current_account_sync_data(instance_id, db_type, username);
CREATE INDEX IF NOT EXISTS idx_instance_dbtype ON current_account_sync_data(instance_id, db_type);
CREATE INDEX IF NOT EXISTS idx_deleted ON current_account_sync_data(is_deleted);
CREATE INDEX IF NOT EXISTS idx_username ON current_account_sync_data(username);
CREATE INDEX IF NOT EXISTS idx_session_id ON current_account_sync_data(session_id);

-- ============================================================================
-- 7. 账户分类管理模块
-- ============================================================================

-- 账户分类表
CREATE TABLE IF NOT EXISTS account_classifications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    color VARCHAR(20),
    icon_name VARCHAR(50) DEFAULT 'fa-tag',
    priority INTEGER DEFAULT 0,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 分类规则表
CREATE TABLE IF NOT EXISTS classification_rules (
    id SERIAL PRIMARY KEY,
    classification_id INTEGER NOT NULL REFERENCES account_classifications(id),
    db_type VARCHAR(20) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_expression TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 账户分类分配表
CREATE TABLE IF NOT EXISTS account_classification_assignments (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES current_account_sync_data(id),
    classification_id INTEGER NOT NULL REFERENCES account_classifications(id),
    assigned_by INTEGER REFERENCES users(id),
    assignment_type VARCHAR(20) NOT NULL DEFAULT 'auto',
    confidence_score REAL,
    notes TEXT,
    batch_id VARCHAR(36),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_account_classification_batch UNIQUE (account_id, classification_id, batch_id)
);

-- 账户分类分配表索引
CREATE INDEX IF NOT EXISTS idx_account_classification_assignments_account_id ON account_classification_assignments(account_id);
CREATE INDEX IF NOT EXISTS idx_account_classification_assignments_classification_id ON account_classification_assignments(classification_id);
CREATE INDEX IF NOT EXISTS idx_account_classification_assignments_is_active ON account_classification_assignments(is_active);

-- ============================================================================
-- 8. 权限配置模块
-- ============================================================================

-- 权限配置表
CREATE TABLE IF NOT EXISTS permission_configs (
    id SERIAL PRIMARY KEY,
    db_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    permission_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_permission_config UNIQUE (db_type, category, permission_name)
);

-- 权限配置表索引
CREATE INDEX IF NOT EXISTS idx_permission_config_db_type ON permission_configs(db_type);
CREATE INDEX IF NOT EXISTS idx_permission_config_category ON permission_configs(category);

-- ============================================================================
-- 9. 同步会话管理模块
-- ============================================================================

-- 同步会话表
CREATE TABLE IF NOT EXISTS sync_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) UNIQUE NOT NULL,
    sync_type VARCHAR(20) NOT NULL CHECK (sync_type IN ('manual_single', 'manual_batch', 'manual_task', 'scheduled_task')),
    sync_category VARCHAR(20) NOT NULL DEFAULT 'account' CHECK (sync_category IN ('account', 'capacity', 'config', 'other')),
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    total_instances INTEGER DEFAULT 0,
    successful_instances INTEGER DEFAULT 0,
    failed_instances INTEGER DEFAULT 0,
    created_by INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 同步实例记录表
CREATE TABLE IF NOT EXISTS sync_instance_records (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES sync_sessions(session_id) ON DELETE CASCADE,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    instance_name VARCHAR(255),
    sync_category VARCHAR(20) NOT NULL DEFAULT 'account' CHECK (sync_category IN ('account', 'capacity', 'config', 'other')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    accounts_synced INTEGER DEFAULT 0,
    accounts_created INTEGER DEFAULT 0,
    accounts_updated INTEGER DEFAULT 0,
    accounts_deleted INTEGER DEFAULT 0,
    error_message TEXT,
    sync_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 同步会话表索引
CREATE INDEX IF NOT EXISTS idx_sync_sessions_session_id ON sync_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sync_sessions_sync_type ON sync_sessions(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_sessions_sync_category ON sync_sessions(sync_category);
CREATE INDEX IF NOT EXISTS idx_sync_sessions_status ON sync_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sync_sessions_created_at ON sync_sessions(created_at);

-- 同步实例记录表索引
CREATE INDEX IF NOT EXISTS idx_sync_instance_records_session_id ON sync_instance_records(session_id);
CREATE INDEX IF NOT EXISTS idx_sync_instance_records_instance_id ON sync_instance_records(instance_id);
CREATE INDEX IF NOT EXISTS idx_sync_instance_records_sync_category ON sync_instance_records(sync_category);
CREATE INDEX IF NOT EXISTS idx_sync_instance_records_status ON sync_instance_records(status);
CREATE INDEX IF NOT EXISTS idx_sync_instance_records_created_at ON sync_instance_records(created_at);

-- ============================================================================
-- 10. 自动分类批次管理模块
-- ============================================================================

-- 自动分类批次表
CREATE TABLE IF NOT EXISTS classification_batches (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(36) UNIQUE NOT NULL,
    batch_type VARCHAR(20) NOT NULL CHECK (batch_type IN ('manual', 'scheduled', 'api')),
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    total_accounts INTEGER DEFAULT 0,
    matched_accounts INTEGER DEFAULT 0,
    failed_accounts INTEGER DEFAULT 0,
    total_rules INTEGER DEFAULT 0,
    active_rules INTEGER DEFAULT 0,
    error_message TEXT,
    batch_details JSONB,
    created_by INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 自动分类批次表索引
CREATE INDEX IF NOT EXISTS idx_classification_batches_batch_id ON classification_batches(batch_id);
CREATE INDEX IF NOT EXISTS idx_classification_batches_batch_type ON classification_batches(batch_type);
CREATE INDEX IF NOT EXISTS idx_classification_batches_status ON classification_batches(status);
CREATE INDEX IF NOT EXISTS idx_classification_batches_started_at ON classification_batches(started_at);
CREATE INDEX IF NOT EXISTS idx_classification_batches_created_by ON classification_batches(created_by);

-- ============================================================================
-- 11. 统一日志管理模块
-- ============================================================================

-- 统一日志表
CREATE TABLE IF NOT EXISTS unified_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    level VARCHAR(8) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    module VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    traceback TEXT,
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 统一日志表索引
CREATE INDEX IF NOT EXISTS idx_unified_logs_timestamp ON unified_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_unified_logs_level ON unified_logs(level);
CREATE INDEX IF NOT EXISTS idx_unified_logs_module ON unified_logs(module);
CREATE INDEX IF NOT EXISTS idx_unified_logs_created_at ON unified_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_timestamp_level_module ON unified_logs(timestamp, level, module);
CREATE INDEX IF NOT EXISTS idx_timestamp_module ON unified_logs(timestamp, module);
CREATE INDEX IF NOT EXISTS idx_level_timestamp ON unified_logs(level, timestamp);

-- ============================================================================
-- 12. 账户变更日志模块
-- ============================================================================

-- 账户变更日志表
CREATE TABLE IF NOT EXISTS account_change_log (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    db_type VARCHAR(20) NOT NULL,
    username VARCHAR(255) NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    change_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_id VARCHAR(36),
    status VARCHAR(20) DEFAULT 'success',
    message TEXT,
    privilege_diff JSONB,
    other_diff JSONB
);

-- 账户变更日志表索引
CREATE INDEX IF NOT EXISTS idx_account_change_log_instance_id ON account_change_log(instance_id);
CREATE INDEX IF NOT EXISTS idx_account_change_log_db_type ON account_change_log(db_type);
CREATE INDEX IF NOT EXISTS idx_account_change_log_username ON account_change_log(username);
CREATE INDEX IF NOT EXISTS idx_account_change_log_change_time ON account_change_log(change_time);
CREATE INDEX IF NOT EXISTS idx_instance_dbtype_username_time ON account_change_log(instance_id, db_type, username, change_time);
CREATE INDEX IF NOT EXISTS idx_change_type_time ON account_change_log(change_type, change_time);
CREATE INDEX IF NOT EXISTS idx_username_time ON account_change_log(username, change_time);

-- ============================================================================
-- 13. 全局参数模块
-- ============================================================================

-- 全局参数表
CREATE TABLE IF NOT EXISTS global_params (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    param_type VARCHAR(50) NOT NULL DEFAULT 'string',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- 14. 创建触发器函数
-- ============================================================================

-- 创建updated_at字段自动更新触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为各表创建updated_at触发器
CREATE TRIGGER update_database_type_configs_updated_at BEFORE UPDATE ON database_type_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_credentials_updated_at BEFORE UPDATE ON credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_instances_updated_at BEFORE UPDATE ON instances FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tags_updated_at BEFORE UPDATE ON tags FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_account_classifications_updated_at BEFORE UPDATE ON account_classifications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_classification_rules_updated_at BEFORE UPDATE ON classification_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_account_classification_assignments_updated_at BEFORE UPDATE ON account_classification_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_permission_configs_updated_at BEFORE UPDATE ON permission_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sync_sessions_updated_at BEFORE UPDATE ON sync_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_classification_batches_updated_at BEFORE UPDATE ON classification_batches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 15. 插入初始数据
-- ============================================================================

-- 插入用户数据
INSERT INTO users (id, username, password, role, created_at, last_login, is_active) VALUES
(1, 'admin', '$2b$12$DKFZJIArZQ0ASgxpcGyrHeAXYTBS0ThJjewzso1BnQQm7UWdomcAu', 'admin', '2025-09-12 00:25:19.014781', NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- 重置序列
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- 插入数据库类型配置数据
INSERT INTO database_type_configs (id, name, display_name, driver, default_port, default_schema, connection_timeout, description, icon, color, features, is_active, is_system, sort_order, created_at, updated_at) VALUES
(1, 'mysql', 'MySQL', 'pymysql', 3306, 'mysql', 30, 'MySQL数据库', 'fa-database', 'primary', '["replication", "partitioning", "json"]', TRUE, TRUE, 1, '2025-09-12 02:02:33.898448', '2025-09-12 03:02:58.406875'),
(2, 'postgresql', 'PostgreSQL', 'psycopg', 5432, 'postgres', 30, 'PostgreSQL数据库', 'fa-database', 'info', '["jsonb", "arrays", "full_text_search"]', TRUE, TRUE, 2, '2025-09-12 02:02:33.899255', '2025-09-12 03:06:59.898296'),
(3, 'sqlserver', 'SQL Server', 'pymssql', 1433, 'master', 30, 'Microsoft SQL Server数据库', 'fa-database', 'danger', '["clustering", "mirroring", "always_on"]', TRUE, TRUE, 3, '2025-09-12 02:02:33.899542', '2025-09-12 03:08:49.557828'),
(4, 'oracle', 'Oracle', 'oracledb', 1521, 'orcl', 30, 'Oracle数据库', 'fa-database', 'warning', '["rac", "asm", "flashback"]', TRUE, TRUE, 4, '2025-09-12 02:02:33.899757', '2025-09-12 03:02:58.407992')
ON CONFLICT (id) DO NOTHING;

-- 重置序列
SELECT setval('database_type_configs_id_seq', (SELECT MAX(id) FROM database_type_configs));

-- 插入账户分类数据
INSERT INTO account_classifications (id, name, description, risk_level, color, icon_name, priority, is_system, is_active, created_at, updated_at) VALUES
(2, '敏感账户', '可授权特定权限以满足业务需求，同时需严格安全控制', 'high', '#fd7e14', 'fa-tag', 80, TRUE, TRUE, '2025-09-12 00:44:16.876132', '2025-09-12 05:28:53.681826'),
(4, '风险账户', '可用于删除库和表的操作，需特别监控以防止误删或恶意行为', 'medium', '#bf17fd', 'fa-tag', 70, TRUE, TRUE, '2025-09-12 00:44:16.876198', '2025-09-12 05:27:36.043494'),
(5, '只读用户', NULL, 'critical', '#69dc38', 'fa-tag', 50, TRUE, TRUE, '2025-09-12 00:44:16.876219', '2025-09-12 05:29:01.826658'),
(7, '特权账户', '用于具有高级权限的管理员或系统账户，负责管理数据库核心操作', 'critical', '#dc3545', 'fa-tag', 90, TRUE, TRUE, '2025-09-12 00:44:16.876259', '2025-09-12 05:26:04.919677'),
(8, '普通账户', '用于日常操作的普通用户账户，权限范围有限', 'low', '#3c49fb', 'fa-tag', 60, TRUE, TRUE, '2025-09-12 00:44:16.876276', '2025-09-12 05:27:45.250653')
ON CONFLICT (id) DO NOTHING;

-- 重置序列
SELECT setval('account_classifications_id_seq', (SELECT MAX(id) FROM account_classifications));

-- 插入分类规则数据
INSERT INTO classification_rules (id, classification_id, db_type, rule_name, rule_expression, is_active, created_at, updated_at) VALUES
(2, 2, 'oracle', 'oracle_super_rule', '{"type": "oracle_permissions", "roles": ["DBA"], "system_privileges": [], "tablespace_privileges": [], "tablespace_quotas": [], "operator": "OR"}', TRUE, '2025-09-12 00:44:16.879297', '2025-09-12 06:08:14.494067'),
(4, 4, 'postgresql', 'postgresql_grant_rule', '{"type": "postgresql_permissions", "role_attributes": ["CREATEROLE"], "database_privileges": [], "tablespace_privileges": [], "operator": "OR"}', TRUE, '2025-09-12 00:44:16.879795', '2025-09-12 06:03:24.239989'),
(5, 7, 'mysql', 'mysql_super_rule', '{"type": "mysql_permissions", "global_privileges": ["SUPER"], "database_privileges": [], "operator": "OR"}', TRUE, '2025-09-12 00:44:16.880022', '2025-09-12 05:31:38.194297'),
(7, 7, 'sqlserver', 'sqlserver_super_rule', '{"type": "sqlserver_permissions", "server_roles": ["sysadmin"], "server_permissions": [], "database_roles": [], "database_privileges": [], "operator": "OR"}', TRUE, '2025-09-12 00:44:16.880470', '2025-09-12 05:39:51.998024'),
(8, 2, 'sqlserver', 'sqlserver_grant_rule', '{"type": "sqlserver_permissions", "server_roles": ["securityadmin"], "server_permissions": [], "database_roles": [], "database_privileges": [], "operator": "OR"}', TRUE, '2025-09-12 00:44:16.880657', '2025-09-12 06:00:46.901211'),
(9, 2, 'mysql', 'mysql_grant_rule', '{"type": "mysql_permissions", "global_privileges": ["GRANT OPTION"], "database_privileges": [], "operator": "OR"}', TRUE, '2025-09-12 05:34:11.813260', '2025-09-12 05:34:11.813269'),
(10, 4, 'mysql', 'mysql_delete_rule', '{"type": "mysql_permissions", "global_privileges": ["DROP"], "database_privileges": ["DROP"], "operator": "OR"}', TRUE, '2025-09-12 05:34:53.465284', '2025-09-12 05:34:53.465291'),
(11, 4, 'sqlserver', 'sqlserver_delete_rule', '{"type": "sqlserver_permissions", "server_roles": [], "server_permissions": ["ALTER ANY DATABASE"], "database_roles": ["db_owner"], "database_privileges": ["DELETE"], "operator": "OR"}', TRUE, '2025-09-12 06:01:31.340355', '2025-09-12 06:01:31.340362'),
(12, 7, 'postgresql', 'postgresql_super_rule', '{"type": "postgresql_permissions", "role_attributes": ["SUPERUSER"], "database_privileges": [], "tablespace_privileges": [], "permissions": ["SUPERUSER"], "operator": "OR"}', TRUE, '2025-09-12 06:03:41.681866', '2025-09-12 06:03:41.681870')
ON CONFLICT (id) DO NOTHING;

-- 重置序列
SELECT setval('classification_rules_id_seq', (SELECT MAX(id) FROM classification_rules));

-- ============================================================================
-- 16. 提交事务
-- ============================================================================

COMMIT;

-- ============================================================================
-- 17. 验证数据
-- ============================================================================

-- 显示表统计信息
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;

-- 显示初始数据统计
SELECT 'Users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'Database Types', COUNT(*) FROM database_type_configs
UNION ALL
SELECT 'Credentials', COUNT(*) FROM credentials
UNION ALL
SELECT 'Instances', COUNT(*) FROM instances
UNION ALL
SELECT 'Tags', COUNT(*) FROM tags
UNION ALL
SELECT 'Account Classifications', COUNT(*) FROM account_classifications
UNION ALL
SELECT 'Classification Rules', COUNT(*) FROM classification_rules
UNION ALL
SELECT 'Permission Configs', COUNT(*) FROM permission_configs
UNION ALL
SELECT 'Sync Sessions', COUNT(*) FROM sync_sessions
UNION ALL
SELECT 'Classification Batches', COUNT(*) FROM classification_batches
UNION ALL
SELECT 'Unified Logs', COUNT(*) FROM unified_logs
UNION ALL
SELECT 'Account Change Log', COUNT(*) FROM account_change_log
UNION ALL
SELECT 'Global Params', COUNT(*) FROM global_params;

-- 脚本执行完成提示
SELECT 'PostgreSQL 初始化脚本执行完成！' as message,
       '鲸落 (Whalefall) 数据库已准备就绪' as description,
       NOW() as completed_at;