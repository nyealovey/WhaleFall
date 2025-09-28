# 分区管理功能技术文档

## 1. 功能概述

### 1.1 功能描述
分区管理功能是鲸落系统的数据库优化模块，专门负责PostgreSQL数据库表的分区创建、维护和清理。该功能主要针对数据库大小统计表和聚合表进行分区管理，提高查询性能和数据管理效率。

### 1.2 主要特性
- **自动分区创建**：按月自动创建分区表
- **分区清理**：自动清理过期分区数据
- **分区监控**：监控分区健康状态和性能
- **索引优化**：为分区表创建优化索引
- **数据迁移**：支持分区数据迁移和重组
- **定时任务**：集成到定时任务系统
- **多表支持**：支持多张表的分区管理

### 1.3 技术特点
- 基于PostgreSQL原生分区功能
- 按月分区策略
- 自动索引创建
- 定时任务集成
- 性能监控和优化

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   分区管理层    │    │   数据库层      │    │   监控层        │
│                 │    │                 │    │                 │
│ - 分区服务      │◄──►│ - 统计表分区    │◄──►│ - 性能监控      │
│ - 清理服务      │    │ - 聚合表分区    │    │ - 健康检查      │
│ - 监控服务      │    │ - 索引管理      │    │ - 告警通知      │
│ - 定时任务      │    │ - 数据迁移      │    │ - 统计报告      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **分区管理服务**：核心分区操作逻辑
- **清理服务**：过期分区清理
- **监控服务**：分区状态监控
- **定时任务**：自动化分区管理

## 3. 数据库设计

### 3.1 分区表结构
```sql
-- 统计表分区
CREATE TABLE database_size_stats (
    id SERIAL,
    instance_id INTEGER NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    size_bytes BIGINT NOT NULL,
    collected_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (collected_date);

-- 聚合表分区
CREATE TABLE database_size_aggregations (
    id SERIAL,
    instance_id INTEGER NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    avg_size_bytes BIGINT,
    max_size_bytes BIGINT,
    min_size_bytes BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (period_start);
```

### 3.2 分区创建示例
```sql
-- 创建月度分区
CREATE TABLE database_size_stats_2024_01 
PARTITION OF database_size_stats
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE database_size_aggregations_2024_01 
PARTITION OF database_size_aggregations
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

## 4. 后端实现

### 4.1 分区管理服务
```python
# app/services/partition_management_service.py
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect
from app import db
from app.config import Config

logger = logging.getLogger(__name__)


