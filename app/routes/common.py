"""
通用 API 路由
提供跨模块使用的通用接口
"""

from flask import Blueprint, Response, request
from flask_login import login_required
from sqlalchemy import func

from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.errors import ValidationError, SystemError
from app.services.database_type_service import DatabaseTypeService
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
common_bp = Blueprint('common', __name__)


@common_bp.route('/api/instances-options', methods=['GET'])
@login_required
@view_required
def get_instance_options() -> Response:
    """
    获取实例下拉选项（通用）
    
    支持按数据库类型筛选，用于各统计页面的实例选择器
    
    Query Parameters:
        db_type: 数据库类型（可选），如 mysql, postgresql, sqlserver, oracle
        
    Returns:
        JSON: {
            "instances": [
                {
                    "id": 1,
                    "name": "实例名称",
                    "db_type": "mysql",
                    "display_name": "实例名称 (MYSQL)"
                }
            ]
        }
        
    Used by:
        - database_aggregations.js (数据库聚合统计页面)
        - instance_aggregations.js (实例聚合统计页面)
    """
    try:
        db_type = request.args.get('db_type')

        query = Instance.query.filter(Instance.is_active.is_(True))
        if db_type:
            db_type_lower = db_type.lower()
            query = query.filter(func.lower(Instance.db_type) == db_type_lower)

        instances = query.order_by(Instance.name.asc()).all()

        options = [
            {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'display_name': f"{instance.name} ({instance.db_type.upper()})",
            }
            for instance in instances
        ]

        log_info("加载实例选项成功", module="common", count=len(options), db_type=db_type)
        return jsonify_unified_success(data={'instances': options}, message="实例选项获取成功")

    except Exception as exc:
        log_error("加载实例选项失败", module="common", error=str(exc))
        raise SystemError("加载实例选项失败") from exc


@common_bp.route('/api/databases-options', methods=['GET'])
@login_required
@view_required
def get_database_options() -> Response:
    """
    获取指定实例的数据库下拉选项（通用）

    Query Parameters:
        instance_id: 实例ID（必填）
        limit: 返回数量（可选，默认100）
        offset: 偏移量（可选，默认0）

    Returns:
        JSON: {
            "databases": [
                {
                    "id": 1,
                    "database_name": "数据库名称",
                    "is_active": true,
                    ...
                }
            ],
            "total_count": 10,
            "limit": 100,
            "offset": 0
        }
    """
    instance_id = request.args.get('instance_id', type=int)
    if not instance_id:
        raise ValidationError("instance_id 为必填参数")

    Instance.query.get_or_404(instance_id)

    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
    except ValueError as exc:
        raise ValidationError('limit/offset 必须为整数') from exc

    try:
        query = (
            InstanceDatabase.query.filter(InstanceDatabase.instance_id == instance_id)
            .order_by(InstanceDatabase.database_name)
        )
        total_count = query.count()
        databases = query.offset(offset).limit(limit).all()
    except Exception as exc:
        log_error(
            "获取实例数据库列表失败",
            module="common",
            instance_id=instance_id,
            error=str(exc),
        )
        raise SystemError("获取实例数据库列表失败") from exc

    data = [
        {
            'id': db.id,
            'database_name': db.database_name,
            'is_active': db.is_active,
            'first_seen_date': db.first_seen_date.isoformat() if db.first_seen_date else None,
            'last_seen_date': db.last_seen_date.isoformat() if db.last_seen_date else None,
            'deleted_at': db.deleted_at.isoformat() if db.deleted_at else None,
        }
        for db in databases
    ]

    payload = {
        'databases': data,
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
    }

    log_info(
        "加载数据库选项成功",
        module="common",
        instance_id=instance_id,
        count=len(data),
    )
    return jsonify_unified_success(data=payload, message="数据库选项获取成功")


@common_bp.route('/api/dbtypes-options', methods=['GET'])
@login_required
@view_required
def get_database_type_options() -> Response:
    """
    获取数据库类型选项（通用）

    Returns:
        JSON: { "database_types": [...] }
    """
    try:
        options = DatabaseTypeService.get_database_types_for_form()
        log_info("加载数据库类型选项成功", module="common", count=len(options))
        return jsonify_unified_success(data={"options": options}, message="数据库类型选项获取成功")
    except Exception as exc:
        log_error("加载数据库类型选项失败", module="common", error=str(exc))
        raise SystemError("加载数据库类型选项失败") from exc
