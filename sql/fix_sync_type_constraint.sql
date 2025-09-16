-- 修复sync_type约束问题
-- 1. 先备份数据
CREATE TABLE IF NOT EXISTS sync_sessions_backup AS 
SELECT * FROM sync_sessions;

-- 2. 删除旧的CHECK约束（SQLite不支持直接删除约束，需要重建表）
-- 创建临时表
CREATE TABLE sync_sessions_temp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(36) UNIQUE NOT NULL,
    sync_type VARCHAR(20) NOT NULL,
    sync_category VARCHAR(20) NOT NULL DEFAULT 'account',
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    total_instances INTEGER DEFAULT 0,
    successful_instances INTEGER DEFAULT 0,
    failed_instances INTEGER DEFAULT 0,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. 复制数据到临时表
INSERT INTO sync_sessions_temp 
SELECT * FROM sync_sessions;

-- 4. 更新sync_type值
UPDATE sync_sessions_temp 
SET sync_type = CASE 
    WHEN sync_type = 'scheduled' THEN 'scheduled_task'
    WHEN sync_type = 'manual_batch' THEN 'manual_batch'
    ELSE sync_type
END;

-- 5. 删除原表
DROP TABLE sync_sessions;

-- 6. 重新创建表，使用新的约束
CREATE TABLE sync_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(36) UNIQUE NOT NULL,
    sync_type VARCHAR(20) NOT NULL CHECK (sync_type IN ('manual_single', 'manual_batch', 'manual_task', 'scheduled_task')),
    sync_category VARCHAR(20) NOT NULL DEFAULT 'account' CHECK (sync_category IN ('account', 'capacity', 'config', 'other')),
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    total_instances INTEGER DEFAULT 0,
    successful_instances INTEGER DEFAULT 0,
    failed_instances INTEGER DEFAULT 0,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 7. 从临时表复制数据
INSERT INTO sync_sessions 
SELECT * FROM sync_sessions_temp;

-- 8. 删除临时表
DROP TABLE sync_sessions_temp;

-- 9. 验证结果
SELECT '更新后的sync_type值:' as info;
SELECT DISTINCT sync_type FROM sync_sessions;

-- 10. 显示统计
SELECT 
    sync_type,
    COUNT(*) as count
FROM sync_sessions 
GROUP BY sync_type;
