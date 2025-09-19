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
-- 13. 定时任务调度模块 (APScheduler)
-- ============================================================================

-- APScheduler任务表
CREATE TABLE IF NOT EXISTS apscheduler_jobs (
    id VARCHAR(191) PRIMARY KEY,
    next_run_time DOUBLE PRECISION,
    job_state BYTEA NOT NULL
);

-- APScheduler任务表索引
CREATE INDEX IF NOT EXISTS ix_apscheduler_jobs_next_run_time ON apscheduler_jobs(next_run_time);

-- ============================================================================
-- 14. 全局参数模块
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
-- 15. 创建触发器函数
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
-- 16. 插入初始数据
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

-- 权限配置数据请参考单独的权限配置文件
-- 文件位置: sql/permission_configs.sql
-- 该文件包含从现有数据库导出的完整权限配置数据

-- 注意：权限配置数据已移至单独文件，请执行以下命令加载：
-- \i sql/permission_configs.sql

-- 插入标签管理数据
INSERT INTO tags (name, display_name, category, color, description, sort_order, is_active, created_at, updated_at) VALUES
-- 地区标签
('beijing', '北京', 'location', 'primary', '北京地区', 1, TRUE, NOW(), NOW()),
('shanghai', '上海', 'location', 'success', '上海地区', 2, TRUE, NOW(), NOW()),
('guangzhou', '广州', 'location', 'info', '广州地区', 3, TRUE, NOW(), NOW()),
('shenzhen', '深圳', 'location', 'warning', '深圳地区', 4, TRUE, NOW(), NOW()),
('hangzhou', '杭州', 'location', 'danger', '杭州地区', 5, TRUE, NOW(), NOW()),
('nanjing', '南京', 'location', 'secondary', '南京地区', 6, TRUE, NOW(), NOW()),
('wuhan', '武汉', 'location', 'dark', '武汉地区', 7, TRUE, NOW(), NOW()),
('chengdu', '成都', 'location', 'light', '成都地区', 8, TRUE, NOW(), NOW()),

-- 公司类型标签
('tech_company', '科技公司', 'company_type', 'primary', '科技类公司', 1, TRUE, NOW(), NOW()),
('financial', '金融机构', 'company_type', 'success', '银行、证券、保险等金融机构', 2, TRUE, NOW(), NOW()),
('manufacturing', '制造业', 'company_type', 'info', '制造业企业', 3, TRUE, NOW(), NOW()),
('retail', '零售业', 'company_type', 'warning', '零售行业', 4, TRUE, NOW(), NOW()),
('healthcare', '医疗健康', 'company_type', 'danger', '医疗健康行业', 5, TRUE, NOW(), NOW()),
('education', '教育培训', 'company_type', 'secondary', '教育培训机构', 6, TRUE, NOW(), NOW()),
('government', '政府机构', 'company_type', 'dark', '政府机关', 7, TRUE, NOW(), NOW()),
('nonprofit', '非营利组织', 'company_type', 'light', '非营利性组织', 8, TRUE, NOW(), NOW()),

-- 环境标签
('production', '生产环境', 'environment', 'danger', '生产环境数据库', 1, TRUE, NOW(), NOW()),
('staging', '预发布环境', 'environment', 'warning', '预发布环境数据库', 2, TRUE, NOW(), NOW()),
('testing', '测试环境', 'environment', 'info', '测试环境数据库', 3, TRUE, NOW(), NOW()),
('development', '开发环境', 'environment', 'success', '开发环境数据库', 4, TRUE, NOW(), NOW()),
('demo', '演示环境', 'environment', 'secondary', '演示环境数据库', 5, TRUE, NOW(), NOW()),

-- 部门标签
('it_department', 'IT部门', 'department', 'primary', '信息技术部门', 1, TRUE, NOW(), NOW()),
('finance_department', '财务部门', 'department', 'success', '财务部门', 2, TRUE, NOW(), NOW()),
('hr_department', '人力资源', 'department', 'info', '人力资源部门', 3, TRUE, NOW(), NOW()),
('marketing_department', '市场部门', 'department', 'warning', '市场营销部门', 4, TRUE, NOW(), NOW()),
('sales_department', '销售部门', 'department', 'danger', '销售部门', 5, TRUE, NOW(), NOW()),
('operations_department', '运营部门', 'department', 'secondary', '运营部门', 6, TRUE, NOW(), NOW()),

