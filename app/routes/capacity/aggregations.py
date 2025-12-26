"""Capacity 域: 聚合统计路由."""

from __future__ import annotations

from flask import Blueprint, Response, request
from flask_login import login_required
from flask_restx import marshal

from app.errors import ValidationError
from app.routes.capacity.restx_models import CAPACITY_CURRENT_AGGREGATION_RESPONSE_FIELDS
from app.services.capacity.current_aggregation_service import CurrentAggregationService
from app.types.capacity_aggregations import CurrentAggregationRequest
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_error, jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call

# 创建蓝图
capacity_aggregations_bp = Blueprint("capacity_aggregations", __name__)

# 聚合模块专注于核心聚合功能, 不包含页面路由

@capacity_aggregations_bp.route("/api/aggregations/current", methods=["POST"])
@login_required
@view_required
@require_csrf
def aggregate_current() -> tuple[Response, int]:
    """手动触发当前周期数据聚合.

    Returns:
        Response: 包含聚合结果的 JSON 响应.

    """
    payload = request.get_json(silent=True) or {}
    aggregation_request = CurrentAggregationRequest(
        requested_period_type=(payload.get("period_type") or "daily").lower(),
        scope=(payload.get("scope") or "all").lower(),
    )
    context_snapshot = {
        "requested_period_type": aggregation_request.requested_period_type,
        "scope": aggregation_request.scope,
        "payload_keys": list(payload.keys()),
    }

    def _execute() -> tuple[Response, int]:
        try:
            result = CurrentAggregationService().aggregate_current(aggregation_request)
        except ValidationError:
            raise
        except Exception as exc:
            log_with_context(
                "error",
                "触发当前周期数据聚合失败",
                module="capacity_aggregations",
                action="aggregate_current",
                context=context_snapshot,
                extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
            )
            return jsonify_unified_error(exc)
        else:
            payload = marshal({"result": result}, CAPACITY_CURRENT_AGGREGATION_RESPONSE_FIELDS)
            return jsonify_unified_success(
                data=payload,
                message="已仅聚合今日数据",
            )

    return safe_route_call(
        _execute,
        module="capacity_aggregations",
        action="aggregate_current",
        public_error="触发当前周期数据聚合失败",
        expected_exceptions=(ValidationError,),
        context=context_snapshot,
    )