class PartitionManagementService:
    """PostgreSQL 分区管理服务"""
    
    def __init__(self):
        # 管理两张表的分区
        self.tables = {
            'stats': {
                'table_name': 'database_size_stats',
                'partition_prefix': 'database_size_stats_',
                'partition_column': 'collected_date',
                'display_name': '统计表'
            },
            'aggregations': {
                'table_name': 'database_size_aggregations',
                'partition_prefix': 'database_size_aggregations_',
                'partition_column': 'period_start',
                'display_name': '聚合表'
            }
        }
    
    def create_partition(self, partition_date: date) -> Dict[str, Any]:
        """创建分区"""
        try:
            # 计算分区时间范围
            partition_start = partition_date.replace(day=1)
            if partition_start.month == 12:
                partition_end = partition_start.replace(year=partition_start.year + 1, month=1)
            else:
                partition_end = partition_start.replace(month=partition_start.month + 1)
            
            created_partitions = []
            
            # 为每张表创建分区
            for table_key, table_config in self.tables.items():
                partition_name = f"{table_config['partition_prefix']}{partition_start.strftime('%Y_%m')}"
                
                try:
                    # 检查分区是否已存在
                    if self._partition_exists(partition_name):
                        created_partitions.append({
                            'table': table_key,
                            'table_name': table_config['table_name'],
                            'partition_name': partition_name,
                            'status': 'exists',
                            'display_name': table_config['display_name']
                        })
                        continue
                    
                    # 创建分区
                    create_sql = f"""
                    CREATE TABLE {partition_name} 
                    PARTITION OF {table_config['table_name']}
                    FOR VALUES FROM ('{partition_start}') TO ('{partition_end}');
                    """
                    
                    db.session.execute(text(create_sql))
                    
                    # 创建索引
                    self._create_partition_indexes(partition_name, table_config)
                    
                    # 添加注释
                    comment_sql = f"""
                    COMMENT ON TABLE {partition_name} IS '{table_config['display_name']}分区表 - {partition_start.strftime('%Y-%m')}'
                    """
                    db.session.execute(text(comment_sql))
                    
                    created_partitions.append({
                        'table': table_key,
                        'table_name': table_config['table_name'],
                        'partition_name': partition_name,
                        'status': 'created',
                        'display_name': table_config['display_name']
                    })
                    
                    logger.info(f"成功创建分区: {partition_name}")
                    
                except Exception as e:
                    logger.error(f"创建分区失败 {partition_name}: {str(e)}")
                    created_partitions.append({
                        'table': table_key,
                        'table_name': table_config['table_name'],
                        'partition_name': partition_name,
                        'status': 'error',
                        'error': str(e),
                        'display_name': table_config['display_name']
                    })
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'分区创建完成',
                'partitions': created_partitions,
                'partition_date': partition_start.strftime('%Y-%m')
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建分区失败: {str(e)}")
            return {
                'success': False,
                'message': f'创建分区失败: {str(e)}',
                'partitions': []
            }
    
    def cleanup_old_partitions(self, retention_months: int = 12) -> Dict[str, Any]:
        """清理旧分区"""
        try:
            cutoff_date = date.today() - timedelta(days=retention_months * 30)
            cutoff_start = cutoff_date.replace(day=1)
            
            cleaned_partitions = []
            
            for table_key, table_config in self.tables.items():
                # 查找需要清理的分区
                partitions_to_clean = self._get_partitions_to_clean(
                    table_config['table_name'], 
                    cutoff_start
                )
                
                for partition_name in partitions_to_clean:
                    try:
                        # 删除分区
                        drop_sql = f"DROP TABLE IF EXISTS {partition_name} CASCADE;"
                        db.session.execute(text(drop_sql))
                        
                        cleaned_partitions.append({
                            'table': table_key,
                            'partition_name': partition_name,
                            'status': 'cleaned'
                        })
                        
                        logger.info(f"成功清理分区: {partition_name}")
                        
                    except Exception as e:
                        logger.error(f"清理分区失败 {partition_name}: {str(e)}")
                        cleaned_partitions.append({
                            'table': table_key,
                            'partition_name': partition_name,
                            'status': 'error',
                            'error': str(e)
                        })
            
            db.session.commit()
            
            return {
                'success': True,
                'message': f'分区清理完成',
                'cleaned_partitions': cleaned_partitions,
                'retention_months': retention_months
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"清理分区失败: {str(e)}")
            return {
                'success': False,
                'message': f'清理分区失败: {str(e)}',
                'cleaned_partitions': []
            }
    
    def get_partition_status(self) -> Dict[str, Any]:
        """获取分区状态"""
        try:
            partition_info = {}
            
            for table_key, table_config in self.tables.items():
                partitions = self._get_table_partitions(table_config['table_name'])
                partition_info[table_key] = {
                    'table_name': table_config['table_name'],
                    'display_name': table_config['display_name'],
                    'partitions': partitions,
                    'total_partitions': len(partitions)
                }
            
            return {
                'success': True,
                'partition_info': partition_info
            }
            
        except Exception as e:
            logger.error(f"获取分区状态失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取分区状态失败: {str(e)}',
                'partition_info': {}
            }
    
    def _partition_exists(self, partition_name: str) -> bool:
        """检查分区是否存在"""
        try:
            check_sql = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = :partition_name
            );
            """
            result = db.session.execute(text(check_sql), {'partition_name': partition_name})
            return result.scalar()
        except Exception:
            return False
    
    def _create_partition_indexes(self, partition_name: str, table_config: Dict[str, Any]) -> None:
        """为分区创建索引"""
        try:
            # 基础索引
            indexes = [
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_id ON {partition_name} (instance_id);",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_collected_date ON {partition_name} ({table_config['partition_column']});",
                f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_date ON {partition_name} (instance_id, {table_config['partition_column']});"
            ]
            
            for index_sql in indexes:
                db.session.execute(text(index_sql))
                
        except Exception as e:
            logger.error(f"创建分区索引失败 {partition_name}: {str(e)}")
    
    def _get_partitions_to_clean(self, table_name: str, cutoff_date: date) -> List[str]:
        """获取需要清理的分区列表"""
        try:
            query_sql = """
            SELECT schemaname, tablename 
            FROM pg_tables 
            WHERE tablename LIKE :pattern 
            AND schemaname = 'public'
            ORDER BY tablename;
            """
            
            pattern = f"{table_name}_%"
            result = db.session.execute(text(query_sql), {'pattern': pattern})
            
            partitions_to_clean = []
            for row in result:
                partition_name = row.tablename
                # 从分区名提取日期
                try:
                    date_part = partition_name.split('_')[-2] + '_' + partition_name.split('_')[-1]
                    partition_date = datetime.strptime(date_part, '%Y_%m').date()
                    if partition_date < cutoff_date:
                        partitions_to_clean.append(partition_name)
                except (ValueError, IndexError):
                    continue
            
            return partitions_to_clean
            
        except Exception as e:
            logger.error(f"获取清理分区列表失败: {str(e)}")
            return []
    
    def _get_table_partitions(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的所有分区信息"""
        try:
            query_sql = """
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE tablename LIKE :pattern 
            AND schemaname = 'public'
            ORDER BY tablename;
            """
            
            pattern = f"{table_name}_%"
            result = db.session.execute(text(query_sql), {'pattern': pattern})
            
            partitions = []
            for row in result:
                partitions.append({
                    'name': row.tablename,
                    'schema': row.schemaname,
                    'size': row.size,
                    'size_bytes': row.size_bytes
                })
            
            return partitions
            
        except Exception as e:
            logger.error(f"获取表分区信息失败: {str(e)}")
            return []
