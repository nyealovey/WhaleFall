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
                'partition_column': 'collected_date'
            },
            'aggregations': {
                'table_name': 'database_size_aggregations',
                'partition_prefix': 'database_size_aggregations_',
                'partition_column': 'period_start'
            }
        }
    
    def create_partition(self, partition_date: date) -> Dict[str, Any]:
        """
        创建指定日期的分区
        
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
            
            partition_name = f"{self.partition_prefix}{partition_start.strftime('%Y_%m')}"
            
            # 检查分区是否已存在
            if self._partition_exists(partition_name):
                return {
                    'success': True,
                    'message': f'分区 {partition_name} 已存在',
                    'partition_name': partition_name,
                    'partition_start': partition_start.isoformat(),
                    'partition_end': partition_end.isoformat()
                }
            
            # 创建分区
            create_sql = f"""
            CREATE TABLE {partition_name} 
            PARTITION OF {self.table_name}
            FOR VALUES FROM ('{partition_start.isoformat()}') TO ('{partition_end.isoformat()}')
            """
            
            db.session.execute(text(create_sql))
            db.session.commit()
            
            # 添加注释
            comment_sql = f"""
            COMMENT ON TABLE {partition_name} IS '数据库大小统计分区表 - {partition_start.strftime('%Y-%m')}'
            """
            db.session.execute(text(comment_sql))
            db.session.commit()
            
            logger.info(f"成功创建分区: {partition_name} ({partition_start} 到 {partition_end})")
            
            return {
                'success': True,
                'message': f'分区 {partition_name} 创建成功',
                'partition_name': partition_name,
                'partition_start': partition_start.isoformat(),
                'partition_end': partition_end.isoformat()
            }
            
        except Exception as e:
            logger.error(f"创建分区失败: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'message': f'创建分区失败: {str(e)}',
                'error': str(e)
            }
    
    def drop_partition(self, partition_date: date) -> Dict[str, Any]:
        """
        删除指定日期的分区
        
        Args:
            partition_date: 分区日期
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        try:
            partition_start = partition_date.replace(day=1)
            partition_name = f"{self.partition_prefix}{partition_start.strftime('%Y_%m')}"
            
            # 检查分区是否存在
            if not self._partition_exists(partition_name):
                return {
                    'success': True,
                    'message': f'分区 {partition_name} 不存在',
                    'partition_name': partition_name
                }
            
            # 删除分区
            drop_sql = f"DROP TABLE {partition_name}"
            db.session.execute(text(drop_sql))
            db.session.commit()
            
            logger.info(f"成功删除分区: {partition_name}")
            
            return {
                'success': True,
                'message': f'分区 {partition_name} 删除成功',
                'partition_name': partition_name
            }
            
        except Exception as e:
            logger.error(f"删除分区失败: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'message': f'删除分区失败: {str(e)}',
                'error': str(e)
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
            cutoff_date = date.today() - timedelta(days=retention_months * 30)
            cleaned_partitions = []
            
            # 获取所有分区
            partitions = self._get_all_partitions()
            
            for partition in partitions:
                partition_name = partition['tablename']
                partition_date = self._extract_partition_date(partition_name)
                
                if partition_date and partition_date < cutoff_date:
                    # 删除旧分区
                    result = self.drop_partition(partition_date)
                    if result['success']:
                        cleaned_partitions.append(partition_name)
            
            logger.info(f"清理了 {len(cleaned_partitions)} 个旧分区")
            
            return {
                'success': True,
                'message': f'清理了 {len(cleaned_partitions)} 个旧分区',
                'cleaned_partitions': cleaned_partitions,
                'retention_months': retention_months
            }
            
        except Exception as e:
            logger.error(f"清理旧分区失败: {str(e)}")
            return {
                'success': False,
                'message': f'清理旧分区失败: {str(e)}',
                'error': str(e)
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
            
            for i in range(months_ahead):
                future_date = date.today() + timedelta(days=i * 30)
                result = self.create_partition(future_date)
                
                if result['success'] and '已存在' not in result['message']:
                    created_partitions.append(result['partition_name'])
            
            logger.info(f"创建了 {len(created_partitions)} 个未来分区")
            
            return {
                'success': True,
                'message': f'创建了 {len(created_partitions)} 个未来分区',
                'created_partitions': created_partitions
            }
            
        except Exception as e:
            logger.error(f"创建未来分区失败: {str(e)}")
            return {
                'success': False,
                'message': f'创建未来分区失败: {str(e)}',
                'error': str(e)
            }
    
    def get_partition_info(self) -> Dict[str, Any]:
        """
        获取分区信息
        
        Returns:
            Dict[str, Any]: 分区信息
        """
        try:
            partitions = self._get_all_partitions()
            partition_info = []
            
            for partition in partitions:
                partition_name = partition['tablename']
                partition_date = self._extract_partition_date(partition_name)
                
                # 获取分区大小
                size_sql = f"""
                SELECT pg_size_pretty(pg_total_relation_size('{partition_name}')) as size,
                       pg_total_relation_size('{partition_name}') as size_bytes
                """
                size_result = db.session.execute(text(size_sql)).fetchone()
                
                # 获取分区记录数
                count_sql = f"SELECT COUNT(*) as count FROM {partition_name}"
                count_result = db.session.execute(text(count_sql)).fetchone()
                
                partition_info.append({
                    'name': partition_name,
                    'date': partition_date.isoformat() if partition_date else None,
                    'size': size_result[0] if size_result else '0 B',
                    'size_bytes': size_result[1] if size_result else 0,
                    'record_count': count_result[0] if count_result else 0
                })
            
            # 按日期排序
            partition_info.sort(key=lambda x: x['date'] or '')
            
            return {
                'success': True,
                'partitions': partition_info,
                'total_partitions': len(partition_info)
            }
            
        except Exception as e:
            logger.error(f"获取分区信息失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取分区信息失败: {str(e)}',
                'error': str(e)
            }
    
    def _partition_exists(self, partition_name: str) -> bool:
        """
        检查分区是否存在
        
        Args:
            partition_name: 分区名称
            
        Returns:
            bool: 分区是否存在
        """
        try:
            check_sql = """
            SELECT EXISTS (
                SELECT 1 FROM pg_tables 
                WHERE tablename = :partition_name
            )
            """
            result = db.session.execute(text(check_sql), {'partition_name': partition_name}).fetchone()
            return result[0] if result else False
        except Exception:
            return False
    
    def _get_all_partitions(self) -> List[Dict[str, Any]]:
        """
        获取所有分区
        
        Returns:
            List[Dict[str, Any]]: 分区列表
        """
        try:
            sql = """
            SELECT tablename, schemaname
            FROM pg_tables 
            WHERE tablename LIKE :pattern
            ORDER BY tablename
            """
            result = db.session.execute(text(sql), {'pattern': f'{self.partition_prefix}%'})
            return [{'tablename': row[0], 'schemaname': row[1]} for row in result.fetchall()]
        except Exception as e:
            logger.error(f"获取分区列表失败: {str(e)}")
            return []
    
    def _extract_partition_date(self, partition_name: str) -> Optional[date]:
        """
        从分区名称提取日期
        
        Args:
            partition_name: 分区名称
            
        Returns:
            Optional[date]: 分区日期
        """
        try:
            if not partition_name.startswith(self.partition_prefix):
                return None
            
            # 提取 YYYY_MM 格式的日期
            date_str = partition_name[len(self.partition_prefix):]
            if len(date_str) == 7 and '_' in date_str:
                year, month = date_str.split('_')
                return date(int(year), int(month), 1)
            
            return None
        except Exception:
            return None
    
    def get_partition_statistics(self) -> Dict[str, Any]:
        """
        获取分区统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 获取总分区数
            total_partitions = len(self._get_all_partitions())
            
            # 获取总大小
            size_sql = f"""
            SELECT 
                pg_size_pretty(SUM(pg_total_relation_size(tablename::regclass))) as total_size,
                SUM(pg_total_relation_size(tablename::regclass)) as total_size_bytes
            FROM pg_tables 
            WHERE tablename LIKE :pattern
            """
            size_result = db.session.execute(text(size_sql), {'pattern': f'{self.partition_prefix}%'}).fetchone()
            
            # 获取总记录数
            count_sql = f"""
            SELECT SUM(n_tup_ins - n_tup_del) as total_records
            FROM pg_stat_user_tables 
            WHERE relname LIKE :pattern
            """
            count_result = db.session.execute(text(count_sql), {'pattern': f'{self.partition_prefix}%'}).fetchone()
            
            return {
                'success': True,
                'total_partitions': total_partitions,
                'total_size': size_result[0] if size_result and size_result[0] else '0 B',
                'total_size_bytes': size_result[1] if size_result and size_result[1] else 0,
                'total_records': count_result[0] if count_result and count_result[0] else 0
            }
            
        except Exception as e:
            logger.error(f"获取分区统计信息失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取分区统计信息失败: {str(e)}',
                'error': str(e)
            }
