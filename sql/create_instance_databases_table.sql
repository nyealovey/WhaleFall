-- 创建实例-数据库关系表
-- 用于维护实例包含哪些数据库，以及数据库的状态变化

CREATE TABLE IF NOT EXISTS instance_databases (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    database_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    first_seen_date DATE NOT NULL DEFAULT CURRENT_DATE,
    last_seen_date DATE NOT NULL DEFAULT CURRENT_DATE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 唯一约束：一个实例中的数据库名称唯一
    UNIQUE(instance_id, database_name)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_instance_databases_instance_id ON instance_databases (instance_id);
CREATE INDEX IF NOT EXISTS ix_instance_databases_database_name ON instance_databases (database_name);
CREATE INDEX IF NOT EXISTS ix_instance_databases_active ON instance_databases (is_active);
CREATE INDEX IF NOT EXISTS ix_instance_databases_last_seen ON instance_databases (last_seen_date);

-- 添加注释
COMMENT ON TABLE instance_databases IS '实例-数据库关系表，维护数据库的存在状态';
COMMENT ON COLUMN instance_databases.instance_id IS '实例ID';
COMMENT ON COLUMN instance_databases.database_name IS '数据库名称';
COMMENT ON COLUMN instance_databases.is_active IS '数据库是否活跃（未删除）';
COMMENT ON COLUMN instance_databases.first_seen_date IS '首次发现日期';
COMMENT ON COLUMN instance_databases.last_seen_date IS '最后发现日期';
COMMENT ON COLUMN instance_databases.deleted_at IS '删除时间';

-- 创建触发器函数：自动更新 last_seen_date
CREATE OR REPLACE FUNCTION update_instance_database_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    -- 当有新的数据库大小数据时，更新 last_seen_date
    UPDATE instance_databases 
    SET last_seen_date = NEW.collected_date,
        updated_at = NOW()
    WHERE instance_id = NEW.instance_id 
    AND database_name = NEW.database_name;
    
    -- 如果数据库不存在，则插入新记录
    IF NOT FOUND THEN
        INSERT INTO instance_databases (instance_id, database_name, first_seen_date, last_seen_date)
        VALUES (NEW.instance_id, NEW.database_name, NEW.collected_date, NEW.collected_date)
        ON CONFLICT (instance_id, database_name) DO UPDATE SET
            last_seen_date = NEW.collected_date,
            is_active = TRUE,
            deleted_at = NULL,
            updated_at = NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
DROP TRIGGER IF EXISTS trg_update_instance_database_last_seen ON database_size_stats;
CREATE TRIGGER trg_update_instance_database_last_seen
    AFTER INSERT ON database_size_stats
    FOR EACH ROW EXECUTE FUNCTION update_instance_database_last_seen();

-- 创建函数：标记数据库为已删除
CREATE OR REPLACE FUNCTION mark_database_as_deleted(
    p_instance_id INTEGER,
    p_database_name VARCHAR(255)
) RETURNS VOID AS $$
BEGIN
    UPDATE instance_databases 
    SET is_active = FALSE,
        deleted_at = NOW(),
        updated_at = NOW()
    WHERE instance_id = p_instance_id 
    AND database_name = p_database_name;
END;
$$ LANGUAGE plpgsql;

-- 创建函数：检测并标记已删除的数据库
CREATE OR REPLACE FUNCTION detect_deleted_databases(p_instance_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    db_record RECORD;
    latest_collection_date DATE;
BEGIN
    -- 获取该实例最新的数据采集日期
    SELECT MAX(collected_date) INTO latest_collection_date
    FROM database_size_stats 
    WHERE instance_id = p_instance_id;
    
    -- 查找在最新采集日期没有数据的活跃数据库
    FOR db_record IN 
        SELECT database_name 
        FROM instance_databases 
        WHERE instance_id = p_instance_id 
        AND is_active = TRUE
        AND database_name NOT IN (
            SELECT DISTINCT database_name 
            FROM database_size_stats 
            WHERE instance_id = p_instance_id 
            AND collected_date = latest_collection_date
        )
    LOOP
        -- 标记为已删除
        PERFORM mark_database_as_deleted(p_instance_id, db_record.database_name);
        deleted_count := deleted_count + 1;
    END LOOP;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
