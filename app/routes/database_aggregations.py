"""
数据库统计聚合路由
提供数据库级别的数据库大小统计聚合功能
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func, desc
from app.models.instance import Instance
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
database_aggregations_bp = Blueprint('database_aggregations', __name__)

# 页面路由
@database_aggregations_bp.route('/', methods=['GET'])
@login_required
@view_required
def database_aggregations():
    """
    数据库统计聚合页面或API
    
    如果是页面请求（无查询参数），返回HTML页面
    如果是API请求（有查询参数），返回JSON数据
    """
    # 检查是否有查询参数，如果有则返回API数据
    if request.args:
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
            
            # 构建查询
            query = DatabaseSizeAggregation.query.join(Instance)
            
            # 过滤掉已删除的数据库（通过检查最新的DatabaseSizeStat记录）
            # 子查询：获取每个实例-数据库组合的最新状态
            latest_stats_subquery = db.session.query(
                DatabaseSizeStat.instance_id,
                DatabaseSizeStat.database_name,
                DatabaseSizeStat.is_deleted,
                func.row_number().over(
                    partition_by=[DatabaseSizeStat.instance_id, DatabaseSizeStat.database_name],
                    order_by=DatabaseSizeStat.collected_date.desc()
                ).label('rn')
            ).subquery()
            
            # 获取未删除的数据库列表
            active_databases_subquery = db.session.query(
                latest_stats_subquery.c.instance_id,
                latest_stats_subquery.c.database_name
            ).filter(
                and_(
                    latest_stats_subquery.c.rn == 1,
                    or_(
                        latest_stats_subquery.c.is_deleted == False,
                        latest_stats_subquery.c.is_deleted.is_(None)
                    )
                )
            ).subquery()
            
            query = query.join(
                active_databases_subquery,
                and_(
                    DatabaseSizeAggregation.instance_id == active_databases_subquery.c.instance_id,
                    DatabaseSizeAggregation.database_name == active_databases_subquery.c.database_name
                )
            )
            
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
    else:
        # 无查询参数，返回HTML页面
        # 获取实例列表用于筛选
        instances = Instance.query.filter_by(is_active=True).all()
        instances_list = [{'id': i.id, 'name': i.name, 'db_type': i.db_type} for i in instances]
        
        # 获取数据库类型列表
        db_types = db.session.query(Instance.db_type).filter_by(is_active=True).distinct().all()
        database_types_list = [{'value': dt[0], 'label': dt[0]} for dt in db_types]
        
        # 获取数据库名称列表
        databases = db.session.query(
            DatabaseSizeAggregation.database_name,
            Instance.name.label('instance_name')
        ).join(Instance).distinct().all()
        databases_list = [{'value': d.database_name, 'label': f"{d.instance_name}.{d.database_name}"} for d in databases]
        
        return render_template('database_sizes/database_aggregations.html',
                             instances=instances_list,
                             database_types=database_types_list,
                             databases=databases_list)


@database_aggregations_bp.route('/summary', methods=['GET'])
@login_required
@view_required
def get_database_aggregations_summary():
    """
    获取数据库统计聚合数据汇总统计
    
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
        
        # 按数据库统计
        database_stats = db.session.query(
            DatabaseSizeAggregation.database_name,
            Instance.name.label('instance_name'),
            func.count(DatabaseSizeAggregation.id).label('count')
        ).join(Instance).group_by(
            DatabaseSizeAggregation.database_name, 
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
            'database_stats': [{'database_name': d.database_name, 'instance_name': d.instance_name, 'count': d.count} for d in database_stats],
            'last_update': latest_aggregation.calculated_at.isoformat() if latest_aggregation else None
        }
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"获取数据库统计聚合汇总时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
