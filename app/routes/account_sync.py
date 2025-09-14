"""
泰摸鱼吧 - 账户同步记录路由
"""

from collections import defaultdict
from collections.abc import Generator
from typing import Any

from flask import (
    Blueprint,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.models.instance import Instance
from app.models.sync_session import SyncSession
from app.services.account_sync_service import account_sync_service
from app.utils.decorators import view_required
from app.utils.structlog_config import get_api_logger, log_error, log_info, log_warning

# 创建蓝图
account_sync_bp = Blueprint("account_sync", __name__)


@account_sync_bp.route("/")
@login_required
@view_required
def sync_records() -> str | Response:
    """统一的同步记录页面"""
    # 获取查询参数
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sync_type = request.args.get("sync_type", "all")
    status = request.args.get("status", "all")
    instance_id = request.args.get("instance_id", type=int)

    # 构建查询 - 使用新的同步会话模型
    query = SyncSession.query.filter_by(sync_category="account")

    # 同步类型过滤
    if sync_type and sync_type != "all":
        query = query.filter(SyncSession.sync_type == sync_type)

    # 状态过滤
    if status and status != "all":
        query = query.filter(SyncSession.status == status)

    # 排序
    query = query.order_by(SyncSession.created_at.desc())

    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 获取实例列表用于过滤
    instances = Instance.query.filter_by(is_active=True).all()

    # 聚合显示逻辑 - 当同步类型是手动批量或定时任务时，需要聚合显示
    # 获取所有记录进行聚合处理，然后手动分页
    all_records = query.order_by(SyncSession.created_at.desc()).all()

    # 分离需要聚合的记录和单独显示的记录
    # task类型的记录已经是聚合记录，不需要再次聚合
    batch_records = [r for r in all_records if r.sync_type == "batch"]
    task_records = [r for r in all_records if r.sync_type == "task"]
    manual_records = [r for r in all_records if r.sync_type == "manual"]

    # 聚合batch类型的记录（task类型已经是聚合记录，不需要再次聚合）
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total_instances": 0,
            "success_count": 0,
            "failed_count": 0,
            "total_accounts": 0,
            "added_count": 0,
            "removed_count": 0,
            "modified_count": 0,
            "created_at": None,
            "sync_records": [],
            "sync_types": [],
            "sync_type_display": "",
        }
    )

    for record in batch_records:
        # 使用分钟级精度作为分组键，相同分钟的同步记录为一组
        time_key = record.sync_time.strftime("%Y-%m-%d %H:%M")

        # 按实例去重，只计算每个实例的最新记录
        instance_key = f"{time_key}_{record.instance_id}"
        if instance_key not in grouped[time_key].get("instance_tracker", {}):
            if "instance_tracker" not in grouped[time_key]:
                grouped[time_key]["instance_tracker"] = {}

            grouped[time_key]["instance_tracker"][instance_key] = record
            grouped[time_key]["total_instances"] += 1

            if record.status == "success":
                grouped[time_key]["success_count"] += 1
            else:
                grouped[time_key]["failed_count"] += 1

            # 只累加一次每个实例的数量
            grouped[time_key]["total_accounts"] += record.synced_count or 0
            grouped[time_key]["added_count"] += record.added_count or 0
            grouped[time_key]["removed_count"] += record.removed_count or 0
            grouped[time_key]["modified_count"] += record.modified_count or 0

            if record.sync_type not in grouped[time_key]["sync_types"]:
                grouped[time_key]["sync_types"].append(record.sync_type)

            if not grouped[time_key]["created_at"] or record.sync_time > grouped[time_key]["created_at"]:
                grouped[time_key]["created_at"] = record.sync_time

        # 始终添加记录到sync_records，用于详情显示
        grouped[time_key]["sync_records"].append(record)

    # 转换为聚合记录列表
    aggregated_records = []
    for time_key, data in sorted(grouped.items(), key=lambda x: x[1]["created_at"], reverse=True):
        # 使用最新记录的时间作为显示时间
        latest_time = max(record.sync_time for record in data["sync_records"])

        # 确定同步类型显示文本 - 直接显示原始值
        sync_types = data["sync_types"]
        if len(sync_types) == 1:
            sync_type_display = sync_types[0]  # 直接显示原始值
        else:
            sync_type_display = " + ".join(sync_types)  # 多个类型用+连接

        # 创建聚合记录对象
        class AggregatedRecord:
            def __init__(self, data: dict[str, Any], latest_time: Any, sync_type_display: str) -> None:
                self.sync_time = latest_time
                self.sync_type = sync_type_display
                self.status = "success" if data["failed_count"] == 0 else "failed"
                self.synced_count = data["total_accounts"]
                self.added_count = data["added_count"]
                self.removed_count = data["removed_count"]
                self.modified_count = data["modified_count"]
                self.message = (
                    f"成功同步 {data['total_accounts']} 个账户"
                    if data["failed_count"] == 0
                    else f"部分失败，成功 {data['success_count']} 个实例，失败 {data['failed_count']} 个实例"
                )
                self.instance = None  # 聚合记录没有单一实例
                self.sync_records = data["sync_records"]  # 保存原始记录用于详情查看
                self.is_aggregated = True

            def get_record_ids(self) -> list[int]:
                """获取记录ID列表"""
                return [record.id for record in self.sync_records]

        aggregated_records.append(AggregatedRecord(data, latest_time, sync_type_display))

    # 处理手动记录，直接显示原始值
    for record in manual_records:
        record.is_aggregated = False

    # 处理task记录，直接显示原始值（已经是聚合记录）
    for record in task_records:
        record.is_aggregated = False

    # 合并聚合记录、手动记录和task记录
    all_display_records = aggregated_records + manual_records + task_records

    # 按时间排序
    all_display_records.sort(key=lambda x: x.sync_time, reverse=True)

    # 手动分页
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_records = all_display_records[start_idx:end_idx]

    # 创建分页对象
    class Pagination:
        def __init__(self, items: list[Any], page: int, per_page: int, total: int) -> None:
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if page > 1 else None
            self.next_num = page + 1 if page < self.pages else None

        def iter_pages(
            self,
            left_edge: int = 2,
            right_edge: int = 2,
            left_current: int = 2,
            right_current: int = 3,
        ) -> Generator[int | None]:
            """生成分页页码迭代器，与Flask-SQLAlchemy的Pagination兼容"""
            last = self.pages
            for num in range(1, last + 1):
                if (
                    num <= left_edge
                    or (num > self.page - left_current - 1 and num < self.page + right_current)
                    or num > last - right_edge
                ):
                    yield num

    sync_records = Pagination(paginated_records, page, per_page, len(all_display_records))

    if request.is_json:
        return jsonify(
            {
                "records": [
                    (
                        record.to_dict()
                        if hasattr(record, "to_dict")
                        else {
                            "id": getattr(record, "id", f"batch_{hash(str(record.sync_time))}"),
                            "sync_time": (record.sync_time.isoformat() if record.sync_time else None),
                            "sync_type": record.sync_type,
                            "status": record.status,
                            "message": record.message,
                            "synced_count": record.synced_count,
                            "instance_name": getattr(record, "instance_name", "批量同步"),
                            "is_aggregated": getattr(record, "is_aggregated", False),
                            "record_ids": getattr(record, "sync_records", []),
                        }
                    )
                    for record in sync_records.items
                ],
                "pagination": {
                    "page": sync_records.page,
                    "pages": sync_records.pages,
                    "per_page": sync_records.per_page,
                    "total": sync_records.total,
                    "has_next": sync_records.has_next,
                    "has_prev": sync_records.has_prev,
                },
                "instances": [instance.to_dict() for instance in instances],
            }
        )

    return render_template(
        "accounts/sync_records.html",
        sync_records=sync_records,
        pagination=sync_records,
        sync_type=sync_type,
        status=status,
        instance_id=instance_id,
        instances=instances,
    )