```

### 4.2 定时任务集成
```python
# app/tasks/partition_management_tasks.py
from datetime import date, timedelta
from app.services.partition_management_service import PartitionManagementService
from app.utils.structlog_config import log_info, log_error


def create_monthly_partitions():
    """创建月度分区任务"""
    try:
        service = PartitionManagementService()
        
        # 创建下个月的分区
        next_month = date.today().replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        result = service.create_partition(next_month)
        
        if result['success']:
            log_info(
                "月度分区创建成功",
                module="partition_management",
                partition_date=result['partition_date'],
                created_count=len([p for p in result['partitions'] if p['status'] == 'created'])
            )
        else:
            log_error(
                "月度分区创建失败",
                module="partition_management",
                error=result['message']
            )
        
        return result
        
    except Exception as e:
        log_error(f"创建月度分区任务失败: {str(e)}", module="partition_management")
        return {'success': False, 'message': str(e)}


def cleanup_old_partitions():
    """清理旧分区任务"""
    try:
        service = PartitionManagementService()
        
        # 清理12个月前的分区
        result = service.cleanup_old_partitions(retention_months=12)
        
        if result['success']:
            log_info(
                "旧分区清理成功",
                module="partition_management",
                cleaned_count=len(result['cleaned_partitions']),
                retention_months=result['retention_months']
            )
        else:
            log_error(
                "旧分区清理失败",
                module="partition_management",
                error=result['message']
            )
        
        return result
        
    except Exception as e:
        log_error(f"清理旧分区任务失败: {str(e)}", module="partition_management")
        return {'success': False, 'message': str(e)}


def monitor_partition_health():
    """监控分区健康状态"""
    try:
        service = PartitionManagementService()
        result = service.get_partition_status()
        
        if result['success']:
            log_info(
                "分区健康检查完成",
                module="partition_management",
                partition_info=result['partition_info']
            )
        else:
            log_error(
                "分区健康检查失败",
                module="partition_management",
                error=result['message']
            )
        
        return result
        
    except Exception as e:
        log_error(f"分区健康检查任务失败: {str(e)}", module="partition_management")
        return {'success': False, 'message': str(e)}
```

## 5. 配置管理

### 5.1 分区配置
```yaml
# app/config/partition_config.yaml
partition_management:
  # 分区策略
  strategy: "monthly"  # monthly, weekly, daily
  
  # 保留策略
  retention:
    months: 12  # 保留12个月的数据
    
  # 自动创建
  auto_create:
    enabled: true
    advance_months: 1  # 提前1个月创建分区
    
  # 自动清理
  auto_cleanup:
    enabled: true
    schedule: "0 2 * * 0"  # 每周日凌晨2点执行
    
  # 监控配置
  monitoring:
    enabled: true
    check_interval: 3600  # 1小时检查一次
    alert_threshold: 0.8  # 分区使用率告警阈值
```

### 5.2 定时任务配置
```yaml
# app/config/scheduler_tasks.yaml
partition_management:
  create_monthly_partitions:
    func: "app.tasks.partition_management_tasks.create_monthly_partitions"
    trigger: "cron"
    hour: 0
    minute: 0
    day: 1
    description: "每月1号创建下个月的分区"
    
  cleanup_old_partitions:
    func: "app.tasks.partition_management_tasks.cleanup_old_partitions"
    trigger: "cron"
    hour: 2
    minute: 0
    day_of_week: 0
    description: "每周日凌晨2点清理旧分区"
    
  monitor_partition_health:
    func: "app.tasks.partition_management_tasks.monitor_partition_health"
    trigger: "interval"
    minutes: 60
    description: "每小时检查分区健康状态"
```

## 6. 性能优化

### 6.1 分区策略优化
- 按月分区平衡查询性能和管理复杂度
- 根据数据量调整分区粒度
- 考虑查询模式优化分区键

### 6.2 索引优化
- 为每个分区创建必要的索引
- 使用复合索引优化查询
- 定期分析索引使用情况

### 6.3 查询优化
- 利用分区裁剪提高查询性能
- 优化跨分区查询
- 使用并行查询处理大数据量

## 7. 监控和告警

### 7.1 分区监控
- 监控分区数量和大小
- 监控分区创建和清理状态
- 监控查询性能

### 7.2 告警机制
- 分区创建失败告警
- 分区清理失败告警
- 分区使用率过高告警

## 8. 维护和运维

### 8.1 分区维护
- 定期检查分区状态
- 优化分区索引
- 清理无用分区

### 8.2 数据迁移
- 支持分区数据迁移
- 分区重组和合并
- 数据一致性检查

---

**注意**: 本文档描述了分区管理功能的完整技术实现，包括分区创建、清理、监控等各个方面。该功能为鲸落系统提供了高效的数据库分区管理能力，显著提升了大数据量场景下的查询性能。
