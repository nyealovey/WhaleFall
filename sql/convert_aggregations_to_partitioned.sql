-- 将 database_size_aggregations 表转换为分区表
-- 按 period_start 字段按月分区

-- 1. 创建新的分区表结构
CREATE TABLE database_size_aggregations_new (
    LIKE database_size_aggregations INCLUDING ALL
) PARTITION BY RANGE (period_start);

-- 2. 创建现有数据的分区
-- 为每个现有的月份创建分区
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
    min_date DATE;
    max_date DATE;
BEGIN
    -- 获取现有数据的最小和最大日期
    SELECT MIN(period_start), MAX(period_start) 
    INTO min_date, max_date 
    FROM database_size_aggregations;
    
    -- 如果没有数据，创建当前月份的分区
    IF min_date IS NULL THEN
        min_date := DATE_TRUNC('month', CURRENT_DATE);
        max_date := min_date;
    END IF;
    
    -- 确保从月初开始
    min_date := DATE_TRUNC('month', min_date);
    max_date := DATE_TRUNC('month', max_date) + INTERVAL '1 month';
    
    -- 为每个月份创建分区
    start_date := min_date;
    WHILE start_date < max_date LOOP
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'database_size_aggregations_' || TO_CHAR(start_date, 'YYYY_MM');
        
        -- 创建分区
        EXECUTE format('CREATE TABLE %I PARTITION OF database_size_aggregations_new FOR VALUES FROM (%L) TO (%L)',
                      partition_name, start_date, end_date);
        
        -- 创建索引
        EXECUTE format('CREATE INDEX idx_%s_instance_db ON %I (instance_id, database_name)',
                      partition_name, partition_name);
        EXECUTE format('CREATE INDEX idx_%s_period ON %I (period_start, period_end)',
                      partition_name, partition_name);
        EXECUTE format('CREATE INDEX idx_%s_type ON %I (period_type, period_start)',
                      partition_name, partition_name);
        
        start_date := end_date;
    END LOOP;
    
    -- 创建未来3个月的分区
    start_date := DATE_TRUNC('month', CURRENT_DATE);
    FOR i IN 0..2 LOOP
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'database_size_aggregations_' || TO_CHAR(start_date, 'YYYY_MM');
        
        -- 检查分区是否已存在
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = partition_name) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF database_size_aggregations_new FOR VALUES FROM (%L) TO (%L)',
                          partition_name, start_date, end_date);
            
            -- 创建索引
            EXECUTE format('CREATE INDEX idx_%s_instance_db ON %I (instance_id, database_name)',
                          partition_name, partition_name);
            EXECUTE format('CREATE INDEX idx_%s_period ON %I (period_start, period_end)',
                          partition_name, partition_name);
            EXECUTE format('CREATE INDEX idx_%s_type ON %I (period_type, period_start)',
                          partition_name, partition_name);
        END IF;
        
        start_date := end_date;
    END LOOP;
END $$;

-- 3. 迁移数据
INSERT INTO database_size_aggregations_new 
SELECT * FROM database_size_aggregations;

-- 4. 重命名表
DROP TABLE database_size_aggregations CASCADE;
ALTER TABLE database_size_aggregations_new RENAME TO database_size_aggregations;

-- 5. 重新创建外键约束
ALTER TABLE database_size_aggregations 
ADD CONSTRAINT fk_database_size_aggregations_instance_id 
FOREIGN KEY (instance_id) REFERENCES instances(id);

-- 6. 添加注释
COMMENT ON TABLE database_size_aggregations IS '数据库大小聚合统计表（按月分区）';
COMMENT ON COLUMN database_size_aggregations.period_start IS '统计周期开始日期（分区键）';
