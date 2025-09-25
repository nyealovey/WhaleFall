-- 数据库大小监控功能 - PostgreSQL 初始化脚本
-- 创建原始数据表和聚合统计表，支持分区表

-- ============================================
-- 1. 创建原始数据表（支持分区）
-- ============================================

-- 主表（分区表）
CREATE TABLE IF NOT EXISTS database_size_stats (
    id BIGSERIAL,
    instance_id INTEGER NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    size_mb BIGINT NOT NULL,
    data_size_mb BIGINT,
    log_size_mb BIGINT,
    collected_date DATE NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, collected_date)
) PARTITION BY RANGE (collected_date);

-- 添加外键约束
ALTER TABLE database_size_stats 
ADD CONSTRAINT fk_database_size_stats_instance_id 
FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE;

-- 添加注释
COMMENT ON TABLE database_size_stats IS '数据库大小统计表（分区表）';
COMMENT ON COLUMN database_size_stats.id IS '主键ID';
COMMENT ON COLUMN database_size_stats.instance_id IS '实例ID';
COMMENT ON COLUMN database_size_stats.database_name IS '数据库名称';
COMMENT ON COLUMN database_size_stats.size_mb IS '数据库总大小（MB）';
COMMENT ON COLUMN database_size_stats.data_size_mb IS '数据部分大小（MB）';
COMMENT ON COLUMN database_size_stats.log_size_mb IS '日志部分大小（MB，SQL Server）';
COMMENT ON COLUMN database_size_stats.collected_date IS '采集日期（用于分区）';
COMMENT ON COLUMN database_size_stats.collected_at IS '采集时间戳';
COMMENT ON COLUMN database_size_stats.created_at IS '记录创建时间';

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_database_size_stats_collected_date 
ON database_size_stats (collected_date);

CREATE INDEX IF NOT EXISTS ix_database_size_stats_instance_date 
ON database_size_stats (instance_id, collected_date);

-- 创建唯一约束（确保每日唯一性）
CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_database_size 
ON database_size_stats (instance_id, database_name, collected_date);

-- ============================================
-- 2. 创建聚合统计表
-- ============================================

