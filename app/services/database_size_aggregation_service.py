"""
数据库大小统计聚合服务
支持每周、每月、每季度的统计聚合计算
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import func, and_, or_
from app.models.database_size_stat import DatabaseSizeStat
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance import Instance
from app import db

logger = logging.getLogger(__name__)


class DatabaseSizeAggregationService:
    """数据库大小统计聚合服务"""
    
    def __init__(self):
        self.period_types = ['daily', 'weekly', 'monthly', 'quarterly']
    
    def calculate_all_aggregations(self) -> Dict[str, Any]:
        """
        计算所有实例的统计聚合数据
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        logger.info("开始计算所有实例的统计聚合数据...")
        
        try:
            results = {
                'daily': self.calculate_daily_aggregations(),
                'weekly': self.calculate_weekly_aggregations(),
                'monthly': self.calculate_monthly_aggregations(),
                'quarterly': self.calculate_quarterly_aggregations()
            }
            
            # 统计总体结果
            total_processed = sum(r.get('processed_instances', 0) for r in results.values())
            total_errors = sum(r.get('errors', 0) for r in results.values())
            total_aggregations = sum(r.get('aggregations_created', 0) for r in results.values())
            
            logger.info(f"统计聚合计算完成: 处理了 {total_processed} 个实例，出现 {total_errors} 个错误，创建了 {total_aggregations} 个聚合记录")
            
            return {
                'success': True,
                'message': f'统计聚合计算完成，处理了 {total_processed} 个实例，创建了 {total_aggregations} 个聚合记录',
                'aggregations_created': total_aggregations,
                'processed_instances': total_processed,
                'errors': total_errors,
                'details': results
            }
            
        except Exception as e:
            logger.error(f"计算统计聚合数据时出错: {str(e)}")
            return {
                'success': False,
                'message': f'计算统计聚合数据时出错: {str(e)}',
                'error': str(e),
                'aggregations_created': 0,
                'processed_instances': 0,
                'errors': 1
            }
    
    def calculate_daily_aggregations(self) -> Dict[str, Any]:
        """
        计算每日统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        logger.info("开始计算每日统计聚合...")
        
        # 获取今天的数据（支持第一天部署的情况）
        end_date = date.today()
        start_date = end_date  # 同一天，支持当天数据聚合
        
        return self._calculate_aggregations('daily', start_date, end_date)
    
    def calculate_weekly_aggregations(self) -> Dict[str, Any]:
        """
        计算每周统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        logger.info("开始计算每周统计聚合...")
        
        # 获取上周的数据
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        return self._calculate_aggregations('weekly', start_date, end_date)
    
    def calculate_monthly_aggregations(self) -> Dict[str, Any]:
        """
        计算每月统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        logger.info("开始计算每月统计聚合...")
        
        # 获取上个月的数据
        today = date.today()
        if today.month == 1:
            start_date = date(today.year - 1, 12, 1)
            end_date = date(today.year - 1, 12, 31)
        else:
            start_date = date(today.year, today.month - 1, 1)
            end_date = date(today.year, today.month, 1) - timedelta(days=1)
        
        return self._calculate_aggregations('monthly', start_date, end_date)
    
    def calculate_quarterly_aggregations(self) -> Dict[str, Any]:
        """
        计算每季度统计聚合
        
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        logger.info("开始计算每季度统计聚合...")
        
        # 获取上个季度的数据
        today = date.today()
        quarter = (today.month - 1) // 3 + 1
        
        if quarter == 1:
            # 上个季度是去年Q4
            start_date = date(today.year - 1, 10, 1)
            end_date = date(today.year - 1, 12, 31)
        else:
            # 上个季度是今年Q(quarter-1)
            quarter_start_month = (quarter - 2) * 3 + 1
            start_date = date(today.year, quarter_start_month, 1)
            end_date = date(today.year, quarter_start_month + 2, 1) - timedelta(days=1)
        
        return self._calculate_aggregations('quarterly', start_date, end_date)
    
    def _calculate_aggregations(self, period_type: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        计算指定周期的统计聚合
        
        Args:
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Any]: 聚合结果统计
        """
        try:
            # 获取所有活跃实例
            instances = Instance.query.filter_by(is_active=True).all()
            
            total_processed = 0
            total_errors = 0
            total_records = 0
            
            for instance in instances:
                try:
                    # 获取该实例在指定时间范围内的数据
                    stats = DatabaseSizeStat.query.filter(
                        DatabaseSizeStat.instance_id == instance.id,
                        DatabaseSizeStat.collected_date >= start_date,
                        DatabaseSizeStat.collected_date <= end_date
                    ).all()
                    
                    if not stats:
                        logger.debug(f"实例 {instance.name} 在 {start_date} 到 {end_date} 期间没有数据")
                        continue
                    
                    # 按数据库分组计算统计
                    db_groups = {}
                    for stat in stats:
                        db_name = stat.database_name
                        if db_name not in db_groups:
                            db_groups[db_name] = []
                        db_groups[db_name].append(stat)
                    
                    # 为每个数据库计算统计聚合
                    for db_name, db_stats in db_groups.items():
                        self._calculate_database_aggregation(
                            instance.id, db_name, period_type, 
                            start_date, end_date, db_stats
                        )
                        total_records += 1
                    
                    total_processed += 1
                    logger.debug(f"实例 {instance.name} 的 {period_type} 聚合计算完成")
                    
                except Exception as e:
                    logger.error(f"处理实例 {instance.id} 的 {period_type} 统计聚合时出错: {str(e)}")
                    total_errors += 1
                    continue
            
            return {
                'status': 'success',
                'period_type': period_type,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_instances': len(instances),
                'processed_instances': total_processed,
                'total_records': total_records,
                'errors': total_errors
            }
            
        except Exception as e:
            logger.error(f"计算 {period_type} 统计聚合时出错: {str(e)}")
            return {
                'status': 'error',
                'period_type': period_type,
                'error': str(e)
            }
    
    def _calculate_database_aggregation(self, instance_id: int, database_name: str, 
                                      period_type: str, start_date: date, end_date: date, 
                                      stats: List[DatabaseSizeStat]) -> None:
        """
        计算单个数据库的统计聚合
        
        Args:
            instance_id: 实例ID
            database_name: 数据库名称
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            stats: 统计数据列表
        """
        try:
            # 计算基本统计
            sizes = [stat.size_mb for stat in stats]
            data_sizes = [stat.data_size_mb for stat in stats if stat.data_size_mb is not None]
            # 不再计算日志大小统计
            
            # 检查是否已存在该周期的聚合数据
            existing = DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.instance_id == instance_id,
                DatabaseSizeAggregation.database_name == database_name,
                DatabaseSizeAggregation.period_type == period_type,
                DatabaseSizeAggregation.period_start == start_date
            ).first()
            
            if existing:
                # 更新现有记录
                aggregation = existing
            else:
                # 创建新记录
                aggregation = DatabaseSizeAggregation(
                    instance_id=instance_id,
                    database_name=database_name,
                    period_type=period_type,
                    period_start=start_date,
                    period_end=end_date
                )
            
            # 更新统计指标
            aggregation.avg_size_mb = int(sum(sizes) / len(sizes))
            aggregation.max_size_mb = max(sizes)
            aggregation.min_size_mb = min(sizes)
            aggregation.data_count = len(stats)
            
            # 数据大小统计
            if data_sizes:
                aggregation.avg_data_size_mb = int(sum(data_sizes) / len(data_sizes))
                aggregation.max_data_size_mb = max(data_sizes)
                aggregation.min_data_size_mb = min(data_sizes)
            
            # 不计算日志大小统计，直接设置为 None
            aggregation.avg_log_size_mb = None
            aggregation.max_log_size_mb = None
            aggregation.min_log_size_mb = None
            
            # 计算增量/减量统计
            self._calculate_change_statistics(aggregation, instance_id, database_name, period_type, start_date, end_date)
            
            aggregation.calculated_at = datetime.utcnow()
            
            if not existing:
                db.session.add(aggregation)
            
            db.session.commit()
            
            logger.debug(f"数据库 {database_name} 的 {period_type} 聚合计算完成")
            
        except Exception as e:
            logger.error(f"计算数据库 {database_name} 的 {period_type} 统计聚合时出错: {str(e)}")
            db.session.rollback()
            raise
    
    def _calculate_change_statistics(self, aggregation, instance_id: int, database_name: str, 
                                   period_type: str, start_date: date, end_date: date) -> None:
        """
        计算增量/减量统计
        
        Args:
            aggregation: 聚合数据对象
            instance_id: 实例ID
            database_name: 数据库名称
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
        """
        try:
            # 计算上一个周期的日期范围
            prev_start_date, prev_end_date = self._get_previous_period_dates(period_type, start_date, end_date)
            
            # 获取上一个周期的数据
            prev_stats = DatabaseSizeStat.query.filter(
                DatabaseSizeStat.instance_id == instance_id,
                DatabaseSizeStat.database_name == database_name,
                DatabaseSizeStat.collected_date >= prev_start_date,
                DatabaseSizeStat.collected_date <= prev_end_date
            ).all()
            
            if not prev_stats:
                # 没有上一个周期的数据，设置为0
                aggregation.size_change_mb = 0
                aggregation.size_change_percent = 0
                aggregation.data_size_change_mb = 0
                aggregation.data_size_change_percent = 0
                aggregation.log_size_change_mb = 0
                aggregation.log_size_change_percent = 0
                aggregation.trend_direction = "stable"
                aggregation.growth_rate = 0
                return
            
            # 计算上一个周期的平均值
            prev_sizes = [stat.size_mb for stat in prev_stats]
            prev_avg_size = sum(prev_sizes) / len(prev_sizes)
            
            prev_data_sizes = [stat.data_size_mb for stat in prev_stats if stat.data_size_mb is not None]
            prev_avg_data_size = sum(prev_data_sizes) / len(prev_data_sizes) if prev_data_sizes else None
            
            # 不再计算日志大小变化
            
            # 计算变化量（当前 - 上一个周期）
            size_change_mb = aggregation.avg_size_mb - prev_avg_size
            aggregation.size_change_mb = int(size_change_mb)
            aggregation.size_change_percent = round((size_change_mb / prev_avg_size * 100) if prev_avg_size > 0 else 0, 2)
            
            # 数据大小变化
            if prev_avg_data_size is not None and aggregation.avg_data_size_mb is not None:
                data_size_change_mb = aggregation.avg_data_size_mb - prev_avg_data_size
                aggregation.data_size_change_mb = int(data_size_change_mb)
                aggregation.data_size_change_percent = round((data_size_change_mb / prev_avg_data_size * 100) if prev_avg_data_size > 0 else 0, 2)
            
            # 不计算日志大小变化，直接设置为 None
            aggregation.log_size_change_mb = None
            aggregation.log_size_change_percent = None
            
            # 设置增长率（简化，不判断趋势方向）
            aggregation.growth_rate = aggregation.size_change_percent
            
        except Exception as e:
            logger.error(f"计算增量/减量统计时出错: {str(e)}")
            # 设置默认值
            aggregation.size_change_mb = 0
            aggregation.size_change_percent = 0
            aggregation.data_size_change_mb = 0
            aggregation.data_size_change_percent = 0
            aggregation.log_size_change_mb = 0
            aggregation.log_size_change_percent = 0
            aggregation.growth_rate = 0
    
    def _get_previous_period_dates(self, period_type: str, start_date: date, end_date: date) -> tuple:
        """
        获取上一个周期的日期范围
        
        Args:
            period_type: 统计周期类型
            start_date: 当前周期开始日期
            end_date: 当前周期结束日期
            
        Returns:
            tuple: (上一个周期开始日期, 上一个周期结束日期)
        """
        if period_type == "daily":
            # 前一天（支持当天数据聚合的情况）
            if start_date == end_date:
                # 如果是同一天，前一天就是昨天
                prev_end_date = start_date - timedelta(days=1)
                prev_start_date = prev_end_date
            else:
                # 如果是多天，前一天是开始日期的前一天
                period_duration = end_date - start_date
                prev_end_date = start_date - timedelta(days=1)
                prev_start_date = prev_end_date - period_duration
        elif period_type == "weekly":
            # 上一周
            period_duration = end_date - start_date
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - period_duration
        elif period_type == "monthly":
            # 上一个月
            if start_date.month == 1:
                prev_start_date = date(start_date.year - 1, 12, 1)
                prev_end_date = date(start_date.year - 1, 12, 31)
            else:
                prev_start_date = date(start_date.year, start_date.month - 1, 1)
                prev_end_date = date(start_date.year, start_date.month, 1) - timedelta(days=1)
        elif period_type == "quarterly":
            # 上一个季度
            quarter = (start_date.month - 1) // 3 + 1
            if quarter == 1:
                prev_start_date = date(start_date.year - 1, 10, 1)
                prev_end_date = date(start_date.year - 1, 12, 31)
            else:
                prev_quarter_start_month = (quarter - 2) * 3 + 1
                prev_start_date = date(start_date.year, prev_quarter_start_month, 1)
                prev_end_date = date(start_date.year, prev_quarter_start_month + 2, 1) - timedelta(days=1)
        else:
            # 默认返回相同周期
            period_duration = end_date - start_date
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - period_duration
        
        return prev_start_date, prev_end_date
    
    def get_aggregations(self, instance_id: int, period_type: str, 
                        start_date: date = None, end_date: date = None,
                        database_name: str = None) -> List[Dict[str, Any]]:
        """
        获取统计聚合数据
        
        Args:
            instance_id: 实例ID
            period_type: 统计周期类型
            start_date: 开始日期
            end_date: 结束日期
            database_name: 数据库名称
            
        Returns:
            List[Dict[str, Any]]: 聚合数据列表
        """
        query = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.instance_id == instance_id,
            DatabaseSizeAggregation.period_type == period_type
        )
        
        if start_date:
            query = query.filter(DatabaseSizeAggregation.period_start >= start_date)
        if end_date:
            query = query.filter(DatabaseSizeAggregation.period_end <= end_date)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)
        
        aggregations = query.order_by(DatabaseSizeAggregation.period_start.desc()).all()
        
        return [self._format_aggregation(agg) for agg in aggregations]
    
    def get_trends_analysis(self, instance_id: int, period_type: str, 
                           months: int = 12) -> Dict[str, Any]:
        """
        获取趋势分析数据
        
        Args:
            instance_id: 实例ID
            period_type: 统计周期类型
            months: 返回最近几个月的数据
            
        Returns:
            Dict[str, Any]: 趋势分析数据
        """
        try:
            # 计算开始日期
            end_date = date.today()
            start_date = end_date - timedelta(days=months * 30)
            
            # 获取聚合数据
            aggregations = self.get_aggregations(instance_id, period_type, start_date, end_date)
            
            if not aggregations:
                return {
                    'trends': [],
                    'summary': {
                        'total_growth_rate': 0,
                        'largest_database': None,
                        'fastest_growing': None
                    }
                }
            
            # 按周期分组
            trends = {}
            for agg in aggregations:
                period = agg['period_start'][:7]  # YYYY-MM
                if period not in trends:
                    trends[period] = {
                        'period': period,
                        'total_size_mb': 0,
                        'databases': []
                    }
                
                trends[period]['total_size_mb'] += agg['statistics']['avg_size_mb']
                trends[period]['databases'].append({
                    'database_name': agg['database_name'],
                    'avg_size_mb': agg['statistics']['avg_size_mb'],
                    'growth_rate': 0  # 需要计算
                })
            
            # 计算增长率
            periods = sorted(trends.keys())
            for i, period in enumerate(periods):
                if i > 0:
                    prev_period = periods[i-1]
                    for db in trends[period]['databases']:
                        prev_db = next((d for d in trends[prev_period]['databases'] 
                                      if d['database_name'] == db['database_name']), None)
                        if prev_db:
                            growth_rate = ((db['avg_size_mb'] - prev_db['avg_size_mb']) / 
                                         prev_db['avg_size_mb'] * 100) if prev_db['avg_size_mb'] > 0 else 0
                            db['growth_rate'] = round(growth_rate, 2)
            
            # 计算总体统计
            total_growth_rate = 0
            largest_database = None
            fastest_growing = None
            max_size = 0
            max_growth = 0
            
            for period_data in trends.values():
                for db in period_data['databases']:
                    if db['avg_size_mb'] > max_size:
                        max_size = db['avg_size_mb']
                        largest_database = db['database_name']
                    
                    if abs(db['growth_rate']) > max_growth:
                        max_growth = abs(db['growth_rate'])
                        fastest_growing = db['database_name']
            
            # 计算总体增长率（简化计算）
            if len(periods) > 1:
                first_period = trends[periods[0]]['total_size_mb']
                last_period = trends[periods[-1]]['total_size_mb']
                total_growth_rate = ((last_period - first_period) / first_period * 100) if first_period > 0 else 0
            
            return {
                'trends': list(trends.values()),
                'summary': {
                    'total_growth_rate': round(total_growth_rate, 2),
                    'largest_database': largest_database,
                    'fastest_growing': fastest_growing
                }
            }
            
        except Exception as e:
            logger.error(f"获取趋势分析数据时出错: {str(e)}")
            return {
                'trends': [],
                'summary': {
                    'total_growth_rate': 0,
                    'largest_database': None,
                    'fastest_growing': None
                }
            }
    
    def _format_aggregation(self, aggregation: DatabaseSizeAggregation) -> Dict[str, Any]:
        """
        格式化聚合数据
        
        Args:
            aggregation: 聚合数据对象
            
        Returns:
            Dict[str, Any]: 格式化后的数据
        """
        return {
            'id': aggregation.id,
            'instance_id': aggregation.instance_id,
            'database_name': aggregation.database_name,
            'period_type': aggregation.period_type,
            'period_start': aggregation.period_start.isoformat() if aggregation.period_start else None,
            'period_end': aggregation.period_end.isoformat() if aggregation.period_end else None,
            'statistics': {
                'avg_size_mb': aggregation.avg_size_mb,
                'max_size_mb': aggregation.max_size_mb,
                'min_size_mb': aggregation.min_size_mb,
                'data_count': aggregation.data_count,
                'avg_data_size_mb': aggregation.avg_data_size_mb,
                'max_data_size_mb': aggregation.max_data_size_mb,
                'min_data_size_mb': aggregation.min_data_size_mb,
                'avg_log_size_mb': aggregation.avg_log_size_mb,
                'max_log_size_mb': aggregation.max_log_size_mb,
                'min_log_size_mb': aggregation.min_log_size_mb
            },
            'changes': {
                'size_change_mb': aggregation.size_change_mb,
                'size_change_percent': float(aggregation.size_change_percent) if aggregation.size_change_percent else 0,
                'data_size_change_mb': aggregation.data_size_change_mb,
                'data_size_change_percent': float(aggregation.data_size_change_percent) if aggregation.data_size_change_percent else None,
                'log_size_change_mb': aggregation.log_size_change_mb,
                'log_size_change_percent': float(aggregation.log_size_change_percent) if aggregation.log_size_change_percent else None,
                'growth_rate': float(aggregation.growth_rate) if aggregation.growth_rate else 0
            },
            'calculated_at': aggregation.calculated_at.isoformat() if aggregation.calculated_at else None,
            'created_at': aggregation.created_at.isoformat() if aggregation.created_at else None
        }
