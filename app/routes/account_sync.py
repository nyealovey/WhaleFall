"""
鲸落 - 账户同步路由
提供账户同步记录的统一管理界面，支持分页、筛选、聚合显示
实现批量同步所有实例账户的功能，使用会话管理架构
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import and_, desc, func

from app.models.instance import Instance
from app.models.sync_session import SyncSession
from app.models.sync_instance_record import SyncInstanceRecord
from app.services.account_sync_service import account_sync_service
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import update_required, view_required
from app.utils.structlog_config import log_error, log_info
from app.utils.timezone import now
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
account_sync_bp = Blueprint('account_sync', __name__)


@account_sync_bp.route('/')
@login_required
@view_required
def index() -> str:
    """账户同步记录列表页面"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        sync_type = request.args.get('sync_type', '').strip()
        status = request.args.get('status', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        
        # 构建查询
        query = SyncSession.query
        
        # 同步类型过滤
        if sync_type and sync_type != 'all':
            query = query.filter(SyncSession.sync_type == sync_type)
        
        # 状态过滤
        if status and status != 'all':
            query = query.filter(SyncSession.status == status)
        
        # 时间范围过滤
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(SyncSession.created_at >= start_datetime)
            except ValueError:
                log_error(f"无效的开始日期格式: {start_date}", module="account_sync")
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(SyncSession.created_at < end_datetime)
            except ValueError:
                log_error(f"无效的结束日期格式: {end_date}", module="account_sync")
        
        # 排序
        query = query.order_by(desc(SyncSession.created_at))
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取实例列表用于筛选
        instances = Instance.query.filter_by(is_active=True).order_by(Instance.id).all()
        instances_list = []
        for instance in instances:
            instances_list.append({
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type
            })
        
        return render_template('accounts/sync_records.html',
                             pagination=pagination,
                             instances_list=instances_list,
                             sync_type=sync_type,
                             status=status,
                             start_date=start_date,
                             end_date=end_date)
        
    except Exception as e:
        log_error(f"获取账户同步记录失败: {str(e)}", module="account_sync")
        return render_template('accounts/sync_records.html', 
                             error="获取同步记录失败")


@account_sync_bp.route('/sync-all', methods=['POST'])
@login_required
@update_required
def sync_all_accounts() -> Response:
    """批量同步所有实例的账户"""
    try:
        log_info(
            "开始批量同步所有实例账户",
            module="account_sync",
            user_id=current_user.id,
        )
        
        # 创建同步会话
        session_result = sync_session_service.create_session(
            sync_type="manual_batch",
            sync_category="account_sync",
            created_by=current_user.id,
            description="批量同步所有实例账户"
        )
        
        if not session_result.get("success"):
            return jsonify({
                "success": False,
                "error": f"创建同步会话失败: {session_result.get('error')}"
            }), 500
        
        session_id = session_result["session_id"]
        
        # 获取所有活跃实例
        instances = Instance.query.filter_by(is_active=True).all()
        
        if not instances:
            return jsonify({
                "success": False,
                "error": "没有找到活跃的数据库实例"
            }), 400
        
        # 为每个实例创建记录
        instance_records = []
        for instance in instances:
            record_result = sync_session_service.add_instance_records(
                session_id=session_id,
                instance_ids=[instance.id],
                sync_type="manual_batch"
            )
            
            if record_result.get("success"):
                instance_records.extend(record_result.get("records", []))
            else:
                log_error(
                    f"为实例 {instance.name} 创建同步记录失败",
                    module="account_sync",
                    instance_id=instance.id,
                    error=record_result.get("error")
                )
        
        # 开始同步每个实例
        success_count = 0
        failed_count = 0
        total_accounts = 0
        total_added = 0
        total_updated = 0
        total_deleted = 0
        
        for instance in instances:
            try:
                # 标记实例开始同步
                sync_session_service.start_instance_sync(session_id, instance.id)
                
                # 执行账户同步
                sync_result = account_sync_service.sync_accounts(
                    instance=instance,
                    sync_type="manual_batch",
                    session_id=session_id,
                    created_by=current_user.id
                )
                
                if sync_result.get("success"):
                    success_count += 1
                    total_accounts += sync_result.get("total_accounts", 0)
                    total_added += sync_result.get("added_accounts", 0)
                    total_updated += sync_result.get("updated_accounts", 0)
                    total_deleted += sync_result.get("deleted_accounts", 0)
                    
                    # 标记实例同步完成
                    sync_session_service.complete_instance_sync(
                        session_id, 
                        instance.id,
                        sync_result
                    )
                    
                    log_info(
                        f"实例 {instance.name} 同步成功",
                        module="account_sync",
                        instance_id=instance.id,
                        total_accounts=sync_result.get("total_accounts", 0),
                        added_accounts=sync_result.get("added_accounts", 0),
                        updated_accounts=sync_result.get("updated_accounts", 0),
                        deleted_accounts=sync_result.get("deleted_accounts", 0)
                    )
                else:
                    failed_count += 1
                    error_msg = sync_result.get("error", "未知错误")
                    
                    # 标记实例同步失败
                    sync_session_service.fail_instance_sync(
                        session_id,
                        instance.id,
                        error_msg
                    )
                    
                    log_error(
                        f"实例 {instance.name} 同步失败",
                        module="account_sync",
                        instance_id=instance.id,
                        error=error_msg
                    )
                    
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                
                # 标记实例同步失败
                sync_session_service.fail_instance_sync(
                    session_id,
                    instance.id,
                    error_msg
                )
                
                log_error(
                    f"实例 {instance.name} 同步异常",
                    module="account_sync",
                    instance_id=instance.id,
                    exception=e
                )
        
        # 更新会话统计
        sync_session_service.update_session_statistics(
            session_id=session_id,
            total_instances=len(instances),
            success_instances=success_count,
            failed_instances=failed_count,
            total_accounts=total_accounts,
            added_accounts=total_added,
            updated_accounts=total_updated,
            deleted_accounts=total_deleted
        )
        
        # 记录操作日志
        log_info(
            f"批量同步完成: 成功 {success_count} 个实例，失败 {failed_count} 个实例",
            module="account_sync",
            session_id=session_id,
            total_instances=len(instances),
            success_count=success_count,
            failed_count=failed_count,
            total_accounts=total_accounts,
            total_added=total_added,
            total_updated=total_updated,
            total_deleted=total_deleted
        )
        
        return jsonify({
            "success": True,
            "message": f"批量同步完成: 成功 {success_count} 个实例，失败 {failed_count} 个实例",
            "data": {
                "session_id": session_id,
                "total_instances": len(instances),
                "success_count": success_count,
                "failed_count": failed_count,
                "total_accounts": total_accounts,
                "added_accounts": total_added,
                "updated_accounts": total_updated,
                "deleted_accounts": total_deleted
            }
        })
        
    except Exception as e:
        log_error(
            f"批量同步异常: {str(e)}",
            module="account_sync",
            exception=e
        )
        return jsonify({
            "success": False,
            "error": f"批量同步失败: {str(e)}"
        }), 500


@account_sync_bp.route('/sync-details-batch', methods=['GET'])
@login_required
@view_required
def get_batch_sync_details() -> Response:
    """获取批量同步详情"""
    try:
        record_ids = request.args.getlist('record_ids')
        
        if not record_ids:
            return jsonify({
                "success": False,
                "error": "缺少记录ID参数"
            }), 400
        
        # 获取同步记录
        records = SyncInstanceRecord.query.filter(
            SyncInstanceRecord.id.in_(record_ids)
        ).all()
        
        # 按实例去重
        instance_details = {}
        for record in records:
            instance_id = record.instance_id
            if instance_id not in instance_details:
                instance_details[instance_id] = {
                    "instance_id": instance_id,
                    "instance_name": record.instance.name if record.instance else "未知实例",
                    "db_type": record.instance.db_type if record.instance else "未知",
                    "status": record.status,
                    "start_time": record.start_time.isoformat() if record.start_time else None,
                    "end_time": record.end_time.isoformat() if record.end_time else None,
                    "total_accounts": record.total_accounts or 0,
                    "added_accounts": record.added_accounts or 0,
                    "updated_accounts": record.updated_accounts or 0,
                    "deleted_accounts": record.deleted_accounts or 0,
                    "error_message": record.error_message
                }
        
        return jsonify({
            "success": True,
            "data": list(instance_details.values())
        })
        
    except Exception as e:
        log_error(f"获取批量同步详情失败: {str(e)}", module="account_sync")
        return jsonify({
            "success": False,
            "error": f"获取同步详情失败: {str(e)}"
        }), 500


@account_sync_bp.route('/sync-details/<session_id>', methods=['GET'])
@login_required
@view_required
def get_sync_details(session_id: str) -> Response:
    """获取同步会话详情"""
    try:
        # 获取同步会话
        session = SyncSession.query.filter_by(session_id=session_id).first()
        
        if not session:
            return jsonify({
                "success": False,
                "error": "同步会话不存在"
            }), 404
        
        # 获取关联的实例记录
        instance_records = SyncInstanceRecord.query.filter_by(
            session_id=session_id
        ).all()
        
        # 构建详情数据
        details = {
            "session": {
                "session_id": session.session_id,
                "sync_type": session.sync_type,
                "sync_category": session.sync_category,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "total_instances": session.total_instances or 0,
                "success_instances": session.success_instances or 0,
                "failed_instances": session.failed_instances or 0,
                "total_accounts": session.total_accounts or 0,
                "added_accounts": session.added_accounts or 0,
                "updated_accounts": session.updated_accounts or 0,
                "deleted_accounts": session.deleted_accounts or 0,
                "description": session.description
            },
            "instance_records": []
        }
        
        for record in instance_records:
            details["instance_records"].append({
                "id": record.id,
                "instance_id": record.instance_id,
                "instance_name": record.instance.name if record.instance else "未知实例",
                "db_type": record.instance.db_type if record.instance else "未知",
                "status": record.status,
                "start_time": record.start_time.isoformat() if record.start_time else None,
                "end_time": record.end_time.isoformat() if record.end_time else None,
                "total_accounts": record.total_accounts or 0,
                "added_accounts": record.added_accounts or 0,
                "updated_accounts": record.updated_accounts or 0,
                "deleted_accounts": record.deleted_accounts or 0,
                "error_message": record.error_message
            })
        
        return jsonify({
            "success": True,
            "data": details
        })
        
    except Exception as e:
        log_error(f"获取同步会话详情失败: {str(e)}", module="account_sync")
        return jsonify({
            "success": False,
            "error": f"获取同步详情失败: {str(e)}"
        }), 500


@account_sync_bp.route('/instances/<int:instance_id>/sync', methods=['POST'])
@login_required
@update_required
def sync_instance_accounts(instance_id: int) -> Response:
    """同步指定实例的账户"""
    try:
        # 获取实例
        instance = Instance.query.get_or_404(instance_id)
        
        log_info(
            f"开始同步实例 {instance.name} 的账户",
            module="account_sync",
            instance_id=instance_id,
            user_id=current_user.id,
        )
        
        # 执行账户同步
        sync_result = account_sync_service.sync_accounts(
            instance=instance,
            sync_type="manual_single",
            created_by=current_user.id
        )
        
        if sync_result.get("success"):
            # 更新实例同步计数
            instance.sync_count = (instance.sync_count or 0) + 1
            instance.last_sync_time = now()
            db.session.commit()
            
            log_info(
                f"实例 {instance.name} 同步成功",
                module="account_sync",
                instance_id=instance_id,
                total_accounts=sync_result.get("total_accounts", 0),
                added_accounts=sync_result.get("added_accounts", 0),
                updated_accounts=sync_result.get("updated_accounts", 0),
                deleted_accounts=sync_result.get("deleted_accounts", 0)
            )
            
            return jsonify({
                "success": True,
                "message": f"实例 {instance.name} 同步成功",
                "data": sync_result
            })
        else:
            error_msg = sync_result.get("error", "未知错误")
            
            log_error(
                f"实例 {instance.name} 同步失败",
                module="account_sync",
                instance_id=instance_id,
                error=error_msg
            )
            
            return jsonify({
                "success": False,
                "error": f"同步失败: {error_msg}"
            }), 500
            
    except Exception as e:
        log_error(
            f"同步实例 {instance_id} 异常: {str(e)}",
            module="account_sync",
            instance_id=instance_id,
            exception=e
        )
        return jsonify({
            "success": False,
            "error": f"同步失败: {str(e)}"
        }), 500