CREATE TABLE IF NOT EXISTS database_size_aggregations (
    id BIGSERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    period_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    avg_size_mb BIGINT NOT NULL,
    max_size_mb BIGINT NOT NULL,
    min_size_mb BIGINT NOT NULL,
    data_count INTEGER NOT NULL,
    avg_data_size_mb BIGINT,
    max_data_size_mb BIGINT,
    min_data_size_mb BIGINT,
    avg_log_size_mb BIGINT,
    max_log_size_mb BIGINT,
    min_log_size_mb BIGINT,
    -- 增量/减量统计字段
    size_change_mb BIGINT DEFAULT 0,
    size_change_percent DECIMAL(5,2) DEFAULT 0,
    data_size_change_mb BIGINT DEFAULT 0,
    data_size_change_percent DECIMAL(5,2) DEFAULT 0,
    log_size_change_mb BIGINT DEFAULT 0,
    log_size_change_percent DECIMAL(5,2) DEFAULT 0,
    -- 增长率字段
    growth_rate DECIMAL(5,2) DEFAULT 0,
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 添加外键约束
ALTER TABLE database_size_aggregations 
ADD CONSTRAINT fk_database_size_aggregations_instance_id 
FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE;

-- 添加注释
COMMENT ON TABLE database_size_aggregations IS '数据库大小聚合统计表';
COMMENT ON COLUMN database_size_aggregations.id IS '主键ID';
COMMENT ON COLUMN database_size_aggregations.instance_id IS '实例ID';
COMMENT ON COLUMN database_size_aggregations.database_name IS '数据库名称';
COMMENT ON COLUMN database_size_aggregations.period_type IS '统计周期类型：weekly, monthly, quarterly';
COMMENT ON COLUMN database_size_aggregations.period_start IS '统计周期开始日期';
COMMENT ON COLUMN database_size_aggregations.period_end IS '统计周期结束日期';
COMMENT ON COLUMN database_size_aggregations.avg_size_mb IS '平均大小（MB）';
COMMENT ON COLUMN database_size_aggregations.max_size_mb IS '最大大小（MB）';
COMMENT ON COLUMN database_size_aggregations.min_size_mb IS '最小大小（MB）';
COMMENT ON COLUMN database_size_aggregations.data_count IS '统计的数据点数量';
COMMENT ON COLUMN database_size_aggregations.avg_data_size_mb IS '平均数据大小（MB）';
COMMENT ON COLUMN database_size_aggregations.max_data_size_mb IS '最大数据大小（MB）';
COMMENT ON COLUMN database_size_aggregations.min_data_size_mb IS '最小数据大小（MB）';
COMMENT ON COLUMN database_size_aggregations.avg_log_size_mb IS '平均日志大小（MB）';
COMMENT ON COLUMN database_size_aggregations.max_log_size_mb IS '最大日志大小（MB）';
COMMENT ON COLUMN database_size_aggregations.min_log_size_mb IS '最小日志大小（MB）';
COMMENT ON COLUMN database_size_aggregations.size_change_mb IS '总大小变化量（MB，可为负值）';
COMMENT ON COLUMN database_size_aggregations.size_change_percent IS '总大小变化百分比（%，可为负值）';
COMMENT ON COLUMN database_size_aggregations.data_size_change_mb IS '数据大小变化量（MB，可为负值）';
COMMENT ON COLUMN database_size_aggregations.data_size_change_percent IS '数据大小变化百分比（%，可为负值）';
COMMENT ON COLUMN database_size_aggregations.log_size_change_mb IS '日志大小变化量（MB，可为负值）';
COMMENT ON COLUMN database_size_aggregations.log_size_change_percent IS '日志大小变化百分比（%，可为负值）';
COMMENT ON COLUMN database_size_aggregations.growth_rate IS '增长率（%，可为负值）';
COMMENT ON COLUMN database_size_aggregations.calculated_at IS '计算时间';
COMMENT ON COLUMN database_size_aggregations.created_at IS '记录创建时间';

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_database_size_aggregations_instance_period 
ON database_size_aggregations (instance_id, period_type, period_start);

CREATE INDEX IF NOT EXISTS ix_database_size_aggregations_period_type 
ON database_size_aggregations (period_type, period_start);

-- 创建唯一约束
CREATE UNIQUE INDEX IF NOT EXISTS uq_database_size_aggregation 
ON database_size_aggregations (instance_id, database_name, period_type, period_start);

-- ============================================
-- 3. 创建分区（示例：当前月份和未来3个月）
-- ============================================

-- 获取当前日期
DO $$
DECLARE
    current_date DATE := CURRENT_DATE;
    partition_start DATE;
    partition_end DATE;
    partition_name TEXT;
    i INTEGER;
BEGIN
    -- 创建当前月份和未来3个月的分区
    FOR i IN 0..3 LOOP
        partition_start := DATE_TRUNC('month', current_date) + (i || ' months')::INTERVAL;
        partition_end := partition_start + '1 month'::INTERVAL;
        partition_name := 'database_size_stats_' || TO_CHAR(partition_start, 'YYYY_MM');
        
        -- 创建分区表
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I 
            PARTITION OF database_size_stats
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_start, partition_end
        );
        
        -- 添加注释
        EXECUTE format('
            COMMENT ON TABLE %I IS ''数据库大小统计分区表 - %s''',
            partition_name, TO_CHAR(partition_start, 'YYYY-MM')
        );
        
        RAISE NOTICE 'Created partition: % for period % to %', 
            partition_name, partition_start, partition_end;
    END LOOP;
END $$;

-- ============================================
-- 4. 创建分区管理函数
-- ============================================

-- 创建分区函数
CREATE OR REPLACE FUNCTION create_database_size_partition(partition_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    partition_start DATE;
    partition_end DATE;
BEGIN
    partition_start := DATE_TRUNC('month', partition_date);
    partition_end := partition_start + '1 month'::INTERVAL;
    partition_name := 'database_size_stats_' || TO_CHAR(partition_start, 'YYYY_MM');
    
    -- 检查分区是否已存在
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = partition_name
    ) THEN
        -- 创建分区
        EXECUTE format('
            CREATE TABLE %I 
            PARTITION OF database_size_stats
            FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_start, partition_end
        );
        
        -- 添加注释
        EXECUTE format('
            COMMENT ON TABLE %I IS ''数据库大小统计分区表 - %s''',
            partition_name, TO_CHAR(partition_start, 'YYYY-MM')
        );
        
        RAISE NOTICE 'Created partition: % for period % to %', 
            partition_name, partition_start, partition_end;
    ELSE
        RAISE NOTICE 'Partition % already exists', partition_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 删除分区函数
CREATE OR REPLACE FUNCTION drop_database_size_partition(partition_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    partition_start DATE;
BEGIN
    partition_start := DATE_TRUNC('month', partition_date);
    partition_name := 'database_size_stats_' || TO_CHAR(partition_start, 'YYYY_MM');
    
    -- 检查分区是否存在
    IF EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = partition_name
    ) THEN
        -- 删除分区
        EXECUTE format('DROP TABLE %I', partition_name);
        RAISE NOTICE 'Dropped partition: %', partition_name;
    ELSE
        RAISE NOTICE 'Partition % does not exist', partition_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 清理旧分区函数（保留指定月数）