@account_sync_bp.route("/sync-all", methods=["POST"])
@login_required
def sync_all_accounts() -> str | Response | tuple[Response, int]:
    """同步所有实例的账户（使用新的会话管理架构）"""
    from app.services.sync_session_service import sync_session_service

    try:
        log_info("开始同步所有账户", module="account_sync", user_id=current_user.id)

        # 获取所有活跃实例
        instances = Instance.query.filter_by(is_active=True).all()

        if not instances:
            log_warning(
                "没有找到活跃的数据库实例",
                module="account_sync",
                user_id=current_user.id,
            )
            return jsonify({"success": False, "error": "没有找到活跃的数据库实例"}), 400

        # 创建同步会话
        session = sync_session_service.create_session(
            sync_type="manual_batch",
            sync_category="account",
            created_by=current_user.id,
        )

        log_info(
            "创建手动批量同步会话",
            module="account_sync",
            session_id=session.session_id,
            user_id=current_user.id,
            instance_count=len(instances),
        )

        # 添加实例记录
        instance_ids = [inst.id for inst in instances]
        records = sync_session_service.add_instance_records(session.session_id, instance_ids)

        success_count = 0
        failed_count = 0
        results = []

        for instance in instances:
            # 找到对应的记录
            record = next((r for r in records if r.instance_id == instance.id), None)
            if not record:
                continue

            try:
                # 开始实例同步
                sync_session_service.start_instance_sync(record.id)

                log_info(
                    f"开始同步实例: {instance.name}",
                    module="account_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                )

                # 使用统一的账户同步服务
                result = account_sync_service.sync_accounts(instance, sync_type="batch", session_id=session.session_id)

                if result["success"]:
                    success_count += 1

                    # 完成实例同步
                    sync_session_service.complete_instance_sync(
                        record.id,
                        accounts_synced=result.get("synced_count", 0),
                        accounts_created=result.get("added_count", 0),
                        accounts_updated=result.get("modified_count", 0),
                        accounts_deleted=result.get("removed_count", 0),
                        sync_details=result.get("details", {}),
                    )

                    log_info(
                        f"实例同步成功: {instance.name}",
                        module="account_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        synced_count=result.get("synced_count", 0),
                    )

                    # 同步会话记录已通过sync_session_service管理，无需额外创建记录
                else:
                    failed_count += 1

                    # 标记实例同步失败
                    sync_session_service.fail_instance_sync(
                        record.id,
                        error_message=result.get("error", "同步失败"),
                        sync_details=result.get("details", {}),
                    )

                    log_error(
                        f"实例同步失败: {instance.name}",
                        module="account_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        error=result.get("error", "同步失败"),
                    )

                    # 同步会话记录已通过sync_session_service管理，无需额外创建记录

                results.append(
                    {
                        "instance_name": instance.name,
                        "success": result["success"],
                        "message": result.get("message", result.get("error", "未知错误")),
                        "synced_count": result.get("synced_count", 0),
                    }
                )

            except Exception as e:
                failed_count += 1

                # 标记实例同步失败
                if record:
                    sync_session_service.fail_instance_sync(
                        record.id,
                        error_message=str(e),
                        sync_details={"exception": str(e)},
                    )

                log_error(
                    f"实例同步异常: {instance.name}",
                    module="account_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                    error=str(e),
                )

                # 同步会话记录已通过sync_session_service管理，无需额外创建记录

                results.append(
                    {
                        "instance_name": instance.name,
                        "success": False,
                        "message": f"同步失败: {str(e)}",
                        "synced_count": 0,
                    }
                )

        # 提交所有同步记录
        db.session.commit()

        # 记录同步完成日志
        log_info(
            f"批量同步完成: 成功 {success_count} 个实例，失败 {failed_count} 个实例",
            module="account_sync",
            session_id=session.session_id,
            user_id=current_user.id,
            total_instances=len(instances),
            success_count=success_count,
            failed_count=failed_count,
        )

        # 记录操作日志
        api_logger = get_api_logger()
        api_logger.info(
            "批量同步账户完成",
            module="account_sync",
            operation_type="BATCH_SYNC_ACCOUNTS_COMPLETE",
            session_id=session.session_id,
            user_id=current_user.id,
            total_instances=len(instances),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
        )

        return jsonify(
            {
                "success": True,
                "message": f"批量同步完成，成功 {success_count} 个实例，失败 {failed_count} 个实例",
                "total_instances": len(instances),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results,
            }
        )

    except Exception as e:
        # 记录详细的错误日志
        api_logger = get_api_logger()
        api_logger.error(
            "同步所有账户失败",
            module="account_sync",
            operation="sync_all_accounts",
            user_id=current_user.id if current_user else None,
            exception=str(e),
        )

        return (
            jsonify(
                {
                    "success": False,
                    "error": f"批量同步失败: {str(e)}",
                }
            ),
            500,
        )


@account_sync_bp.route("/sync-details-batch", methods=["GET"])
@login_required
def sync_details_batch() -> str | Response | tuple[Response, int]:
    """获取批量同步详情"""
    try:
        record_ids = request.args.get("record_ids", "").split(",")
        record_ids = [int(rid) for rid in record_ids if rid.strip()]  # type: ignore

        if not record_ids:
            return jsonify({"success": False, "error": "没有提供记录ID"}), 400

        # 获取同步记录 - 使用新的同步会话模型
        records = SyncSession.query.filter(SyncSession.id.in_(record_ids)).all()

        if not records:
            return jsonify({"success": False, "error": "没有找到同步记录"}), 404

        # 构建详情数据，按实例去重，只保留最新的记录
        details = []
        instance_records = {}

        for record in records:
            if record.instance_id is None:
                # 聚合记录：从data.results中提取每个实例的详细信息
                if record.data and "results" in record.data:
                    for result in record.data["results"]:
                        instance_name = result.get("instance_name", "未知实例")
                        instance_records[instance_name] = {
                            "id": record.id,
                            "instance_name": instance_name,
                            "status": ("success" if result.get("success", False) else "failed"),
                            "message": result.get("message", ""),
                            "synced_count": result.get("synced_count", 0),
                            "sync_time": record.sync_time,
                        }
            else:
                # 单个实例记录
                instance = Instance.query.get(record.instance_id)
                instance_name = instance.name if instance else "未知实例"

                # 如果这个实例还没有记录，或者当前记录更新，则保存
                if (
                    instance_name not in instance_records
                    or record.sync_time > instance_records[instance_name]["sync_time"]
                ):
                    instance_records[instance_name] = {
                        "id": record.id,
                        "instance_name": instance_name,
                        "status": record.status,
                        "message": record.message,
                        "synced_count": record.synced_count,
                        "sync_time": record.sync_time,
                    }

        # 转换为列表并按实例名称排序
        details = list(instance_records.values())
        details.sort(key=lambda x: x["instance_name"])

        # 转换时间格式
        for detail in details:
            if detail["sync_time"]:
                detail["sync_time"] = detail["sync_time"].isoformat()
            else:
                detail["sync_time"] = None

        return jsonify(
            {
                "success": True,
                "details": details,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"获取同步详情失败: {str(e)}"}), 500


@account_sync_bp.route("/sync-details/<sync_id>")
@login_required
def sync_details(sync_id: int) -> str | Response | tuple[Response, int]:
    """同步详情页面"""
    try:
        record = SyncSession.query.get_or_404(sync_id)
        # 获取会话关联的实例记录
        instance_records = record.instance_records.all()
        instances = [Instance.query.get(ir.instance_id) for ir in instance_records if ir.instance_id]

        if request.is_json:
            return jsonify(
                {
                    "success": True,
                    "record": record.to_dict(),
                    "instances": [inst.to_dict() for inst in instances if inst],
                    "instance_records": [ir.to_dict() for ir in instance_records],
                }
            )

        return render_template(
            "accounts/sync_details.html",
            record=record,
            instances=instances,
            instance_records=instance_records,
        )

    except Exception as e:
        if request.is_json:
            return (
                jsonify({"success": False, "error": f"获取同步详情失败: {str(e)}"}),
                500,
            )

        flash(f"获取同步详情失败: {str(e)}", "error")
        return redirect(url_for("account_sync.sync_records"))
