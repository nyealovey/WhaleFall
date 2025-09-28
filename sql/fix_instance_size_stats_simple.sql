-- 简单修复 instance_size_stats 表的分区问题
-- 确保表存在且为分区表

-- 1. 删除现有表（如果存在）
DROP TABLE IF EXISTS instance_size_stats CASCADE;

-- 2. 创建分区表
CREATE TABLE instance_size_stats (
    id SERIAL,
    instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
    total_size_mb INTEGER NOT NULL DEFAULT 0,
    database_count INTEGER NOT NULL DEFAULT 0,
    collected_date DATE NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, collected_date)
) PARTITION BY RANGE (collected_date);

-- 3. 创建索引
CREATE INDEX IF NOT EXISTS ix_instance_size_stats_instance_id ON instance_size_stats (instance_id);
CREATE INDEX IF NOT EXISTS ix_instance_size_stats_collected_date ON instance_size_stats (collected_date);
CREATE INDEX IF NOT EXISTS ix_instance_size_stats_instance_date ON instance_size_stats (instance_id, collected_date);
CREATE INDEX IF NOT EXISTS ix_instance_size_stats_deleted ON instance_size_stats (is_deleted);
CREATE INDEX IF NOT EXISTS ix_instance_size_stats_total_size ON instance_size_stats (total_size_mb);

-- 4. 创建唯一约束
CREATE UNIQUE INDEX IF NOT EXISTS uq_instance_size_stats_instance_date 
ON instance_size_stats (instance_id, collected_date) 
WHERE is_deleted = FALSE;

-- 5. 添加注释
COMMENT ON TABLE instance_size_stats IS '实例大小统计表（按月分区）';
COMMENT ON COLUMN instance_size_stats.instance_id IS '实例ID';
COMMENT ON COLUMN instance_size_stats.total_size_mb IS '实例总大小（MB）';
COMMENT ON COLUMN instance_size_stats.database_count IS '数据库数量';
COMMENT ON COLUMN instance_size_stats.collected_date IS '采集日期';
COMMENT ON COLUMN instance_size_stats.collected_at IS '采集时间';
COMMENT ON COLUMN instance_size_stats.is_deleted IS '是否已删除';
COMMENT ON COLUMN instance_size_stats.deleted_at IS '删除时间';

-- 6. 创建分区函数
CREATE OR REPLACE FUNCTION create_instance_size_stats_partitions()
RETURNS void AS $$
DECLARE
    current_year INTEGER;
    current_month INTEGER;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
BEGIN
    -- 获取当前年月
    current_year := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month := EXTRACT(MONTH FROM CURRENT_DATE);
    
    -- 创建当前月份的分区
    partition_name := 'instance_size_stats_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := current_year || '-' || LPAD(current_month::TEXT, 2, '0') || '-01';
    end_date := CASE 
        WHEN current_month = 12 THEN (current_year + 1) || '-01-01'
        ELSE current_year || '-' || LPAD((current_month + 1)::TEXT, 2, '0') || '-01'
    END;
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF instance_size_stats FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date);
    
    -- 创建下个月份的分区
    IF current_month = 12 THEN
        current_year := current_year + 1;
        current_month := 1;
    ELSE
        current_month := current_month + 1;
    END IF;
    
    partition_name := 'instance_size_stats_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := current_year || '-' || LPAD(current_month::TEXT, 2, '0') || '-01';
    end_date := CASE 
        WHEN current_month = 12 THEN (current_year + 1) || '-01-01'
        ELSE current_year || '-' || LPAD((current_month + 1)::TEXT, 2, '0') || '-01'
    END;
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF instance_size_stats FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date);
    
    RAISE NOTICE 'Created instance_size_stats partitions for % and %', 
        (current_year || '-' || LPAD((current_month - 1)::TEXT, 2, '0')), 
        (current_year || '-' || LPAD(current_month::TEXT, 2, '0'));
END;
$$ LANGUAGE plpgsql;

-- 7. 执行分区创建
SELECT create_instance_size_stats_partitions();

-- 8. 创建触发器函数，自动创建分区
CREATE OR REPLACE FUNCTION instance_size_stats_partition_trigger()
RETURNS TRIGGER AS $$
DECLARE
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
    year_val INTEGER;
    month_val INTEGER;
BEGIN
    -- 从 collected_date 提取年月
    year_val := EXTRACT(YEAR FROM NEW.collected_date);
    month_val := EXTRACT(MONTH FROM NEW.collected_date);
    
    -- 构建分区名称
    partition_name := 'instance_size_stats_' || year_val || '_' || LPAD(month_val::TEXT, 2, '0');
    
    -- 检查分区是否存在
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = partition_name
    ) THEN
        -- 创建分区
        start_date := year_val || '-' || LPAD(month_val::TEXT, 2, '0') || '-01';
        end_date := CASE 
            WHEN month_val = 12 THEN (year_val + 1) || '-01-01'
            ELSE year_val || '-' || LPAD((month_val + 1)::TEXT, 2, '0') || '-01'
        END;
        
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_stats FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date);
        
        RAISE NOTICE 'Created partition % for date %', partition_name, NEW.collected_date;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 9. 创建触发器
DROP TRIGGER IF EXISTS instance_size_stats_partition_trigger ON instance_size_stats;
CREATE TRIGGER instance_size_stats_partition_trigger
    BEFORE INSERT ON instance_size_stats
    FOR EACH ROW
    EXECUTE FUNCTION instance_size_stats_partition_trigger();

-- 10. 验证表创建成功
SELECT 'instance_size_stats table created successfully' as status;
