"""
实例统计 API 路由
提供实例性能监控、连接统计、健康度分析等接口
专注于实例层面的统计功能
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, render_template, current_app
from app.utils.time_utils import time_utils
from flask_login import login_required, current_user
from sqlalchemy import and_, desc, func
from app.models.instance import Instance
from app.models.instance_size_stat import InstanceSizeStat
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
instance_stats_bp = Blueprint('instance_stats', __name__)

# 页面路由
@instance_stats_bp.route('/database', methods=['GET'])
@login_required
@view_required
def database_aggregations():
    """
    数据库统计聚合页面（实例统计层面）
    返回HTML页面
    """
    # 获取数据库类型列表
    from app import db
    db_types = db.session.query(Instance.db_type).distinct().all()
    db_types_list = [db_type[0] for db_type in db_types]
    
    return render_template('database_sizes/database_aggregations.html', 
                         db_types_list=db_types_list)

@instance_stats_bp.route('/api/instances/<int:instance_id>/performance', methods=['GET'])
@login_required
@view_required
def get_instance_performance(instance_id: int):
    """
    获取指定实例的性能统计信息
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 实例性能统计信息
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取最近30天的数据
        thirty_days_ago = time_utils.now_china().date() - timedelta(days=30)
        
        # 查询最近30天的实例大小统计数据
        recent_stats = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.is_deleted == False,
            InstanceSizeStat.collected_date >= thirty_days_ago
        ).order_by(InstanceSizeStat.collected_date).all()
        
        if not recent_stats:
            return jsonify({
                'success': True,
                'data': {
                    'instance_id': instance_id,
                    'instance_name': instance.name,
                    'db_type': instance.db_type,
                    'total_size_mb': 0,
                    'database_count': 0,
                    'growth_rate': 0,
                    'avg_daily_growth_mb': 0,
                    'last_collected': None,
                    'status': 'no_data'
                }
            })
        
        # 计算性能指标
        total_size_mb = recent_stats[-1].total_size_mb
        database_count = recent_stats[-1].database_count
        last_collected = recent_stats[-1].collected_date
        
        # 计算增长率
        growth_rate = 0
        if len(recent_stats) >= 2:
            first_size = recent_stats[0].total_size_mb
            last_size = recent_stats[-1].total_size_mb
            if first_size > 0:
                growth_rate = ((last_size - first_size) / first_size) * 100
        
        # 计算平均日增长率
        avg_daily_growth_mb = 0
        if len(recent_stats) >= 2:
            days_diff = (recent_stats[-1].collected_date - recent_stats[0].collected_date).days
            if days_diff > 0:
                size_diff = recent_stats[-1].total_size_mb - recent_stats[0].total_size_mb
                avg_daily_growth_mb = size_diff / days_diff
        
        # 确定状态
        status = 'healthy'
        if growth_rate > 50:  # 30天内增长超过50%
            status = 'high_growth'
        elif growth_rate < -10:  # 30天内减少超过10%
            status = 'shrinking'
        elif total_size_mb == 0:
            status = 'no_data'
        
        return jsonify({
            'success': True,
            'data': {
                'instance_id': instance_id,
                'instance_name': instance.name,
                'db_type': instance.db_type,
                'total_size_mb': total_size_mb,
                'database_count': database_count,
                'growth_rate': growth_rate,
                'avg_daily_growth_mb': avg_daily_growth_mb,
                'last_collected': last_collected.isoformat() if last_collected else None,
                'status': status
            }
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 性能统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@instance_stats_bp.route('/api/instances/<int:instance_id>/trends', methods=['GET'])
@login_required
@view_required
def get_instance_trends(instance_id: int):
    """
    获取指定实例的趋势数据
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 实例趋势数据
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取查询参数
        days = int(request.args.get('days', 30))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 计算日期范围
        if start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            end_date_obj = time_utils.now_china().date()
            start_date_obj = end_date_obj - timedelta(days=days)
        
        # 查询趋势数据
        trends = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.is_deleted == False,
            InstanceSizeStat.collected_date >= start_date_obj,
            InstanceSizeStat.collected_date <= end_date_obj
        ).order_by(InstanceSizeStat.collected_date).all()
        
        # 构建趋势数据
        trend_data = []
        for stat in trends:
            trend_data.append({
                'date': stat.collected_date.isoformat(),
                'total_size_mb': stat.total_size_mb,
                'database_count': stat.database_count,
                'avg_size_mb': stat.total_size_mb / stat.database_count if stat.database_count > 0 else 0
            })
        
        return jsonify({
            'success': True,
            'data': {
                'instance_id': instance_id,
                'instance_name': instance.name,
                'db_type': instance.db_type,
                'start_date': start_date_obj.isoformat(),
                'end_date': end_date_obj.isoformat(),
                'trends': trend_data
            }
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 趋势数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@instance_stats_bp.route('/api/instances/<int:instance_id>/health', methods=['GET'])
@login_required
@view_required
def get_instance_health(instance_id: int):
    """
    获取指定实例的健康度分析
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 实例健康度信息
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取最近7天的数据
        seven_days_ago = time_utils.now_china().date() - timedelta(days=7)
        
        # 查询最近7天的数据
        recent_stats = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.is_deleted == False,
            InstanceSizeStat.collected_date >= seven_days_ago
        ).order_by(InstanceSizeStat.collected_date).all()
        
        if not recent_stats:
            return jsonify({
                'success': True,
                'data': {
                    'instance_id': instance_id,
                    'instance_name': instance.name,
                    'db_type': instance.db_type,
                    'health_score': 0,
                    'status': 'no_data',
                    'issues': ['no_recent_data'],
                    'recommendations': ['检查数据采集任务是否正常运行']
                }
            })
        
        # 计算健康度指标
        health_score = 100
        issues = []
        recommendations = []
        
        # 检查数据新鲜度
        last_collected = recent_stats[-1].collected_date
        days_since_last_collection = (time_utils.now_china().date() - last_collected).days
        
        if days_since_last_collection > 1:
            health_score -= 20
            issues.append('数据采集延迟')
            recommendations.append('检查数据采集任务状态')
        
        # 检查数据完整性
        expected_days = 7
        actual_days = len(set(stat.collected_date for stat in recent_stats))
        completeness = actual_days / expected_days
        
        if completeness < 0.8:
            health_score -= 15
            issues.append('数据采集不完整')
            recommendations.append('检查数据采集任务的执行频率')
        
        # 检查容量增长异常
        if len(recent_stats) >= 2:
            growth_rates = []
            for i in range(1, len(recent_stats)):
                prev_size = recent_stats[i-1].total_size_mb
                curr_size = recent_stats[i].total_size_mb
                if prev_size > 0:
                    growth_rate = ((curr_size - prev_size) / prev_size) * 100
                    growth_rates.append(growth_rate)
            
            if growth_rates:
                avg_growth_rate = sum(growth_rates) / len(growth_rates)
                max_growth_rate = max(growth_rates)
                
                if max_growth_rate > 50:  # 单日增长超过50%
                    health_score -= 25
                    issues.append('容量异常增长')
                    recommendations.append('检查是否有大量数据写入或数据迁移')
                elif avg_growth_rate > 20:  # 平均日增长超过20%
                    health_score -= 10
                    issues.append('容量快速增长')
                    recommendations.append('考虑容量规划和监控')
        
        # 检查数据库数量变化
        if len(recent_stats) >= 2:
            db_count_changes = []
            for i in range(1, len(recent_stats)):
                prev_count = recent_stats[i-1].database_count
                curr_count = recent_stats[i].database_count
                db_count_changes.append(curr_count - prev_count)
            
            if db_count_changes:
                max_change = max(db_count_changes)
                min_change = min(db_count_changes)
                
                if abs(max_change) > 5 or abs(min_change) > 5:  # 数据库数量变化超过5个
                    health_score -= 15
                    issues.append('数据库数量异常变化')
                    recommendations.append('检查数据库创建和删除操作')
        
        # 确定健康状态
        if health_score >= 90:
            status = 'excellent'
        elif health_score >= 70:
            status = 'good'
        elif health_score >= 50:
            status = 'warning'
        else:
            status = 'critical'
        
        return jsonify({
            'success': True,
            'data': {
                'instance_id': instance_id,
                'instance_name': instance.name,
                'db_type': instance.db_type,
                'health_score': max(0, health_score),
                'status': status,
                'issues': issues,
                'recommendations': recommendations,
                'last_collected': last_collected.isoformat(),
                'data_completeness': completeness
            }
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 健康度分析失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@instance_stats_bp.route('/api/instances/<int:instance_id>/capacity-forecast', methods=['GET'])
@login_required
@view_required
def get_instance_capacity_forecast(instance_id: int):
    """
    获取指定实例的容量预测
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 容量预测信息
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取最近30天的数据
        thirty_days_ago = time_utils.now_china().date() - timedelta(days=30)
        
        # 查询最近30天的数据
        recent_stats = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.is_deleted == False,
            InstanceSizeStat.collected_date >= thirty_days_ago
        ).order_by(InstanceSizeStat.collected_date).all()
        
        if len(recent_stats) < 7:  # 至少需要7天的数据
            return jsonify({
                'success': True,
                'data': {
                    'instance_id': instance_id,
                    'instance_name': instance.name,
                    'db_type': instance.db_type,
                    'forecast_available': False,
                    'message': '数据不足，无法进行预测（至少需要7天数据）'
                }
            })
        
        # 计算日增长率
        daily_growth_rates = []
        for i in range(1, len(recent_stats)):
            prev_size = recent_stats[i-1].total_size_mb
            curr_size = recent_stats[i].total_size_mb
            if prev_size > 0:
                growth_rate = ((curr_size - prev_size) / prev_size) * 100
                daily_growth_rates.append(growth_rate)
        
        if not daily_growth_rates:
            return jsonify({
                'success': True,
                'data': {
                    'instance_id': instance_id,
                    'instance_name': instance.name,
                    'db_type': instance.db_type,
                    'forecast_available': False,
                    'message': '无法计算增长率'
                }
            })
        
        # 计算平均日增长率
        avg_daily_growth_rate = sum(daily_growth_rates) / len(daily_growth_rates)
        
        # 当前容量
        current_size_mb = recent_stats[-1].total_size_mb
        
        # 预测未来30天、90天、180天的容量
        forecast_30_days = current_size_mb * (1 + avg_daily_growth_rate / 100) ** 30
        forecast_90_days = current_size_mb * (1 + avg_daily_growth_rate / 100) ** 90
        forecast_180_days = current_size_mb * (1 + avg_daily_growth_rate / 100) ** 180
        
        # 预测达到特定容量的时间（假设有容量限制）
        capacity_warnings = []
        if avg_daily_growth_rate > 0:
            # 假设1TB为警告阈值
            warning_threshold_mb = 1024 * 1024  # 1TB in MB
            if current_size_mb < warning_threshold_mb:
                days_to_warning = ((warning_threshold_mb / current_size_mb) ** (1 / (avg_daily_growth_rate / 100))) - 1
                if days_to_warning > 0:
                    capacity_warnings.append({
                        'threshold': '1TB',
                        'days_to_reach': int(days_to_warning),
                        'date': (time_utils.now_china().date() + timedelta(days=int(days_to_warning))).isoformat()
                    })
        
        return jsonify({
            'success': True,
            'data': {
                'instance_id': instance_id,
                'instance_name': instance.name,
                'db_type': instance.db_type,
                'forecast_available': True,
                'current_size_mb': current_size_mb,
                'avg_daily_growth_rate': avg_daily_growth_rate,
                'forecasts': {
                    '30_days': {
                        'size_mb': forecast_30_days,
                        'size_gb': forecast_30_days / 1024,
                        'size_tb': forecast_30_days / (1024 * 1024)
                    },
                    '90_days': {
                        'size_mb': forecast_90_days,
                        'size_gb': forecast_90_days / 1024,
                        'size_tb': forecast_90_days / (1024 * 1024)
                    },
                    '180_days': {
                        'size_mb': forecast_180_days,
                        'size_gb': forecast_180_days / 1024,
                        'size_tb': forecast_180_days / (1024 * 1024)
                    }
                },
                'capacity_warnings': capacity_warnings
            }
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 容量预测失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@instance_stats_bp.route('/api/databases/aggregations', methods=['GET'])
@login_required
@view_required
def get_databases_aggregations():
    """
    获取数据库统计聚合数据（实例统计层面）
    原 /api/database 功能
    
    Returns:
        JSON: 数据库聚合数据
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        database_name = request.args.get('database_name')
        period_type = request.args.get('period_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        # 是否返回所有数据（用于图表显示）
        get_all = request.args.get('get_all', 'false').lower() == 'true'
        
        # 计算offset
        offset = (page - 1) * per_page
        limit = per_page
        
        # 构建查询 - 直接查询聚合统计表
        from app.models.database_size_aggregation import DatabaseSizeAggregation
        query = DatabaseSizeAggregation.query.join(Instance)
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(DatabaseSizeAggregation.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)
        if period_type:
            query = query.filter(DatabaseSizeAggregation.period_type == period_type)
        if start_date:
            query = query.filter(DatabaseSizeAggregation.period_start >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(DatabaseSizeAggregation.period_end <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # 排序和分页
        if get_all:
            # 用于图表显示：按大小排序获取TOP 20
            query = query.order_by(desc(DatabaseSizeAggregation.avg_size_mb))
            aggregations = query.limit(20).all()
            total = len(aggregations)
        else:
            # 用于表格显示：按时间排序分页
            query = query.order_by(desc(DatabaseSizeAggregation.period_start))
            total = query.count()
            aggregations = query.offset(offset).limit(limit).all()
        
        # 转换为字典格式，包含实例信息
        data = []
        for agg in aggregations:
            agg_dict = agg.to_dict()
            # 添加实例信息
            agg_dict['instance'] = {
                'id': agg.instance.id,
                'name': agg.instance.name,
                'db_type': agg.instance.db_type
            }
            data.append(agg_dict)
        
        return jsonify({
            'success': True,
            'data': data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page < (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"获取数据库统计聚合数据时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@instance_stats_bp.route('/api/databases/aggregations/summary', methods=['GET'])
@login_required
@view_required
def get_databases_aggregations_summary():
    """
    获取数据库统计聚合汇总信息（实例统计层面）
    原 /api/database/summary 功能
    
    Returns:
        JSON: 数据库聚合汇总信息
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        database_name = request.args.get('database_name')
        period_type = request.args.get('period_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 构建查询
        from app.models.database_size_aggregation import DatabaseSizeAggregation
        query = DatabaseSizeAggregation.query.join(Instance)
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(DatabaseSizeAggregation.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)
        if period_type:
            query = query.filter(DatabaseSizeAggregation.period_type == period_type)
        if start_date:
            query = query.filter(DatabaseSizeAggregation.period_start >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(DatabaseSizeAggregation.period_end <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # 获取聚合数据
        aggregations = query.all()
        
        if not aggregations:
            return jsonify({
                'success': True,
                'data': {
                    'total_databases': 0,
                    'total_size_mb': 0,
                    'avg_size_mb': 0,
                    'max_size_mb': 0,
                    'period_type': period_type or 'all'
                }
            })
        
        # 计算汇总统计
        total_databases = len(set(agg.database_name for agg in aggregations))
        total_size_mb = sum(agg.avg_size_mb for agg in aggregations)
        avg_size_mb = total_size_mb / len(aggregations) if aggregations else 0
        max_size_mb = max(agg.avg_size_mb for agg in aggregations) if aggregations else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_databases': total_databases,
                'total_size_mb': total_size_mb,
                'avg_size_mb': avg_size_mb,
                'max_size_mb': max_size_mb,
                'period_type': period_type or 'all'
            }
        })
        
    except Exception as e:
        logger.error(f"获取数据库统计聚合汇总时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
