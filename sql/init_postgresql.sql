-- PostgreSQL 初始化脚本 v1.0
-- 鲸落 (TaifishV4) 数据库初始化脚本
-- 基于现有 SQLite 数据库结构和数据生成
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
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL
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
    connection_timeout INTEGER,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    features TEXT,
    is_active BOOLEAN,
    is_system BOOLEAN,
    sort_order INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
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
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
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
    database_version VARCHAR(100),
    environment VARCHAR(20) NOT NULL,
    sync_count INTEGER NOT NULL,
    credential_id INTEGER REFERENCES credentials(id),
    description TEXT,
    tags JSONB,
    status VARCHAR(20),
    is_active BOOLEAN NOT NULL,
    last_connected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 实例表索引
CREATE UNIQUE INDEX IF NOT EXISTS ix_instances_name ON instances(name);
CREATE INDEX IF NOT EXISTS ix_instances_status ON instances(status);
CREATE INDEX IF NOT EXISTS ix_instances_db_type ON instances(db_type);
CREATE INDEX IF NOT EXISTS ix_instances_environment ON instances(environment);

-- ============================================================================
-- 5. 账户管理模块
-- ============================================================================

-- 账户表
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    username VARCHAR(255) NOT NULL,
    host VARCHAR(255),
    database_name VARCHAR(255),
    account_type VARCHAR(50),
    plugin VARCHAR(100),
    password_expired BOOLEAN DEFAULT FALSE,
    password_last_changed TIMESTAMP WITH TIME ZONE,
    is_locked BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    permissions TEXT,
    is_superuser BOOLEAN DEFAULT FALSE,
    can_grant BOOLEAN DEFAULT FALSE,
    -- Oracle特有字段
    user_id INTEGER,
    lock_date TIMESTAMP WITH TIME ZONE,
    expiry_date TIMESTAMP WITH TIME ZONE,
    default_tablespace VARCHAR(100),
    -- SQL Server特有字段
    account_created_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 账户表索引
CREATE INDEX IF NOT EXISTS idx_accounts_instance_id ON accounts(instance_id);
CREATE INDEX IF NOT EXISTS idx_accounts_username ON accounts(username);
CREATE INDEX IF NOT EXISTS idx_accounts_is_active ON accounts(is_active);
CREATE INDEX IF NOT EXISTS idx_accounts_is_superuser ON accounts(is_superuser);

-- ============================================================================
-- 6. 账户分类管理模块
-- ============================================================================

-- 账户分类表
CREATE TABLE IF NOT EXISTS account_classifications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    risk_level VARCHAR(20) NOT NULL,
    color VARCHAR(20),
    priority INTEGER,
    is_system BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 分类规则表
CREATE TABLE IF NOT EXISTS classification_rules (
    id SERIAL PRIMARY KEY,
    classification_id INTEGER NOT NULL REFERENCES account_classifications(id),
    db_type VARCHAR(20) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_expression TEXT NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 账户分类分配表
CREATE TABLE IF NOT EXISTS account_classification_assignments (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    classification_id INTEGER NOT NULL REFERENCES account_classifications(id),
    assigned_by INTEGER REFERENCES users(id),
    assignment_type VARCHAR(20) NOT NULL DEFAULT 'auto',
    confidence_score REAL,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_account_classification UNIQUE (account_id, classification_id)
);

-- 账户分类分配表索引
CREATE INDEX IF NOT EXISTS idx_account_classification_assignments_account_id ON account_classification_assignments(account_id);
CREATE INDEX IF NOT EXISTS idx_account_classification_assignments_classification_id ON account_classification_assignments(classification_id);
CREATE INDEX IF NOT EXISTS idx_account_classification_assignments_is_active ON account_classification_assignments(is_active);

-- ============================================================================
-- 7. 权限配置模块
-- ============================================================================

-- 权限配置表
CREATE TABLE IF NOT EXISTS permission_configs (
    id SERIAL PRIMARY KEY,
    db_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    permission_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN,
    sort_order INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_permission_config UNIQUE (db_type, category, permission_name)
);

-- 权限配置表索引
CREATE INDEX IF NOT EXISTS idx_permission_config_db_type ON permission_configs(db_type);
CREATE INDEX IF NOT EXISTS idx_permission_config_category ON permission_configs(category);

-- ============================================================================
-- 8. 任务管理模块
-- ============================================================================

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL,
    db_type VARCHAR(50) NOT NULL,
    schedule VARCHAR(100),
    description TEXT,
    python_code TEXT,
    config JSONB,
    is_active BOOLEAN NOT NULL,
    is_builtin BOOLEAN NOT NULL,
    last_run TIMESTAMP WITH TIME ZONE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    last_status VARCHAR(20),
    last_message TEXT,
    run_count INTEGER,
    success_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 任务表索引
CREATE INDEX IF NOT EXISTS ix_tasks_db_type ON tasks(db_type);
CREATE INDEX IF NOT EXISTS ix_tasks_task_type ON tasks(task_type);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tasks_name ON tasks(name);

-- ============================================================================
-- 9. 同步数据模块
-- ============================================================================

-- 同步数据表
CREATE TABLE IF NOT EXISTS sync_data (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50) NOT NULL,
    instance_id INTEGER REFERENCES instances(id),
    task_id INTEGER REFERENCES tasks(id),
    data JSONB,
    sync_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'success',
    message TEXT,
    synced_count INTEGER DEFAULT 0,
    added_count INTEGER DEFAULT 0,
    removed_count INTEGER DEFAULT 0,
    modified_count INTEGER DEFAULT 0,
    error_message TEXT,
    records_count INTEGER DEFAULT 0
);

