"""
统计聚合路由
提供实例级别和数据库级别的数据库大小统计聚合功能
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from app.utils.time_utils import time_utils
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_, or_
from app.models.instance import Instance
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.services.database_size_aggregation_service import DatabaseSizeAggregationService
from app.tasks.database_size_aggregation_tasks import (
    calculate_database_size_aggregations,
    calculate_instance_aggregations,
    calculate_period_aggregations,
    get_aggregation_status
)
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
aggregations_bp = Blueprint('aggregations', __name__)

# 页面路由
@aggregations_bp.route('/', methods=['GET'])
@login_required
@view_required
def aggregations():
    """
    统计聚合页面或API
    
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
            view_type = request.args.get('view_type', 'instance')  # instance 或 database
            table_type = request.args.get('table_type', 'all')  # all, database, instance
            
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            # 是否返回所有数据（用于图表显示）
            get_all = request.args.get('get_all', 'false').lower() == 'true'
            
            # 计算offset
            offset = (page - 1) * per_page
            limit = per_page
            
            # 根据表类型选择查询
            from app.models.instance_size_aggregation import InstanceSizeAggregation
            
            if table_type == 'instance':
                # 查询实例聚合表
                query = InstanceSizeAggregation.query.join(Instance)
                
                # 应用过滤条件
                if instance_id:
                    query = query.filter(InstanceSizeAggregation.instance_id == instance_id)
                if db_type:
                    query = query.filter(Instance.db_type == db_type)
                if period_type:
                    query = query.filter(InstanceSizeAggregation.period_type == period_type)
                if start_date:
                    query = query.filter(InstanceSizeAggregation.period_start >= datetime.strptime(start_date, '%Y-%m-%d').date())
                if end_date:
                    query = query.filter(InstanceSizeAggregation.period_end <= datetime.strptime(end_date, '%Y-%m-%d').date())
                
                # 排序和分页
                if get_all:
                    aggregations = query.order_by(desc(InstanceSizeAggregation.avg_size_mb)).limit(20).all()
                    total = len(aggregations)
                else:
                    query = query.order_by(desc(InstanceSizeAggregation.period_start))
                    total = query.count()
                    aggregations = query.offset(offset).limit(limit).all()
                
                # 转换为字典格式
                data = []
                for agg in aggregations:
                    agg_dict = agg.to_dict()
                    agg_dict['table_type'] = 'instance'
                    agg_dict['database_name'] = 'N/A'  # 实例聚合没有数据库名称
                    agg_dict['instance'] = {
                        'id': agg.instance.id,
                        'name': agg.instance.name,
                        'db_type': agg.instance.db_type
                    }
                    data.append(agg_dict)
                    
            else:
                # 默认查询数据库聚合表
                query = DatabaseSizeAggregation.query.join(Instance)
                
                # 过滤掉已删除的数据库
                latest_stats_subquery = db.session.query(
                    DatabaseSizeStat.instance_id,
                    DatabaseSizeStat.database_name,
                    DatabaseSizeStat.is_deleted,
                    func.row_number().over(
                        partition_by=[DatabaseSizeStat.instance_id, DatabaseSizeStat.database_name],
                        order_by=DatabaseSizeStat.collected_date.desc()
                    ).label('rn')
                ).subquery()
                
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
                    aggregations = query.order_by(desc(DatabaseSizeAggregation.avg_size_mb)).limit(20).all()
                    total = len(aggregations)
                else:
                    query = query.order_by(desc(DatabaseSizeAggregation.period_start))
                    total = query.count()
                    aggregations = query.offset(offset).limit(limit).all()
                
                # 转换为字典格式
                data = []
                for agg in aggregations:
                    agg_dict = agg.to_dict()
                    agg_dict['table_type'] = 'database'
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
                'has_next': page < (total + per_page - 1) // per_page,
                'view_type': view_type
            })
            
        except Exception as e:
            logger.error(f"获取统计聚合数据时出错: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    else:
        # 无查询参数，返回HTML页面
        # 获取实例列表用于筛选
        instances = Instance.query.filter_by(is_active=True).order_by(Instance.id).all()
        instances_list = []
        for instance in instances:
            instances_list.append({
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type
            })
        
        # 获取数据库类型配置
        from app.models.database_type_config import DatabaseTypeConfig
        database_types = DatabaseTypeConfig.query.filter_by(is_active=True).order_by(DatabaseTypeConfig.id).all()
        database_types_list = []
        for db_type in database_types:
            database_types_list.append({
                'name': db_type.name,
                'display_name': db_type.display_name
            })
        
        # 获取数据库名称列表
        databases = db.session.query(
            DatabaseSizeAggregation.database_name,
            Instance.name.label('instance_name')
        ).join(Instance).distinct().all()
        databases_list = [{'value': d.database_name, 'label': f"{d.instance_name}.{d.database_name}"} for d in databases]
        
        return render_template('database_sizes/instance_aggregations.html', 
                             instances=instances_list,
                             database_types=database_types_list,
                             db_type=request.args.get('db_type', ''))


@aggregations_bp.route('/summary', methods=['GET'])
@login_required
@view_required
def get_aggregations_summary():
    """
    获取统计聚合数据汇总统计
    
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
            'average_size_mb': float(size_stats.avg_size) if size_stats.avg_size else 0,
            'max_size_mb': int(size_stats.max_size) if size_stats.max_size else 0,
            'period_stats': [
                {'period_type': stat.period_type, 'count': stat.count}
                for stat in period_stats
            ],
            'top_instances': [
                {'instance_id': stat.instance_id, 'instance_name': stat.instance_name, 'count': stat.count}
                for stat in instance_stats
            ],
            'top_databases': [
                {'database_name': stat.database_name, 'instance_name': stat.instance_name, 'count': stat.count}
                for stat in database_stats
            ],
            'last_updated': latest_aggregation.calculated_at.isoformat() if latest_aggregation else None
        }
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"获取统计聚合汇总数据时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@aggregations_bp.route('/instance', methods=['GET'])
@login_required
@view_required
def instance_aggregations():
    """
    实例统计聚合页面
    返回HTML页面
    """
    # 获取实例列表
    instances = Instance.query.filter_by(is_active=True).order_by(Instance.name).all()
    instances_list = []
    for instance in instances:
        instances_list.append({
            'id': instance.id,
            'name': instance.name,
            'db_type': instance.db_type,
            'host': instance.host,
            'port': instance.port
        })
    
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


@aggregations_bp.route('/instance/api', methods=['GET'])
@login_required
@view_required
def instance_aggregations_api():
    """
    实例统计聚合API
    返回JSON数据
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        period_type = request.args.get('period_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        time_range = request.args.get('time_range')
        
        # 处理time_range参数，转换为start_date和end_date
        if time_range and not start_date and not end_date:
            from datetime import timedelta
            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=int(time_range))
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        # 是否返回所有数据（用于图表显示）
        get_all = request.args.get('get_all', 'false').lower() == 'true'
        
        # 计算offset
        offset = (page - 1) * per_page
        limit = per_page
        
        # 构建查询 - 查询实例统计聚合表
        from app.models.instance_size_aggregation import InstanceSizeAggregation
        query = InstanceSizeAggregation.query.join(Instance)
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(InstanceSizeAggregation.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if period_type:
            query = query.filter(InstanceSizeAggregation.period_type == period_type)
        if start_date:
            query = query.filter(InstanceSizeAggregation.period_start >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(InstanceSizeAggregation.period_end <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # 排序和分页
        if get_all:
            # 用于图表显示：按总大小排序获取TOP N实例
            # 先按实例分组，获取每个实例的最大容量
            from sqlalchemy import func
            subquery = query.with_entities(
                InstanceSizeAggregation.instance_id,
                func.max(InstanceSizeAggregation.total_size_mb).label('max_total_size_mb')
            ).group_by(InstanceSizeAggregation.instance_id).subquery()
            
            # 获取TOP 100实例的ID
            top_instances = db.session.query(subquery.c.instance_id).order_by(
                desc(subquery.c.max_total_size_mb)
            ).limit(100).all()
            top_instance_ids = [row[0] for row in top_instances]
            
            # 获取这些实例的所有聚合数据
            aggregations = query.filter(
                InstanceSizeAggregation.instance_id.in_(top_instance_ids)
            ).order_by(desc(InstanceSizeAggregation.total_size_mb)).all()
            total = len(aggregations)
        else:
            # 用于表格显示：按时间排序分页
            query = query.order_by(desc(InstanceSizeAggregation.period_start))
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
            # 为了兼容前端，添加 avg_size_mb 字段
            agg_dict['avg_size_mb'] = agg_dict.get('total_size_mb', 0)
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


@aggregations_bp.route('/database', methods=['GET'])
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
            
            # 构建查询 - 直接查询聚合统计表
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
        
        # 获取数据库名称列表
        databases = db.session.query(
            DatabaseSizeAggregation.database_name,
            Instance.name.label('instance_name')
        ).join(Instance).distinct().all()
        databases_list = [{'value': d.database_name, 'label': f"{d.instance_name}.{d.database_name}"} for d in databases]
        
        return render_template('database_sizes/database_aggregations.html',
                             instances=instances_list,
                             database_types=database_types_list,
                             databases=databases_list,
                             db_type=request.args.get('db_type', ''))


@aggregations_bp.route('/instance/summary', methods=['GET'])
@login_required
@view_required
def get_instance_aggregations_summary():
    """
    获取实例统计聚合数据汇总统计
    
    Returns:
        JSON: 汇总统计信息
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        period_type = request.args.get('period_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        time_range = request.args.get('time_range')
        
        # 处理time_range参数，转换为start_date和end_date
        if time_range and not start_date and not end_date:
            from datetime import timedelta
            end_date_obj = datetime.now()
            start_date_obj = end_date_obj - timedelta(days=int(time_range))
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        # 构建查询 - 使用实例统计聚合表
        from app.models.instance_size_aggregation import InstanceSizeAggregation
        query = InstanceSizeAggregation.query.join(Instance)
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(InstanceSizeAggregation.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if period_type:
            query = query.filter(InstanceSizeAggregation.period_type == period_type)
        if start_date:
            query = query.filter(InstanceSizeAggregation.period_start >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(InstanceSizeAggregation.period_end <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # 获取基本统计
        total_aggregations = query.count()
        
        # 获取活跃实例数 - 从筛选后的聚合数据中获取
        if db_type:
            # 当有数据库类型筛选时，从聚合数据中获取实例数
            total_instances = db.session.query(
                func.count(func.distinct(InstanceSizeAggregation.instance_id))
            ).select_from(query.subquery()).scalar() or 0
        else:
            # 没有筛选时，获取所有活跃实例数
            total_instances = Instance.query.filter_by(is_active=True).count()
        
        # 获取数据库数量统计 - 从筛选后的数据获取
        total_databases = db.session.query(
            func.sum(InstanceSizeAggregation.database_count)
        ).select_from(query.subquery()).scalar() or 0
        
        # 获取大小统计 - 从筛选后的数据获取，按实例去重取最新数据
        # 先获取每个实例的最新数据
        latest_data_subquery = db.session.query(
            InstanceSizeAggregation.instance_id,
            func.max(InstanceSizeAggregation.calculated_at).label('latest_calculated_at')
        ).select_from(query.subquery()).group_by(InstanceSizeAggregation.instance_id).subquery()
        
        # 获取每个实例的最新容量数据
        latest_sizes = db.session.query(
            InstanceSizeAggregation.total_size_mb
        ).select_from(query.subquery()).join(
            latest_data_subquery,
            (InstanceSizeAggregation.instance_id == latest_data_subquery.c.instance_id) &
            (InstanceSizeAggregation.calculated_at == latest_data_subquery.c.latest_calculated_at)
        ).all()
        
        # 计算统计值
        if latest_sizes:
            sizes = [row[0] for row in latest_sizes if row[0] is not None]
            total_size = sum(sizes)
            avg_size = total_size / len(sizes) if sizes else 0
            max_size = max(sizes) if sizes else 0
        else:
            total_size = 0
            avg_size = 0
            max_size = 0
        
        # 按周期类型统计 - 使用筛选后的数据
        period_stats = db.session.query(
            InstanceSizeAggregation.period_type,
            func.count(InstanceSizeAggregation.id).label('count')
        ).select_from(query.subquery()).group_by(InstanceSizeAggregation.period_type).all()
        
        # 按实例统计 - 使用筛选后的数据
        instance_stats = db.session.query(
            InstanceSizeAggregation.instance_id,
            Instance.name.label('instance_name'),
            func.count(InstanceSizeAggregation.id).label('count')
        ).select_from(query.subquery()).join(Instance).group_by(
            InstanceSizeAggregation.instance_id, 
            Instance.name
        ).order_by(func.count(InstanceSizeAggregation.id).desc()).limit(10).all()
        
        # 最近更新时间 - 使用筛选后的数据
        latest_aggregation = query.order_by(
            desc(InstanceSizeAggregation.calculated_at)
        ).first()
        
        summary = {
            'total_aggregations': total_aggregations,
            'total_instances': total_instances,
            'total_databases': total_databases,
            'total_size_mb': total_size,
            'avg_size_mb': float(avg_size),
            'max_size_mb': max_size,
            'period_stats': [{'period_type': p.period_type, 'count': p.count} for p in period_stats],
            'instance_stats': [{'instance_name': i.instance_name, 'count': i.count} for i in instance_stats],
            'last_update': latest_aggregation.calculated_at.isoformat() if latest_aggregation else None
        }
        
        # 添加调试日志
        logger.info(f"API响应数据: db_type={db_type}, total_instances={total_instances}, total_size_mb={total_size}")
        
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


@aggregations_bp.route('/database/summary', methods=['GET'])
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


# 聚合统计管理相关API

@aggregations_bp.route('/manual_aggregate', methods=['POST'])
@login_required
@view_required
def manual_aggregate():
    """
    手动触发聚合计算
    
    Returns:
        JSON: 聚合结果
    """
    try:
        # 触发聚合任务
        result = calculate_database_size_aggregations()
        
        return jsonify({
            'success': True,
            'message': '手动聚合任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"手动聚合时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@aggregations_bp.route('/aggregate', methods=['POST'])
@login_required
@view_required
def calculate_aggregations():
    """
    手动触发统计聚合计算
    
    Returns:
        JSON: 聚合结果
    """
    try:
        # 执行聚合计算
        aggregation_service = DatabaseSizeAggregationService()
        result = aggregation_service.calculate_all_aggregations()
        
        return jsonify({
            'message': 'Database size aggregation completed',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"手动统计聚合时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@aggregations_bp.route('/aggregate-today', methods=['POST'])
@login_required
@view_required
def calculate_today_aggregations():
    """
    手动触发今日数据聚合计算
    
    Returns:
        JSON: 聚合结果
    """
    try:
        # 执行今日数据聚合计算
        aggregation_service = DatabaseSizeAggregationService()
        
        # 计算数据库聚合
        database_result = aggregation_service.calculate_today_aggregations()
        
        # 计算实例聚合
        instance_result = aggregation_service.calculate_today_instance_aggregations()
        
        return jsonify({
            'message': 'Today data aggregation completed',
            'database_result': database_result,
            'instance_result': instance_result
        })
        
    except Exception as e:
        logger.error(f"手动计算今日数据聚合时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@aggregations_bp.route('/aggregate/status', methods=['GET'])
@login_required
@view_required
def get_aggregation_status_api():
    """
    获取聚合状态信息
    
    Returns:
        JSON: 状态信息
    """
    try:
        result = get_aggregation_status()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': time_utils.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取聚合状态时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@aggregations_bp.route('/instances/<int:instance_id>/database-sizes/aggregations', methods=['GET'])
@login_required
@view_required
def get_instance_database_aggregations(instance_id: int):
    """
    获取指定实例的数据库大小统计聚合数据
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 统计聚合数据
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取查询参数
        period_type = request.args.get('period_type', 'monthly')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        database_name = request.args.get('database_name')
        
        # 验证周期类型
        if period_type not in ['weekly', 'monthly', 'quarterly']:
            return jsonify({'error': 'Invalid period_type. Must be weekly, monthly, or quarterly'}), 400
        
        # 解析日期
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        
        # 获取聚合数据
        aggregation_service = DatabaseSizeAggregationService()
        data = aggregation_service.get_aggregations(
            instance_id=instance_id,
            period_type=period_type,
            start_date=start_date_obj,
            end_date=end_date_obj,
            database_name=database_name
        )
        
        return jsonify({
            'data': data,
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port
            },
            'period_type': period_type
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 统计聚合数据时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
