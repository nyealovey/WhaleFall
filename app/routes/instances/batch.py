"""Instances 域：批量创建与删除路由。"""

from __future__ import annotations

import csv
import io
from typing import Any

from flask import Blueprint, Response, request
from flask_login import current_user, login_required

from app import db
from app.constants import HttpStatus
from app.constants.import_templates import (
    INSTANCE_IMPORT_REQUIRED_FIELDS,
    INSTANCE_IMPORT_TEMPLATE_HEADERS,
)
from app.constants.system_constants import ErrorCategory
from app.errors import SystemError, ValidationError
from app.services.instances import InstanceBatchCreationService, InstanceBatchDeletionService
from app.utils.decorators import create_required, delete_required, require_csrf
from app.utils.response_utils import jsonify_unified_error_message, jsonify_unified_success
from app.utils.structlog_config import log_error

instances_batch_bp = Blueprint(
    "instances_batch",
    __name__,
    url_prefix="/instances/batch",
)

batch_creation_service = InstanceBatchCreationService()
batch_deletion_service = InstanceBatchDeletionService()

EXPECTED_IMPORT_FIELDS = {header.lower() for header in INSTANCE_IMPORT_TEMPLATE_HEADERS}


def _normalize_header(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip("\ufeff").lower()


def _validate_csv_headers(fieldnames: list[str] | None) -> None:
    """校验 CSV 表头是否包含所有必填字段。"""

    normalized_headers = {
        _normalize_header(name)
        for name in (fieldnames or [])
        if name is not None
    }
    missing = INSTANCE_IMPORT_REQUIRED_FIELDS - normalized_headers
    if missing:
        missing_label = ", ".join(sorted(missing))
        raise ValidationError(f"CSV文件缺少必填列: {missing_label}")


def _normalize_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    """将 CSV 行转换为服务可识别的字段格式。"""

    normalized: dict[str, Any] = {}
    for raw_key, raw_value in (row or {}).items():
        field_name = _normalize_header(raw_key)
        if field_name not in EXPECTED_IMPORT_FIELDS:
            continue
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if not value:
                continue
        else:
            value = raw_value

        if field_name == "db_type" and isinstance(value, str):
            normalized[field_name] = value.lower()
        else:
            normalized[field_name] = value

    return normalized


@instances_batch_bp.route("/api/delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete_instances_batch() -> str | Response | tuple[Response, int]:
    """批量删除实例。

    Returns:
        tuple[Response, int] | Response | str: 删除结果。

    Raises:
        SystemError: 当删除过程中出现异常时抛出。
    """
    try:
        data = request.get_json() or {}
        instance_ids = data.get("instance_ids", [])

        result = batch_deletion_service.delete_instances(instance_ids, operator_id=current_user.id)
        message = f"成功删除 {result.get('deleted_count', 0)} 个实例"

        return jsonify_unified_success(data=result, message=message)

    except Exception as exc:  # noqa: BLE001
        log_error("批量删除实例失败", module="instances", exception=exc)
        raise SystemError("批量删除实例失败") from exc


@instances_batch_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_instances_batch() -> str | Response | tuple[Response, int]:
    """批量创建实例。

    Returns:
        tuple[Response, int] | Response | str: 创建结果。

    Raises:
        ValidationError: 当 CSV 不合法时抛出。
        SystemError: 当服务执行失败时抛出。
    """
    try:
        uploaded_file = request.files.get("file")
        if not uploaded_file or not uploaded_file.filename.endswith(".csv"):
            raise ValidationError("请上传CSV格式文件")

        return _process_csv_file(uploaded_file)

    except ValidationError as exc:
        db.session.rollback()
        return jsonify_unified_error_message(
            str(exc),
            status_code=HttpStatus.BAD_REQUEST,
            category=ErrorCategory.VALIDATION,
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        log_error("批量创建实例失败", module="instances", exception=exc)
        raise SystemError("批量创建实例失败") from exc


def _process_csv_file(file_obj: Any) -> Response:  # noqa: ANN401
    """解析 CSV 文件并触发批量创建。

    Args:
        file_obj: 上传的文件对象。

    Returns:
        Response: 批量创建的统一响应。

    Raises:
        ValidationError: 当 CSV 解析失败时抛出。
    """
    try:
        stream = io.StringIO(file_obj.stream.read().decode("utf-8-sig"), newline=None)
        csv_input = csv.DictReader(stream)
        _validate_csv_headers(csv_input.fieldnames)

        instances_data: list[dict[str, Any]] = []
        for row in csv_input:
            normalized_row = _normalize_csv_row(row)
            if normalized_row:
                instances_data.append(normalized_row)

        if not instances_data:
            raise ValidationError("CSV文件为空或未包含有效数据")

        return _create_instances(instances_data)

    except ValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"CSV文件处理失败: {exc}") from exc


def _create_instances(instances_data: list[dict[str, Any]]) -> Response:
    """调用批量创建服务并返回统一响应。

    Args:
        instances_data: CSV 解析出的实例数据列表。

    Returns:
        Response: 成功或失败的 JSON 响应。
    """
    operator_id = getattr(current_user, "id", None)
    result = batch_creation_service.create_instances(instances_data, operator_id=operator_id)
    message = result.pop("message", f"成功创建 {result.get('created_count', 0)} 个实例")
    return jsonify_unified_success(data=result, message=message)
