"""
实例统计聚合路由
提供实例级别的数据库大小统计聚合功能
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from app.models.instance import Instance
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
instance_aggregations_bp = Blueprint('instance_aggregations', __name__)

# 页面路由
@instance_aggregations_bp.route('/', methods=['GET'])
@login_required
@view_required
def instance_aggregations():
    """
    实例统计聚合页面或API
    
    如果是页面请求（无查询参数），返回HTML页面
    如果是API请求（有查询参数），返回JSON数据
    """
    # 检查是否有查询参数，如果有则返回API数据
    if request.args:
        try:
            # 获取查询参数
            instance_id = request.args.get('instance_id', type=int)
            db_type = request.args.get('db_type')
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
            query = DatabaseSizeAggregation.query.join(Instance)
            
            # 应用过滤条件
            if instance_id:
                query = query.filter(DatabaseSizeAggregation.instance_id == instance_id)
            if db_type:
                query = query.filter(Instance.db_type == db_type)
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
            logger.error(f"获取实例统计聚合数据时出错: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    else:
        # 无查询参数，返回HTML页面
        # 获取实例列表用于筛选
        instances = Instance.query.filter_by(is_active=True).all()
        instances_list = [{'id': i.id, 'name': i.name, 'db_type': i.db_type} for i in instances]
        
        # 获取数据库类型配置
        from app.models.database_type_config import DatabaseTypeConfig
        database_types = DatabaseTypeConfig.query.filter_by(is_active=True).order_by(DatabaseTypeConfig.id).all()
        database_types_list = []
        for db_type in database_types:
            database_types_list.append({
                'name': db_type.name,
                'display_name': db_type.display_name
            })
        
        return render_template('database_sizes/instance_aggregations.html',
                             instances=instances_list,
                             database_types=database_types_list,
                             db_type=request.args.get('db_type', ''))


@instance_aggregations_bp.route('/summary', methods=['GET'])
@login_required
@view_required
def get_instance_aggregations_summary():
    """
    获取实例统计聚合数据汇总统计
    
    Returns:
        JSON: 汇总统计信息
    """
    try:
        # 获取基本统计
        total_aggregations = DatabaseSizeAggregation.query.count()
        total_instances = Instance.query.filter_by(is_active=True).count()
        
        # 获取数据库数量统计
        total_databases = db.session.query(
            func.count(func.distinct(DatabaseSizeAggregation.database_name))
        ).scalar() or 0
        
        # 获取大小统计
        size_stats = db.session.query(
            func.avg(DatabaseSizeAggregation.avg_size_mb).label('avg_size'),
            func.max(DatabaseSizeAggregation.max_size_mb).label('max_size')
        ).first()
        
        # 按周期类型统计
        period_stats = db.session.query(
            DatabaseSizeAggregation.period_type,
            func.count(DatabaseSizeAggregation.id).label('count')
        ).group_by(DatabaseSizeAggregation.period_type).all()
        
        # 按实例统计
        instance_stats = db.session.query(
            DatabaseSizeAggregation.instance_id,
            Instance.name.label('instance_name'),
            func.count(DatabaseSizeAggregation.id).label('count')
        ).join(Instance).group_by(
            DatabaseSizeAggregation.instance_id, 
            Instance.name
        ).order_by(func.count(DatabaseSizeAggregation.id).desc()).limit(10).all()
        
        # 最近更新时间
        latest_aggregation = DatabaseSizeAggregation.query.order_by(
            desc(DatabaseSizeAggregation.calculated_at)
        ).first()
        
        summary = {
            'total_aggregations': total_aggregations,
            'total_instances': total_instances,
            'total_databases': total_databases,
            'avg_size_mb': float(size_stats.avg_size) if size_stats.avg_size else 0,
            'max_size_mb': size_stats.max_size or 0,
            'period_stats': [{'period_type': p.period_type, 'count': p.count} for p in period_stats],
            'instance_stats': [{'instance_name': i.instance_name, 'count': i.count} for i in instance_stats],
            'last_update': latest_aggregation.calculated_at.isoformat() if latest_aggregation else None
        }
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"获取实例统计聚合汇总时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
