"""
数据库大小监控功能 - Alembic 迁移脚本
这个脚本可以手动执行，用于创建数据库大小监控相关的表
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'database_size_monitoring'
down_revision = None  # 替换为实际的上一版本
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构"""
    
    # 1. 创建原始数据表（分区表）
    op.create_table(
        'database_size_stats',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('database_name', sa.String(length=255), nullable=False),
        sa.Column('size_mb', sa.BigInteger(), nullable=False),
        sa.Column('data_size_mb', sa.BigInteger(), nullable=True),
        sa.Column('log_size_mb', sa.BigInteger(), nullable=True),
        sa.Column('collected_date', sa.Date(), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', 'collected_date'),
        comment='数据库大小统计表（分区表）'
    )
    
    # 创建索引
    op.create_index('ix_database_size_stats_collected_date', 'database_size_stats', ['collected_date'])
    op.create_index('ix_database_size_stats_instance_date', 'database_size_stats', ['instance_id', 'collected_date'])
    op.create_index('uq_daily_database_size', 'database_size_stats', ['instance_id', 'database_name', 'collected_date'], unique=True)
    
    # 2. 创建聚合统计表
    op.create_table(
        'database_size_aggregations',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('database_name', sa.String(length=255), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('avg_size_mb', sa.BigInteger(), nullable=False),
        sa.Column('max_size_mb', sa.BigInteger(), nullable=False),
        sa.Column('min_size_mb', sa.BigInteger(), nullable=False),
        sa.Column('data_count', sa.Integer(), nullable=False),
        sa.Column('avg_data_size_mb', sa.BigInteger(), nullable=True),
        sa.Column('max_data_size_mb', sa.BigInteger(), nullable=True),
        sa.Column('min_data_size_mb', sa.BigInteger(), nullable=True),
        sa.Column('avg_log_size_mb', sa.BigInteger(), nullable=True),
        sa.Column('max_log_size_mb', sa.BigInteger(), nullable=True),
        sa.Column('min_log_size_mb', sa.BigInteger(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='数据库大小聚合统计表'
    )
    
    # 创建索引
    op.create_index('ix_database_size_aggregations_instance_period', 'database_size_aggregations', ['instance_id', 'period_type', 'period_start'])
    op.create_index('ix_database_size_aggregations_period_type', 'database_size_aggregations', ['period_type', 'period_start'])
    op.create_index('uq_database_size_aggregation', 'database_size_aggregations', ['instance_id', 'database_name', 'period_type', 'period_start'], unique=True)
    
    # 3. 创建分区（需要手动执行 SQL）
    # 注意：Alembic 不直接支持分区表创建，需要在 upgrade() 中执行原始 SQL
    op.execute("""
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
            
            IF NOT EXISTS (
                SELECT 1 FROM pg_tables 
                WHERE tablename = partition_name
            ) THEN
                EXECUTE format('
                    CREATE TABLE %I 
                    PARTITION OF database_size_stats
                    FOR VALUES FROM (%L) TO (%L)',
                    partition_name, partition_start, partition_end
                );
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # 创建当前月份和未来3个月的分区
    op.execute("""
        DO $$
        DECLARE
            current_date DATE := CURRENT_DATE;
            partition_start DATE;
            i INTEGER;
        BEGIN
            FOR i IN 0..3 LOOP
                partition_start := DATE_TRUNC('month', current_date) + (i || ' months')::INTERVAL;
                PERFORM create_database_size_partition(partition_start);
            END LOOP;
        END $$;
    """)


def downgrade():
    """降级数据库结构"""
    
    # 删除表（会自动删除分区）
    op.drop_table('database_size_aggregations')
    op.drop_table('database_size_stats')
    
    # 删除函数
    op.execute("DROP FUNCTION IF EXISTS create_database_size_partition(DATE)")
    op.execute("DROP FUNCTION IF EXISTS drop_database_size_partition(DATE)")
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_database_size_partitions(INTEGER)")