-- 项目标签
('core_system', '核心系统', 'project', 'primary', '核心业务系统', 1, TRUE, NOW(), NOW()),
('data_warehouse', '数据仓库', 'project', 'success', '数据仓库项目', 2, TRUE, NOW(), NOW()),
('analytics', '数据分析', 'project', 'info', '数据分析项目', 3, TRUE, NOW(), NOW()),
('mobile_app', '移动应用', 'project', 'warning', '移动应用项目', 4, TRUE, NOW(), NOW()),
('web_portal', 'Web门户', 'project', 'danger', 'Web门户项目', 5, TRUE, NOW(), NOW()),
('api_service', 'API服务', 'project', 'secondary', 'API服务项目', 6, TRUE, NOW(), NOW()),

-- 其他标签
('high_priority', '高优先级', 'other', 'danger', '高优先级数据库', 1, TRUE, NOW(), NOW()),
('backup_required', '需要备份', 'other', 'warning', '需要定期备份的数据库', 2, TRUE, NOW(), NOW()),
('monitoring', '监控中', 'other', 'info', '正在监控的数据库', 3, TRUE, NOW(), NOW()),
('maintenance', '维护中', 'other', 'secondary', '正在维护的数据库', 4, TRUE, NOW(), NOW()),
('deprecated', '已废弃', 'other', 'dark', '已废弃的数据库', 5, TRUE, NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

-- 插入全局参数数据
INSERT INTO global_params (key, value, description, param_type, created_at, updated_at) VALUES
('system_name', '鲸落数据库管理系统', '系统名称', 'string', NOW(), NOW()),
('system_version', 'v4.0.0', '系统版本', 'string', NOW(), NOW()),
('default_timezone', 'Asia/Shanghai', '默认时区', 'string', NOW(), NOW()),
('max_login_attempts', '5', '最大登录尝试次数', 'integer', NOW(), NOW()),
('session_timeout', '3600', '会话超时时间（秒）', 'integer', NOW(), NOW()),
('password_min_length', '8', '密码最小长度', 'integer', NOW(), NOW()),
('password_require_special', 'true', '密码是否需要特殊字符', 'boolean', NOW(), NOW()),
('account_sync_interval', '1800', '账户同步间隔（秒）', 'integer', NOW(), NOW()),
('log_retention_days', '30', '日志保留天数', 'integer', NOW(), NOW()),
('backup_retention_days', '7', '备份保留天数', 'integer', NOW(), NOW()),
('max_concurrent_syncs', '5', '最大并发同步数', 'integer', NOW(), NOW()),
('enable_auto_classification', 'true', '是否启用自动分类', 'boolean', NOW(), NOW()),
('classification_confidence_threshold', '0.8', '分类置信度阈值', 'float', NOW(), NOW()),
('enable_email_notifications', 'false', '是否启用邮件通知', 'boolean', NOW(), NOW()),
('smtp_server', '', 'SMTP服务器地址', 'string', NOW(), NOW()),
('smtp_port', '587', 'SMTP端口', 'integer', NOW(), NOW()),
('smtp_username', '', 'SMTP用户名', 'string', NOW(), NOW()),
('smtp_password', '', 'SMTP密码', 'string', NOW(), NOW()),
('notification_email', '', '通知邮箱', 'string', NOW(), NOW()),
('enable_audit_log', 'true', '是否启用审计日志', 'boolean', NOW(), NOW()),
('audit_log_retention_days', '90', '审计日志保留天数', 'integer', NOW(), NOW()),
('enable_performance_monitoring', 'true', '是否启用性能监控', 'boolean', NOW(), NOW()),
('performance_monitoring_interval', '300', '性能监控间隔（秒）', 'integer', NOW(), NOW()),
('enable_security_scan', 'true', '是否启用安全扫描', 'boolean', NOW(), NOW()),
('security_scan_interval', '86400', '安全扫描间隔（秒）', 'integer', NOW(), NOW())
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- 17. 提交事务
-- ============================================================================

COMMIT;

-- ============================================================================
-- 18. 验证数据
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
SELECT 'APScheduler Jobs', COUNT(*) FROM apscheduler_jobs
UNION ALL
SELECT 'Global Params', COUNT(*) FROM global_params;

-- 脚本执行完成提示
SELECT 'PostgreSQL 初始化脚本执行完成！' as message,
       '鲸落 (Whalefall) 数据库已准备就绪' as description,
       NOW() as completed_at;