CREATE OR REPLACE FUNCTION cleanup_old_database_size_partitions(retention_months INTEGER DEFAULT 12)
RETURNS VOID AS $$
DECLARE
    cutoff_date DATE;
    partition_record RECORD;
BEGIN
    cutoff_date := CURRENT_DATE - (retention_months || ' months')::INTERVAL;
    
    -- 查找需要清理的分区
    FOR partition_record IN
        SELECT tablename 
        FROM pg_tables 
        WHERE tablename LIKE 'database_size_stats_%'
        AND tablename ~ '^\d{4}_\d{2}$'
    LOOP
        -- 从表名提取日期
        DECLARE
            year_month TEXT;
            partition_date DATE;
        BEGIN
            year_month := substring(partition_record.tablename from 'database_size_stats_(\d{4}_\d{2})$');
            partition_date := TO_DATE(year_month, 'YYYY_MM');
            
            -- 如果分区日期早于截止日期，则删除
            IF partition_date < cutoff_date THEN
                EXECUTE format('DROP TABLE %I', partition_record.tablename);
                RAISE NOTICE 'Cleaned up old partition: %', partition_record.tablename;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'Error processing partition %: %', partition_record.tablename, SQLERRM;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 5. 创建触发器（自动创建分区）
-- ============================================

-- 创建触发器函数
CREATE OR REPLACE FUNCTION auto_create_database_size_partition()
RETURNS TRIGGER AS $$
DECLARE
    partition_date DATE;
BEGIN
    partition_date := DATE_TRUNC('month', NEW.collected_date);
    
    -- 尝试创建分区（如果不存在）
    PERFORM create_database_size_partition(partition_date);
    
    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to create partition for date %: %', partition_date, SQLERRM;
        RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
DROP TRIGGER IF EXISTS trigger_auto_create_database_size_partition ON database_size_stats;
CREATE TRIGGER trigger_auto_create_database_size_partition
    BEFORE INSERT ON database_size_stats
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_database_size_partition();

-- ============================================
-- 6. 创建视图（便于查询）
-- ============================================

-- 创建最近30天的数据视图
CREATE OR REPLACE VIEW v_database_size_recent AS
SELECT 
    dss.*,
    i.name as instance_name,
    i.db_type,
    i.host,
    i.port
FROM database_size_stats dss
JOIN instances i ON dss.instance_id = i.id
WHERE dss.collected_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY dss.collected_date DESC, dss.instance_id, dss.database_name;

-- 创建统计聚合视图
CREATE OR REPLACE VIEW v_database_size_aggregations_recent AS
SELECT 
    dsa.*,
    i.name as instance_name,
    i.db_type,
    i.host,
    i.port
FROM database_size_aggregations dsa
JOIN instances i ON dsa.instance_id = i.id
WHERE dsa.period_start >= CURRENT_DATE - INTERVAL '12 months'
ORDER BY dsa.period_start DESC, dsa.instance_id, dsa.database_name;

-- ============================================
-- 7. 创建示例数据（可选）
-- ============================================

-- 插入一些示例数据（仅用于测试）
/*
INSERT INTO database_size_stats (instance_id, database_name, size_mb, data_size_mb, log_size_mb, collected_date, collected_at)
SELECT 
    1 as instance_id,
    'test_db_' || generate_series(1, 5) as database_name,
    (random() * 1000 + 100)::BIGINT as size_mb,
    (random() * 800 + 80)::BIGINT as data_size_mb,
    (random() * 200 + 20)::BIGINT as log_size_mb,
    CURRENT_DATE - (random() * 30)::INTEGER as collected_date,
    NOW() - (random() * 30 * 24 * 60 * 60)::INTEGER * INTERVAL '1 second' as collected_at
WHERE EXISTS (SELECT 1 FROM instances WHERE id = 1);
*/

-- ============================================
-- 8. 权限设置
-- ============================================

-- 为应用用户授予权限
-- GRANT SELECT, INSERT, UPDATE, DELETE ON database_size_stats TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON database_size_aggregations TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE database_size_stats_id_seq TO your_app_user;
-- GRANT USAGE, SELECT ON SEQUENCE database_size_aggregations_id_seq TO your_app_user;

-- ============================================
-- 完成
-- ============================================

-- 显示创建结果
SELECT 
    'database_size_stats' as table_name,
    'Partitioned table created' as status
UNION ALL
SELECT 
    'database_size_aggregations' as table_name,
    'Regular table created' as status
UNION ALL
SELECT 
    'Partition management functions' as table_name,
    'Functions created' as status
UNION ALL
SELECT 
    'Auto-partition trigger' as table_name,
    'Trigger created' as status;

-- 显示当前分区
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename LIKE 'database_size_stats_%'
ORDER BY tablename;
