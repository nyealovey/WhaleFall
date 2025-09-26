"""
PostgreSQL 分区管理服务
负责创建、清理和监控数据库大小统计表和聚合表的分区
"""

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
        """
        创建指定日期的分区（同时创建两张表的分区）
        
        Args:
            partition_date: 分区日期
            
        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            # 计算分区的时间范围（按月分区）
            partition_start = partition_date.replace(day=1)
            if partition_start.month == 12:
                partition_end = partition_start.replace(year=partition_start.year + 1, month=1)
            else:
                partition_end = partition_start.replace(month=partition_start.month + 1)
            
            created_partitions = []
            errors = []
            
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
                    error_msg = f"创建 {table_config['display_name']} 分区失败: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            if errors:
                db.session.rollback()
                return {
                    'success': False,
                    'message': f'部分分区创建失败: {"; ".join(errors)}',
                    'created_partitions': created_partitions,
                    'errors': errors
                }
            else:
                db.session.commit()
                return {
                    'success': True,
                    'message': f'成功创建 {len(created_partitions)} 个分区',
                    'created_partitions': created_partitions,
                    'partition_start': partition_start.isoformat(),
                    'partition_end': partition_end.isoformat()
                }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建分区失败: {str(e)}")
            return {
                'success': False,
                'message': f'创建分区失败: {str(e)}'
            }
    
    def create_future_partitions(self, months_ahead: int = 3) -> Dict[str, Any]:
        """
        创建未来几个月的分区
        
        Args:
            months_ahead: 提前创建的月数
            
        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            created_partitions = []
            current_date = date.today()
            
            for i in range(months_ahead):
                target_date = current_date + timedelta(days=30 * i)
                result = self.create_partition(target_date)
                
                if result['success']:
                    created_partitions.extend(result.get('created_partitions', []))
                else:
                    logger.warning(f"创建分区失败: {result['message']}")
            
            return {
                'success': True,
                'message': f'成功创建 {len(created_partitions)} 个未来分区',
                'created_partitions': created_partitions
            }
            
        except Exception as e:
            logger.error(f"创建未来分区失败: {str(e)}")
            return {
                'success': False,
                'message': f'创建未来分区失败: {str(e)}'
            }
    
    def cleanup_old_partitions(self, retention_months: int = 12) -> Dict[str, Any]:
        """
        清理旧分区
        
        Args:
            retention_months: 保留月数
            
        Returns:
            Dict[str, Any]: 清理结果
        """
        try:
            cutoff_date = date.today() - timedelta(days=30 * retention_months)
            cutoff_date = cutoff_date.replace(day=1)  # 月初
            
            dropped_partitions = []
            errors = []
            
            # 为每张表清理旧分区
            for table_key, table_config in self.tables.items():
                partitions_to_drop = self._get_partitions_to_cleanup(cutoff_date, table_config)
                
                for partition_name in partitions_to_drop:
                    try:
                        # 删除分区
                        drop_sql = f"DROP TABLE IF EXISTS {partition_name};"
                        db.session.execute(text(drop_sql))
                        dropped_partitions.append({
                            'table': table_key,
                            'table_name': table_config['table_name'],
                            'partition_name': partition_name,
                            'display_name': table_config['display_name']
                        })
                        logger.info(f"成功删除旧分区: {partition_name}")
                        
                    except Exception as e:
                        error_msg = f"删除 {table_config['display_name']} 分区 {partition_name} 失败: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
            if errors:
                db.session.rollback()
                return {
                    'success': False,
                    'message': f'部分分区清理失败: {"; ".join(errors)}',
                    'dropped_partitions': dropped_partitions,
                    'errors': errors
                }
            else:
                db.session.commit()
                return {
                    'success': True,
                    'message': f'成功清理 {len(dropped_partitions)} 个旧分区',
                    'dropped_partitions': dropped_partitions
                }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"清理旧分区失败: {str(e)}")
            return {
                'success': False,
                'message': f'清理旧分区失败: {str(e)}'
            }
    
    def get_partition_info(self) -> Dict[str, Any]:
        """
        获取分区信息（包含两张表的分区）
        
        Returns:
            Dict[str, Any]: 分区信息
        """
        try:
            all_partitions = []
            total_size_bytes = 0
            total_records = 0
            
            # 获取每张表的分区信息
            for table_key, table_config in self.tables.items():
                partitions = self._get_table_partitions(table_config)
                all_partitions.extend(partitions)
                
                # 计算总大小和记录数
                for partition in partitions:
                    total_size_bytes += partition.get('size_bytes', 0)
                    total_records += partition.get('record_count', 0)
            
            # 按分区名称排序
            all_partitions.sort(key=lambda x: x['name'])
            
            return {
                'success': True,
                'partitions': all_partitions,
                'total_partitions': len(all_partitions),
                'total_size_bytes': total_size_bytes,
                'total_size': self._format_size(total_size_bytes),
                'total_records': total_records,
                'tables': list(self.tables.keys())
            }
            
        except Exception as e:
            logger.error(f"获取分区信息失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取分区信息失败: {str(e)}'
            }
    
    def get_partition_statistics(self) -> Dict[str, Any]:
        """
        获取分区统计信息
        
        Returns:
            Dict[str, Any]: 分区统计
        """
        try:
            partition_info = self.get_partition_info()
            
            if not partition_info['success']:
                return partition_info
            
            return {
                'success': True,
                'total_records': partition_info['total_records'],
                'total_partitions': partition_info['total_partitions'],
                'total_size': partition_info['total_size'],
                'total_size_bytes': partition_info['total_size_bytes'],
                'partitions': partition_info['partitions'],
                'tables': partition_info['tables']
            }
            
        except Exception as e:
            logger.error(f"获取分区统计失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取分区统计失败: {str(e)}'
            }
    
    def _get_table_partitions(self, table_config: Dict[str, str]) -> List[Dict[str, Any]]:
        """获取指定表的分区信息"""
        try:
            # 查询分区信息
            query = """
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE tablename LIKE :pattern
            ORDER BY tablename;
            """
            
            result = db.session.execute(text(query), {
                'pattern': f'{table_config["partition_prefix"]}%'
            }).fetchall()
            
            partitions = []
            for row in result:
                # 从分区名提取日期
                date_str = self._extract_date_from_partition_name(row.tablename, table_config["partition_prefix"])
                
                # 获取记录数
                record_count = self._get_partition_record_count(row.tablename)
                
                # 判断分区状态
                status = self._get_partition_status(date_str)
                
                partitions.append({
                    'name': row.tablename,
                    'table': table_config['table_name'],
                    'display_name': table_config['display_name'],
                    'size': row.size,
                    'size_bytes': row.size_bytes,
                    'record_count': record_count,
                    'date': date_str,
                    'status': status
                })
            
            return partitions
            
        except Exception as e:
            logger.error(f"获取表 {table_config['table_name']} 分区信息失败: {str(e)}")
            return []
    
    def _partition_exists(self, partition_name: str) -> bool:
        """检查分区是否存在"""
        try:
            query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = :partition_name
            );
            """
            result = db.session.execute(text(query), {'partition_name': partition_name}).scalar()
            return bool(result)
        except Exception:
            return False
    
    def _get_partitions_to_cleanup(self, cutoff_date: date, table_config: Dict[str, str]) -> List[str]:
        """获取需要清理的分区列表"""
        try:
            query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE tablename LIKE :pattern
            ORDER BY tablename;
            """
            
            result = db.session.execute(text(query), {
                'pattern': f'{table_config["partition_prefix"]}%'
            }).fetchall()
            
            partitions_to_drop = []
            for row in result:
                # 从分区名提取日期
                date_str = self._extract_date_from_partition_name(row.tablename, table_config["partition_prefix"])
                if date_str:
                    try:
                        partition_date = datetime.strptime(date_str, '%Y/%m/%d').date()
                        if partition_date < cutoff_date:
                            partitions_to_drop.append(row.tablename)
                    except ValueError:
                        continue
            
            return partitions_to_drop
            
        except Exception as e:
            logger.error(f"获取清理分区列表失败: {str(e)}")
            return []
    
    def _extract_date_from_partition_name(self, partition_name: str, prefix: str) -> Optional[str]:
        """从分区名提取日期"""
        try:
            # 移除前缀，获取日期部分 (YYYY_MM)
            date_part = partition_name.replace(prefix, '')
            parts = date_part.split('_')
            if len(parts) >= 2:
                year = parts[0]
                month = parts[1]
                return f"{year}/{month}/01"
        except Exception:
            pass
        return None
    
    def _get_partition_record_count(self, partition_name: str) -> int:
        """获取分区的记录数"""
        try:
            query = f"SELECT COUNT(*) FROM {partition_name};"
            result = db.session.execute(text(query)).scalar()
            return result or 0
        except Exception:
            return 0
    
    def _get_partition_status(self, date_str: Optional[str]) -> str:
        """获取分区状态"""
        if not date_str:
            return 'unknown'
        
        try:
            partition_date = datetime.strptime(date_str, '%Y/%m/%d').date()
            today = date.today()
            current_month = today.replace(day=1)
            
            if partition_date == current_month:
                return 'current'
            elif partition_date < current_month:
                return 'past'
            else:
                return 'future'
        except ValueError:
            return 'unknown'
    
    def _create_partition_indexes(self, partition_name: str, table_config: Dict[str, str]):
        """为分区创建索引"""
        try:
            if table_config['table_name'] == 'database_size_stats':
                # 统计表索引
                indexes = [
                    f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_db ON {partition_name} (instance_id, database_name);",
                    f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_date ON {partition_name} (collected_date);",
                    f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_date ON {partition_name} (instance_id, collected_date);"
                ]
            else:
                # 聚合表索引
                indexes = [
                    f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_instance_db ON {partition_name} (instance_id, database_name);",
                    f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_period ON {partition_name} (period_start, period_end);",
                    f"CREATE INDEX IF NOT EXISTS idx_{partition_name}_type ON {partition_name} (period_type, period_start);"
                ]
            
            for index_sql in indexes:
                db.session.execute(text(index_sql))
            
        except Exception as e:
            logger.error(f"创建分区索引失败: {str(e)}")
            raise
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"
