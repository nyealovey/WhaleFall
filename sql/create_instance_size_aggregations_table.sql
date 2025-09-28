-- 创建实例大小聚合统计表
-- 支持分区表，按 period_start 字段按月分区

CREATE TABLE IF NOT EXISTS instance_size_aggregations (
    id BIGSERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    
    -- 统计周期
    period_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- 实例总大小统计
    total_size_mb BIGINT NOT NULL,
    avg_size_mb BIGINT NOT NULL,
    max_size_mb BIGINT NOT NULL,
    min_size_mb BIGINT NOT NULL,
    data_count INTEGER NOT NULL,
    
    -- 数据库数量统计
    database_count INTEGER NOT NULL,
    avg_database_count NUMERIC(10, 2),
    max_database_count INTEGER,
    min_database_count INTEGER,
    
    -- 变化统计
    total_size_change_mb BIGINT,
    total_size_change_percent NUMERIC(10, 2),
    database_count_change INTEGER,
    database_count_change_percent NUMERIC(10, 2),
    
    -- 增长率
    growth_rate NUMERIC(10, 2),
    trend_direction VARCHAR(20),
    
    -- 时间戳
    calculated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_instance_size_aggregations_instance_period 
ON instance_size_aggregations (instance_id, period_type, period_start);

CREATE INDEX IF NOT EXISTS ix_instance_size_aggregations_period_type 
ON instance_size_aggregations (period_type, period_start);

-- 创建唯一约束
ALTER TABLE instance_size_aggregations 
ADD CONSTRAINT uq_instance_size_aggregation 
UNIQUE (instance_id, period_type, period_start);

-- 创建分区表（按月分区）
-- 注意：分区表需要在PostgreSQL中手动创建，这里提供示例
-- 示例：创建2024年的分区
-- CREATE TABLE instance_size_aggregations_2024_01 PARTITION OF instance_size_aggregations
-- FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- 添加注释
COMMENT ON TABLE instance_size_aggregations IS '实例大小聚合统计表（分区表）';
COMMENT ON COLUMN instance_size_aggregations.period_type IS '统计周期类型：daily, weekly, monthly, quarterly';
COMMENT ON COLUMN instance_size_aggregations.period_start IS '统计周期开始日期（用于分区）';
COMMENT ON COLUMN instance_size_aggregations.period_end IS '统计周期结束日期';
COMMENT ON COLUMN instance_size_aggregations.total_size_mb IS '实例总大小（MB）';
COMMENT ON COLUMN instance_size_aggregations.avg_size_mb IS '平均大小（MB）';
COMMENT ON COLUMN instance_size_aggregations.max_size_mb IS '最大大小（MB）';
COMMENT ON COLUMN instance_size_aggregations.min_size_mb IS '最小大小（MB）';
COMMENT ON COLUMN instance_size_aggregations.data_count IS '统计的数据点数量';
COMMENT ON COLUMN instance_size_aggregations.database_count IS '数据库数量';
COMMENT ON COLUMN instance_size_aggregations.avg_database_count IS '平均数据库数量';
COMMENT ON COLUMN instance_size_aggregations.max_database_count IS '最大数据库数量';
COMMENT ON COLUMN instance_size_aggregations.min_database_count IS '最小数据库数量';
COMMENT ON COLUMN instance_size_aggregations.total_size_change_mb IS '总大小变化（MB）';
COMMENT ON COLUMN instance_size_aggregations.total_size_change_percent IS '总大小变化百分比';
COMMENT ON COLUMN instance_size_aggregations.database_count_change IS '数据库数量变化';
COMMENT ON COLUMN instance_size_aggregations.database_count_change_percent IS '数据库数量变化百分比';
COMMENT ON COLUMN instance_size_aggregations.growth_rate IS '增长率（百分比）';
COMMENT ON COLUMN instance_size_aggregations.trend_direction IS '趋势方向：growing, shrinking, stable';
COMMENT ON COLUMN instance_size_aggregations.calculated_at IS '计算时间';
COMMENT ON COLUMN instance_size_aggregations.created_at IS '记录创建时间';