-- 同步数据表索引
CREATE INDEX IF NOT EXISTS idx_sync_data_sync_type ON sync_data(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_data_instance_id ON sync_data(instance_id);
CREATE INDEX IF NOT EXISTS idx_sync_data_task_id ON sync_data(task_id);
CREATE INDEX IF NOT EXISTS idx_sync_data_sync_time ON sync_data(sync_time);
CREATE INDEX IF NOT EXISTS idx_sync_data_status ON sync_data(status);

-- ============================================================================
-- 10. 账户变化跟踪模块
-- ============================================================================

-- 账户变化表
CREATE TABLE IF NOT EXISTS account_changes (
    id SERIAL PRIMARY KEY,
    sync_data_id INTEGER NOT NULL REFERENCES sync_data(id),
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    change_type VARCHAR(20) NOT NULL,
    account_data JSONB NOT NULL,
    change_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 账户变化表索引
CREATE INDEX IF NOT EXISTS idx_account_changes_sync_data_id ON account_changes(sync_data_id);
CREATE INDEX IF NOT EXISTS idx_account_changes_instance_id ON account_changes(instance_id);
CREATE INDEX IF NOT EXISTS idx_account_changes_change_type ON account_changes(change_type);
CREATE INDEX IF NOT EXISTS idx_account_changes_change_time ON account_changes(change_time);

-- ============================================================================
-- 11. 日志管理模块
-- ============================================================================

-- 日志表
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    log_type VARCHAR(50) NOT NULL,
    module VARCHAR(100),
    message TEXT NOT NULL,
    details TEXT,
    user_id INTEGER REFERENCES users(id),
    ip_address VARCHAR(45),
    user_agent TEXT,
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 日志表索引
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_log_type ON logs(log_type);
CREATE INDEX IF NOT EXISTS idx_logs_module ON logs(module);
CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);

-- ============================================================================
-- 12. 同步会话管理模块
-- ============================================================================

-- 同步会话表
CREATE TABLE IF NOT EXISTS sync_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) UNIQUE NOT NULL,
    sync_type VARCHAR(20) NOT NULL CHECK (sync_type IN ('scheduled', 'manual_batch')),
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
    session_id VARCHAR(36) NOT NULL,
    instance_id INTEGER NOT NULL,
    instance_name VARCHAR(255),
    sync_category VARCHAR(20) NOT NULL DEFAULT 'account' CHECK (sync_category IN ('account', 'capacity', 'config', 'other')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    -- 账户同步统计字段
    accounts_synced INTEGER DEFAULT 0,
    accounts_created INTEGER DEFAULT 0,
    accounts_updated INTEGER DEFAULT 0,
    accounts_deleted INTEGER DEFAULT 0,
    -- 通用字段
    error_message TEXT,
    sync_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sync_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE
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
-- 13. 自动分类批次管理模块
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
-- 14. 统一日志管理模块
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

-- ============================================================================
-- 15. 更新现有表结构
-- ============================================================================

-- 为sync_data表添加新字段
ALTER TABLE sync_data ADD COLUMN IF NOT EXISTS session_id VARCHAR(36);
ALTER TABLE sync_data ADD COLUMN IF NOT EXISTS sync_category VARCHAR(20);

-- 为accounts表添加分类相关字段
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS last_classified_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS last_classification_batch_id VARCHAR(36);

-- 创建新字段的索引
CREATE INDEX IF NOT EXISTS idx_sync_data_session_id ON sync_data(session_id);
CREATE INDEX IF NOT EXISTS idx_sync_data_sync_category ON sync_data(sync_category);
CREATE INDEX IF NOT EXISTS idx_accounts_last_classified_at ON accounts(last_classified_at);
CREATE INDEX IF NOT EXISTS idx_accounts_last_classification_batch_id ON accounts(last_classification_batch_id);

-- ============================================================================
-- 16. 创建触发器
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
CREATE TRIGGER update_instances_updated_at BEFORE UPDATE ON instances FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_credentials_updated_at BEFORE UPDATE ON credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_account_classifications_updated_at BEFORE UPDATE ON account_classifications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_classification_rules_updated_at BEFORE UPDATE ON classification_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_account_classification_assignments_updated_at BEFORE UPDATE ON account_classification_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sync_sessions_updated_at BEFORE UPDATE ON sync_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_classification_batches_updated_at BEFORE UPDATE ON classification_batches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 17. 插入真实数据（基于现有 SQLite 数据库）
-- ============================================================================

-- 插入用户数据
INSERT INTO users (id, username, password, role, created_at, last_login, is_active) VALUES
(1, 'admin', '$2b$12$DKFZJIArZQ0ASgxpcGyrHeAXYTBS0ThJjewzso1BnQQm7UWdomcAu', 'admin', '2025-09-12 00:25:19.014781', NULL, TRUE),
(2, 'jinxj', '$2b$12$MFRYxABcpq2UCv1aC22KLuZ88TO0ICM53jIunXNz5C.L7IaOm.Ca.', 'user', '2025-09-12 04:55:11.168860', NULL, TRUE)
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
INSERT INTO account_classifications (id, name, description, risk_level, color, priority, is_system, is_active, created_at, updated_at) VALUES
(2, '敏感账户', '可授权特定权限以满足业务需求，同时需严格安全控制', 'high', '#fd7e14', 80, TRUE, TRUE, '2025-09-12 00:44:16.876132', '2025-09-12 05:28:53.681826'),
(4, '风险账户', '可用于删除库和表的操作，需特别监控以防止误删或恶意行为', 'medium', '#bf17fd', 70, TRUE, TRUE, '2025-09-12 00:44:16.876198', '2025-09-12 05:27:36.043494'),
(5, '只读用户', NULL, 'critical', '#69dc38', 50, TRUE, TRUE, '2025-09-12 00:44:16.876219', '2025-09-12 05:29:01.826658'),
(7, '特权账户', '用于具有高级权限的管理员或系统账户，负责管理数据库核心操作', 'critical', '#dc3545', 90, TRUE, TRUE, '2025-09-12 00:44:16.876259', '2025-09-12 05:26:04.919677'),
(8, '普通账户', '用于日常操作的普通用户账户，权限范围有限', 'low', '#3c49fb', 60, TRUE, TRUE, '2025-09-12 00:44:16.876276', '2025-09-12 05:27:45.250653')
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

-- 插入权限配置数据（MySQL）
INSERT INTO permission_configs (db_type, category, permission_name, description, is_active, sort_order) VALUES
-- MySQL 全局权限
('mysql', 'global_privileges', 'ALTER', '修改表结构', TRUE, 1),
('mysql', 'global_privileges', 'ALTER ROUTINE', '修改存储过程和函数', TRUE, 2),
('mysql', 'global_privileges', 'CREATE', '创建数据库和表', TRUE, 3),
('mysql', 'global_privileges', 'CREATE ROUTINE', '创建存储过程和函数', TRUE, 4),
('mysql', 'global_privileges', 'CREATE TEMPORARY TABLES', '创建临时表', TRUE, 5),
('mysql', 'global_privileges', 'CREATE USER', '创建用户权限', TRUE, 6),
('mysql', 'global_privileges', 'CREATE VIEW', '创建视图', TRUE, 7),
('mysql', 'global_privileges', 'DELETE', '删除数据', TRUE, 8),
('mysql', 'global_privileges', 'DROP', '删除数据库和表', TRUE, 9),
('mysql', 'global_privileges', 'EVENT', '创建、修改、删除事件', TRUE, 10),
('mysql', 'global_privileges', 'EXECUTE', '执行存储过程和函数', TRUE, 11),
('mysql', 'global_privileges', 'FILE', '文件操作权限', TRUE, 12),
('mysql', 'global_privileges', 'GRANT OPTION', '授权权限，可以授予其他用户权限', TRUE, 13),
('mysql', 'global_privileges', 'INDEX', '创建和删除索引', TRUE, 14),
('mysql', 'global_privileges', 'INSERT', '插入数据', TRUE, 15),
('mysql', 'global_privileges', 'LOCK TABLES', '锁定表', TRUE, 16),
('mysql', 'global_privileges', 'PROCESS', '查看所有进程', TRUE, 17),
('mysql', 'global_privileges', 'REFERENCES', '引用权限', TRUE, 18),
('mysql', 'global_privileges', 'RELOAD', '重载权限表', TRUE, 19),
('mysql', 'global_privileges', 'REPLICATION CLIENT', '复制客户端权限', TRUE, 20),
('mysql', 'global_privileges', 'REPLICATION SLAVE', '复制从库权限', TRUE, 21),
('mysql', 'global_privileges', 'SELECT', '查询数据', TRUE, 22),
('mysql', 'global_privileges', 'SHOW DATABASES', '显示所有数据库', TRUE, 23),
('mysql', 'global_privileges', 'SHOW VIEW', '显示视图', TRUE, 24),
('mysql', 'global_privileges', 'SHUTDOWN', '关闭MySQL服务器', TRUE, 25),
('mysql', 'global_privileges', 'SUPER', '超级权限，可以执行任何操作', TRUE, 26),
('mysql', 'global_privileges', 'TRIGGER', '创建和删除触发器', TRUE, 27),
('mysql', 'global_privileges', 'UPDATE', '更新数据', TRUE, 28),
('mysql', 'global_privileges', 'USAGE', '无权限，仅用于连接', TRUE, 29),
-- MySQL 数据库权限
('mysql', 'database_privileges', 'CREATE', '创建数据库和表', TRUE, 1),
('mysql', 'database_privileges', 'DROP', '删除数据库和表', TRUE, 2),
('mysql', 'database_privileges', 'ALTER', '修改数据库和表结构', TRUE, 3),
('mysql', 'database_privileges', 'INDEX', '创建和删除索引', TRUE, 4),
('mysql', 'database_privileges', 'INSERT', '插入数据', TRUE, 5),
('mysql', 'database_privileges', 'UPDATE', '更新数据', TRUE, 6),
('mysql', 'database_privileges', 'DELETE', '删除数据', TRUE, 7),
('mysql', 'database_privileges', 'SELECT', '查询数据', TRUE, 8),
('mysql', 'database_privileges', 'CREATE TEMPORARY TABLES', '创建临时表', TRUE, 9),
('mysql', 'database_privileges', 'LOCK TABLES', '锁定表', TRUE, 10),
('mysql', 'database_privileges', 'EXECUTE', '执行存储过程和函数', TRUE, 11),
('mysql', 'database_privileges', 'CREATE VIEW', '创建视图', TRUE, 12),
('mysql', 'database_privileges', 'SHOW VIEW', '显示视图', TRUE, 13),
('mysql', 'database_privileges', 'CREATE ROUTINE', '创建存储过程和函数', TRUE, 14),
('mysql', 'database_privileges', 'ALTER ROUTINE', '修改存储过程和函数', TRUE, 15),
('mysql', 'database_privileges', 'EVENT', '创建、修改、删除事件', TRUE, 16),
('mysql', 'database_privileges', 'TRIGGER', '创建和删除触发器', TRUE, 17)
ON CONFLICT (db_type, category, permission_name) DO NOTHING;

-- 插入权限配置数据（PostgreSQL）
INSERT INTO permission_configs (db_type, category, permission_name, description, is_active, sort_order) VALUES
-- PostgreSQL 数据库权限
('postgresql', 'database_privileges', 'CONNECT', '连接数据库权限', TRUE, 1),
('postgresql', 'database_privileges', 'CREATE', '创建对象权限', TRUE, 2),
('postgresql', 'database_privileges', 'TEMPORARY', '创建临时表权限', TRUE, 3),
('postgresql', 'database_privileges', 'TEMP', '创建临时表权限（别名）', TRUE, 4),
-- PostgreSQL 预定义角色
('postgresql', 'predefined_roles', 'SUPERUSER', '超级用户角色，拥有所有权限', TRUE, 1),
('postgresql', 'predefined_roles', 'CREATEDB', '创建数据库角色', TRUE, 2),
('postgresql', 'predefined_roles', 'CREATEROLE', '创建角色角色', TRUE, 3),
('postgresql', 'predefined_roles', 'INHERIT', '继承权限角色', TRUE, 4),
('postgresql', 'predefined_roles', 'LOGIN', '登录角色', TRUE, 5),
('postgresql', 'predefined_roles', 'REPLICATION', '复制角色', TRUE, 6),
('postgresql', 'predefined_roles', 'BYPASSRLS', '绕过行级安全角色', TRUE, 7),
('postgresql', 'predefined_roles', 'CONNECTION LIMIT', '连接限制角色', TRUE, 8),
('postgresql', 'predefined_roles', 'PASSWORD', '密码角色', TRUE, 9),
('postgresql', 'predefined_roles', 'VALID UNTIL', '有效期角色', TRUE, 10),
-- PostgreSQL 表空间权限
('postgresql', 'tablespace_privileges', 'CREATE', '创建表空间权限', TRUE, 1),
('postgresql', 'tablespace_privileges', 'USAGE', '使用表空间权限', TRUE, 2)
ON CONFLICT (db_type, category, permission_name) DO NOTHING;

-- 插入权限配置数据（SQL Server）
INSERT INTO permission_configs (db_type, category, permission_name, description, is_active, sort_order) VALUES
-- SQL Server 数据库权限
('sqlserver', 'database_privileges', 'SELECT', '查询数据', TRUE, 1),
('sqlserver', 'database_privileges', 'INSERT', '插入数据', TRUE, 2),
('sqlserver', 'database_privileges', 'UPDATE', '更新数据', TRUE, 3),
('sqlserver', 'database_privileges', 'DELETE', '删除数据', TRUE, 4),
('sqlserver', 'database_privileges', 'CREATE', '创建对象', TRUE, 5),
('sqlserver', 'database_privileges', 'ALTER', '修改/删除对象（包含DROP功能）', TRUE, 6),
('sqlserver', 'database_privileges', 'EXECUTE', '执行存储过程', TRUE, 7),
('sqlserver', 'database_privileges', 'CONTROL', '完全控制权限', TRUE, 8),
('sqlserver', 'database_privileges', 'REFERENCES', '引用权限', TRUE, 9),
('sqlserver', 'database_privileges', 'VIEW DEFINITION', '查看定义', TRUE, 10),
('sqlserver', 'database_privileges', 'TAKE OWNERSHIP', '获取所有权', TRUE, 11),
('sqlserver', 'database_privileges', 'IMPERSONATE', '模拟权限', TRUE, 12),
('sqlserver', 'database_privileges', 'CREATE SCHEMA', '创建架构', TRUE, 13),
('sqlserver', 'database_privileges', 'ALTER ANY SCHEMA', '修改任意架构', TRUE, 14),
('sqlserver', 'database_privileges', 'CREATE TABLE', '创建表', TRUE, 15),
('sqlserver', 'database_privileges', 'CREATE VIEW', '创建视图', TRUE, 16),
('sqlserver', 'database_privileges', 'CREATE PROCEDURE', '创建存储过程', TRUE, 17),
('sqlserver', 'database_privileges', 'CREATE FUNCTION', '创建函数', TRUE, 18),
('sqlserver', 'database_privileges', 'CREATE TRIGGER', '创建触发器', TRUE, 19),
-- SQL Server 服务器角色
('sqlserver', 'server_roles', 'sysadmin', '系统管理员', TRUE, 1),
('sqlserver', 'server_roles', 'serveradmin', '服务器管理员', TRUE, 2),
('sqlserver', 'server_roles', 'securityadmin', '安全管理员', TRUE, 3),
('sqlserver', 'server_roles', 'processadmin', '进程管理员', TRUE, 4),
('sqlserver', 'server_roles', 'setupadmin', '设置管理员', TRUE, 5),
('sqlserver', 'server_roles', 'bulkadmin', '批量操作管理员', TRUE, 6),
('sqlserver', 'server_roles', 'diskadmin', '磁盘管理员', TRUE, 7),
('sqlserver', 'server_roles', 'dbcreator', '数据库创建者', TRUE, 8),
('sqlserver', 'server_roles', 'public', '公共角色', TRUE, 9),
-- SQL Server 数据库角色
('sqlserver', 'database_roles', 'db_owner', '数据库所有者', TRUE, 1),
('sqlserver', 'database_roles', 'db_accessadmin', '访问管理员', TRUE, 2),
('sqlserver', 'database_roles', 'db_securityadmin', '安全管理员', TRUE, 3),
('sqlserver', 'database_roles', 'db_ddladmin', 'DDL管理员', TRUE, 4),
('sqlserver', 'database_roles', 'db_backupoperator', '备份操作员', TRUE, 5),
('sqlserver', 'database_roles', 'db_datareader', '数据读取者', TRUE, 6),
('sqlserver', 'database_roles', 'db_datawriter', '数据写入者', TRUE, 7),
('sqlserver', 'database_roles', 'db_denydatareader', '拒绝数据读取', TRUE, 8),
('sqlserver', 'database_roles', 'db_denydatawriter', '拒绝数据写入', TRUE, 9),
-- SQL Server 服务器权限
('sqlserver', 'server_permissions', 'CONTROL SERVER', '控制服务器', TRUE, 1),
('sqlserver', 'server_permissions', 'ALTER ANY LOGIN', '修改任意登录', TRUE, 2),
('sqlserver', 'server_permissions', 'ALTER ANY SERVER ROLE', '修改任意服务器角色', TRUE, 3),
('sqlserver', 'server_permissions', 'CREATE ANY DATABASE', '创建任意数据库', TRUE, 4),
('sqlserver', 'server_permissions', 'ALTER ANY DATABASE', '修改任意数据库', TRUE, 5),
('sqlserver', 'server_permissions', 'VIEW SERVER STATE', '查看服务器状态', TRUE, 6),
('sqlserver', 'server_permissions', 'ALTER SERVER STATE', '修改服务器状态', TRUE, 7),
('sqlserver', 'server_permissions', 'ALTER SETTINGS', '修改设置', TRUE, 8),
('sqlserver', 'server_permissions', 'ALTER TRACE', '修改跟踪', TRUE, 9),
('sqlserver', 'server_permissions', 'AUTHENTICATE SERVER', '服务器身份验证', TRUE, 10),
('sqlserver', 'server_permissions', 'BACKUP DATABASE', '备份数据库', TRUE, 11),
('sqlserver', 'server_permissions', 'BACKUP LOG', '备份日志', TRUE, 12),
('sqlserver', 'server_permissions', 'CHECKPOINT', '检查点', TRUE, 13),
('sqlserver', 'server_permissions', 'CONNECT SQL', '连接SQL', TRUE, 14),
('sqlserver', 'server_permissions', 'SHUTDOWN', '关闭服务器', TRUE, 15),
('sqlserver', 'server_permissions', 'IMPERSONATE ANY LOGIN', '模拟任意登录', TRUE, 16),
('sqlserver', 'server_permissions', 'VIEW ANY DEFINITION', '查看任意定义', TRUE, 17)
ON CONFLICT (db_type, category, permission_name) DO NOTHING;

-- 插入权限配置数据（Oracle）
INSERT INTO permission_configs (db_type, category, permission_name, description, is_active, sort_order) VALUES
-- Oracle 系统权限
('oracle', 'system_privileges', 'CREATE SESSION', '创建会话权限', TRUE, 1),
('oracle', 'system_privileges', 'CREATE USER', '创建用户权限', TRUE, 2),
('oracle', 'system_privileges', 'ALTER USER', '修改用户权限', TRUE, 3),
('oracle', 'system_privileges', 'DROP USER', '删除用户权限', TRUE, 4),
('oracle', 'system_privileges', 'CREATE ROLE', '创建角色权限', TRUE, 5),
('oracle', 'system_privileges', 'ALTER ROLE', '修改角色权限', TRUE, 6),
('oracle', 'system_privileges', 'DROP ROLE', '删除角色权限', TRUE, 7),
('oracle', 'system_privileges', 'GRANT ANY PRIVILEGE', '授予任意权限', TRUE, 8),
('oracle', 'system_privileges', 'GRANT ANY ROLE', '授予任意角色', TRUE, 9),
('oracle', 'system_privileges', 'CREATE TABLE', '创建表权限', TRUE, 10),
('oracle', 'system_privileges', 'CREATE ANY TABLE', '创建任意表权限', TRUE, 11),
('oracle', 'system_privileges', 'ALTER ANY TABLE', '修改任意表权限', TRUE, 12),
('oracle', 'system_privileges', 'DROP ANY TABLE', '删除任意表权限', TRUE, 13),
('oracle', 'system_privileges', 'SELECT ANY TABLE', '查询任意表权限', TRUE, 14),
('oracle', 'system_privileges', 'INSERT ANY TABLE', '插入任意表权限', TRUE, 15),
('oracle', 'system_privileges', 'UPDATE ANY TABLE', '更新任意表权限', TRUE, 16),
('oracle', 'system_privileges', 'DELETE ANY TABLE', '删除任意表权限', TRUE, 17),
('oracle', 'system_privileges', 'CREATE INDEX', '创建索引权限', TRUE, 18),
('oracle', 'system_privileges', 'CREATE ANY INDEX', '创建任意索引权限', TRUE, 19),
('oracle', 'system_privileges', 'ALTER ANY INDEX', '修改任意索引权限', TRUE, 20),
('oracle', 'system_privileges', 'DROP ANY INDEX', '删除任意索引权限', TRUE, 21),
('oracle', 'system_privileges', 'CREATE PROCEDURE', '创建存储过程权限', TRUE, 22),
('oracle', 'system_privileges', 'CREATE ANY PROCEDURE', '创建任意存储过程权限', TRUE, 23),
('oracle', 'system_privileges', 'ALTER ANY PROCEDURE', '修改任意存储过程权限', TRUE, 24),
('oracle', 'system_privileges', 'DROP ANY PROCEDURE', '删除任意存储过程权限', TRUE, 25),
('oracle', 'system_privileges', 'EXECUTE ANY PROCEDURE', '执行任意存储过程权限', TRUE, 26),
('oracle', 'system_privileges', 'CREATE SEQUENCE', '创建序列权限', TRUE, 27),
('oracle', 'system_privileges', 'CREATE ANY SEQUENCE', '创建任意序列权限', TRUE, 28),
('oracle', 'system_privileges', 'ALTER ANY SEQUENCE', '修改任意序列权限', TRUE, 29),
('oracle', 'system_privileges', 'DROP ANY SEQUENCE', '删除任意序列权限', TRUE, 30),
('oracle', 'system_privileges', 'SELECT ANY SEQUENCE', '查询任意序列权限', TRUE, 31),
('oracle', 'system_privileges', 'CREATE VIEW', '创建视图权限', TRUE, 32),
('oracle', 'system_privileges', 'CREATE ANY VIEW', '创建任意视图权限', TRUE, 33),
('oracle', 'system_privileges', 'DROP ANY VIEW', '删除任意视图权限', TRUE, 34),
('oracle', 'system_privileges', 'CREATE TRIGGER', '创建触发器权限', TRUE, 35),
('oracle', 'system_privileges', 'CREATE ANY TRIGGER', '创建任意触发器权限', TRUE, 36),
('oracle', 'system_privileges', 'ALTER ANY TRIGGER', '修改任意触发器权限', TRUE, 37),
('oracle', 'system_privileges', 'DROP ANY TRIGGER', '删除任意触发器权限', TRUE, 38),
('oracle', 'system_privileges', 'CREATE TABLESPACE', '创建表空间权限', TRUE, 39),
('oracle', 'system_privileges', 'ALTER TABLESPACE', '修改表空间权限', TRUE, 40),
('oracle', 'system_privileges', 'DROP TABLESPACE', '删除表空间权限', TRUE, 41),
('oracle', 'system_privileges', 'UNLIMITED TABLESPACE', '无限制表空间权限', TRUE, 42),
('oracle', 'system_privileges', 'CREATE DATABASE LINK', '创建数据库链接权限', TRUE, 43),
('oracle', 'system_privileges', 'CREATE PUBLIC DATABASE LINK', '创建公共数据库链接权限', TRUE, 44),
('oracle', 'system_privileges', 'DROP PUBLIC DATABASE LINK', '删除公共数据库链接权限', TRUE, 45),
('oracle', 'system_privileges', 'CREATE SYNONYM', '创建同义词权限', TRUE, 46),
('oracle', 'system_privileges', 'CREATE ANY SYNONYM', '创建任意同义词权限', TRUE, 47),
('oracle', 'system_privileges', 'CREATE PUBLIC SYNONYM', '创建公共同义词权限', TRUE, 48),
('oracle', 'system_privileges', 'DROP ANY SYNONYM', '删除任意同义词权限', TRUE, 49),
('oracle', 'system_privileges', 'DROP PUBLIC SYNONYM', '删除公共同义词权限', TRUE, 50),
('oracle', 'system_privileges', 'AUDIT SYSTEM', '系统审计权限', TRUE, 51),
('oracle', 'system_privileges', 'AUDIT ANY', '任意审计权限', TRUE, 52),
('oracle', 'system_privileges', 'EXEMPT ACCESS POLICY', '豁免访问策略权限', TRUE, 53),
('oracle', 'system_privileges', 'EXEMPT REDACTION POLICY', '豁免数据脱敏策略权限', TRUE, 54),
('oracle', 'system_privileges', 'SYSDBA', '系统数据库管理员权限', TRUE, 55),
('oracle', 'system_privileges', 'SYSOPER', '系统操作员权限', TRUE, 56),
-- Oracle 预定义角色
('oracle', 'roles', 'CONNECT', '连接角色，基本连接权限', TRUE, 1),
('oracle', 'roles', 'RESOURCE', '资源角色，创建对象权限', TRUE, 2),
('oracle', 'roles', 'DBA', '数据库管理员角色，所有系统权限', TRUE, 3),
('oracle', 'roles', 'EXP_FULL_DATABASE', '导出完整数据库角色', TRUE, 4),
('oracle', 'roles', 'IMP_FULL_DATABASE', '导入完整数据库角色', TRUE, 5),
('oracle', 'roles', 'RECOVERY_CATALOG_OWNER', '恢复目录所有者角色', TRUE, 6),
('oracle', 'roles', 'AUDIT_ADMIN', '审计管理员角色', TRUE, 7),
('oracle', 'roles', 'AUDIT_VIEWER', '审计查看者角色', TRUE, 8),
('oracle', 'roles', 'AUTHENTICATEDUSER', '认证用户角色', TRUE, 9),
('oracle', 'roles', 'AQ_ADMINISTRATOR_ROLE', '高级队列管理员角色', TRUE, 10),
('oracle', 'roles', 'AQ_USER_ROLE', '高级队列用户角色', TRUE, 11),
('oracle', 'roles', 'CONNECT_ROLE', '连接角色（新版本）', TRUE, 12),
('oracle', 'roles', 'RESOURCE_ROLE', '资源角色（新版本）', TRUE, 13),
('oracle', 'roles', 'SCHEDULER_ADMIN', '调度器管理员角色', TRUE, 14),
('oracle', 'roles', 'HS_ADMIN_ROLE', '异构服务管理员角色', TRUE, 15),
('oracle', 'roles', 'GATHER_SYSTEM_STATISTICS', '收集系统统计信息角色', TRUE, 16),
('oracle', 'roles', 'LOGSTDBY_ADMINISTRATOR', '逻辑备用数据库管理员角色', TRUE, 17),
('oracle', 'roles', 'DBFS_ROLE', '数据库文件系统角色', TRUE, 18),
('oracle', 'roles', 'XDBADMIN', 'XML数据库管理员角色', TRUE, 19),
('oracle', 'roles', 'XDBWEBSERVICES', 'XML数据库Web服务角色', TRUE, 20),
-- Oracle 表空间权限
('oracle', 'tablespace_privileges', 'CREATE TABLESPACE', '创建表空间权限', TRUE, 1),
('oracle', 'tablespace_privileges', 'ALTER TABLESPACE', '修改表空间权限', TRUE, 2),
('oracle', 'tablespace_privileges', 'DROP TABLESPACE', '删除表空间权限', TRUE, 3),
('oracle', 'tablespace_privileges', 'MANAGE TABLESPACE', '管理表空间权限', TRUE, 4),
('oracle', 'tablespace_privileges', 'UNLIMITED TABLESPACE', '无限制表空间权限', TRUE, 5),
('oracle', 'tablespace_privileges', 'CREATE ANY TABLESPACE', '创建任意表空间权限', TRUE, 6),
('oracle', 'tablespace_privileges', 'ALTER ANY TABLESPACE', '修改任意表空间权限', TRUE, 7),
('oracle', 'tablespace_privileges', 'DROP ANY TABLESPACE', '删除任意表空间权限', TRUE, 8),
('oracle', 'tablespace_privileges', 'MANAGE ANY TABLESPACE', '管理任意表空间权限', TRUE, 9),
('oracle', 'tablespace_privileges', 'SELECT ANY TABLESPACE', '查询任意表空间权限', TRUE, 10),
-- Oracle 表空间配额
('oracle', 'tablespace_quotas', 'UNLIMITED', '无限制表空间配额', TRUE, 1),
('oracle', 'tablespace_quotas', 'DEFAULT', '默认表空间配额', TRUE, 2),
('oracle', 'tablespace_quotas', 'QUOTA', '指定大小表空间配额', TRUE, 3),
('oracle', 'tablespace_quotas', 'NO QUOTA', '无表空间配额', TRUE, 4),
('oracle', 'tablespace_quotas', 'QUOTA 1M', '1MB表空间配额', TRUE, 5),
('oracle', 'tablespace_quotas', 'QUOTA 10M', '10MB表空间配额', TRUE, 6),
('oracle', 'tablespace_quotas', 'QUOTA 100M', '100MB表空间配额', TRUE, 7),
('oracle', 'tablespace_quotas', 'QUOTA 1G', '1GB表空间配额', TRUE, 8),
('oracle', 'tablespace_quotas', 'QUOTA 10G', '10GB表空间配额', TRUE, 9),
('oracle', 'tablespace_quotas', 'QUOTA 100G', '100GB表空间配额', TRUE, 10),
('oracle', 'tablespace_quotas', 'QUOTA 1T', '1TB表空间配额', TRUE, 11),
('oracle', 'tablespace_quotas', 'QUOTA 10T', '10TB表空间配额', TRUE, 12),
('oracle', 'tablespace_quotas', 'QUOTA 100T', '100TB表空间配额', TRUE, 13),
('oracle', 'tablespace_quotas', 'QUOTA 1P', '1PB表空间配额', TRUE, 14),
('oracle', 'tablespace_quotas', 'QUOTA 10P', '10PB表空间配额', TRUE, 15),
('oracle', 'tablespace_quotas', 'QUOTA 100P', '100PB表空间配额', TRUE, 16),
('oracle', 'tablespace_quotas', 'QUOTA 1E', '1EB表空间配额', TRUE, 17),
('oracle', 'tablespace_quotas', 'QUOTA 10E', '10EB表空间配额', TRUE, 18),
('oracle', 'tablespace_quotas', 'QUOTA 100E', '100EB表空间配额', TRUE, 19),
('oracle', 'tablespace_quotas', 'QUOTA 1Z', '1ZB表空间配额', TRUE, 20),
('oracle', 'tablespace_quotas', 'QUOTA 10Z', '10ZB表空间配额', TRUE, 21),
('oracle', 'tablespace_quotas', 'QUOTA 100Z', '100ZB表空间配额', TRUE, 22),
('oracle', 'tablespace_quotas', 'QUOTA 1Y', '1YB表空间配额', TRUE, 23),
('oracle', 'tablespace_quotas', 'QUOTA 10Y', '10YB表空间配额', TRUE, 24),
('oracle', 'tablespace_quotas', 'QUOTA 100Y', '100YB表空间配额', TRUE, 25)
ON CONFLICT (db_type, category, permission_name) DO NOTHING;

-- 重置序列
SELECT setval('permission_configs_id_seq', (SELECT MAX(id) FROM permission_configs));

-- 插入任务数据
INSERT INTO tasks (id, name, task_type, db_type, schedule, description, python_code, config, is_active, is_builtin, last_run, last_run_at, last_status, last_message, run_count, success_count, created_at, updated_at) VALUES
(1, 'account_sync', 'sync_accounts', 'mysql', '*/5 * * * *', '测试', '# 账户同步任务 - MySQL
# 此任务将使用统一的AccountSyncService进行账户同步
# 无需手动编写代码，系统会自动调用相应的服务

def sync_mysql_accounts(instance, config):
    """同步MySQL数据库账户信息 - 使用统一服务"""
    from app.services.account_sync_service import account_sync_service

    # 调用统一的账户同步服务
    result = account_sync_service.sync_accounts(instance, sync_type='task')
    return result', '{}', TRUE, FALSE, NULL, NULL, NULL, NULL, 0, 0, '2025-09-12 01:20:05.772007', '2025-09-12 01:20:05.772013')
ON CONFLICT (id) DO NOTHING;

-- 重置序列
SELECT setval('tasks_id_seq', (SELECT MAX(id) FROM tasks));

-- ============================================================================
-- 13. 创建触发器函数（用于自动更新 updated_at 字段）
-- ============================================================================

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为相关表创建更新时间触发器
CREATE TRIGGER update_database_type_configs_updated_at BEFORE UPDATE ON database_type_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_credentials_updated_at BEFORE UPDATE ON credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_instances_updated_at BEFORE UPDATE ON instances FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_accounts_updated_at BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_account_classifications_updated_at BEFORE UPDATE ON account_classifications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_classification_rules_updated_at BEFORE UPDATE ON classification_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_account_classification_assignments_updated_at BEFORE UPDATE ON account_classification_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_permission_configs_updated_at BEFORE UPDATE ON permission_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 14. 创建视图（用于统计和报表）
-- ============================================================================

-- 账户统计视图
CREATE OR REPLACE VIEW account_stats AS
SELECT
    i.db_type,
    i.environment,
    COUNT(a.id) as total_accounts,
    COUNT(CASE WHEN a.is_superuser THEN 1 END) as superuser_count,
    COUNT(CASE WHEN a.is_locked THEN 1 END) as locked_count,
    COUNT(CASE WHEN a.password_expired THEN 1 END) as expired_count
FROM instances i
LEFT JOIN accounts a ON i.id = a.instance_id AND a.is_active = TRUE
WHERE i.is_active = TRUE AND i.deleted_at IS NULL
GROUP BY i.db_type, i.environment;

-- 同步统计视图
CREATE OR REPLACE VIEW sync_stats AS
SELECT
    sync_type,
    status,
    COUNT(*) as count,
    MAX(sync_time) as last_sync,
    SUM(synced_count) as total_synced
FROM sync_data
GROUP BY sync_type, status;

-- ============================================================================
-- 15. 提交事务
-- ============================================================================

COMMIT;

-- ============================================================================
-- 16. 验证数据
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
SELECT 'Account Classifications', COUNT(*) FROM account_classifications
UNION ALL
SELECT 'Classification Rules', COUNT(*) FROM classification_rules
UNION ALL
SELECT 'Tasks', COUNT(*) FROM tasks;

-- 显示账户统计
SELECT * FROM account_stats;

-- 显示同步统计
SELECT * FROM sync_stats;

-- 脚本执行完成提示
SELECT 'PostgreSQL 初始化脚本执行完成！' as message,
       '鲸落 (TaifishV4) 数据库已准备就绪' as description,
       NOW() as completed_at;
