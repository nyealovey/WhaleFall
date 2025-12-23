"""Instances 域:批量创建与删除路由.

负责处理 CSV 批量导入、删除等实例管理接口。
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, Any

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
from app.utils.route_safety import safe_route_call

if TYPE_CHECKING:
    from werkzeug.datastructures import FileStorage

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
    """校验 CSV 表头是否包含所有必填字段."""
    normalized_headers = {_normalize_header(name) for name in (fieldnames or []) if name is not None}
    missing = INSTANCE_IMPORT_REQUIRED_FIELDS - normalized_headers
    if missing:
        missing_label = ", ".join(sorted(missing))
        msg = f"CSV文件缺少必填列: {missing_label}"
        raise ValidationError(msg)


def _normalize_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    """将 CSV 行转换为服务可识别的字段格式."""
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
    """批量删除实例.

    Returns:
        tuple[Response, int] | Response | str: 删除结果.

    """
    payload = request.get_json() or {}

    def _execute() -> tuple[Response, int]:
        instance_ids = payload.get("instance_ids", [])
        result = batch_deletion_service.delete_instances(
            instance_ids,
            operator_id=current_user.id,
            deletion_mode="soft",
        )
        message = f"成功移入回收站 {result.get('deleted_count', 0)} 个实例"
        return jsonify_unified_success(data=result, message=message)

    return safe_route_call(
        _execute,
        module="instances_batch",
        action="delete_instances_batch",
        public_error="批量移入回收站失败",
        expected_exceptions=(ValidationError,),
        context={"count": len(payload.get("instance_ids", []))},
    )


@instances_batch_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_instances_batch() -> str | Response | tuple[Response, int]:
    """批量创建实例.

    Returns:
        tuple[Response, int] | Response | str: 创建结果.

    """
    uploaded_file = request.files.get("file")

    def _execute() -> tuple[Response, int]:
        if not uploaded_file or not uploaded_file.filename or not uploaded_file.filename.endswith(".csv"):
            msg = "请上传CSV格式文件"
            raise ValidationError(msg)
        return _process_csv_file(uploaded_file)

    try:
        return safe_route_call(
            _execute,
            module="instances_batch",
            action="create_instances_batch",
            public_error="批量创建实例失败",
            expected_exceptions=(ValidationError,),
        )
    except ValidationError as exc:
        db.session.rollback()
        return jsonify_unified_error_message(
            str(exc),
            status_code=HttpStatus.BAD_REQUEST,
            category=ErrorCategory.VALIDATION,
        )
    except SystemError:
        db.session.rollback()
        raise


def _process_csv_file(file_obj: FileStorage) -> tuple[Response, int]:
    """解析 CSV 文件并触发批量创建.

    Args:
        file_obj: 上传的文件对象.

    Returns:
        Response: 批量创建的统一响应.

    Raises:
        ValidationError: 当 CSV 解析失败时抛出.

    """
    try:
        stream = io.StringIO(file_obj.stream.read().decode("utf-8-sig"), newline=None)
        csv_input = csv.DictReader(stream)
        csv_fieldnames = list(csv_input.fieldnames) if csv_input.fieldnames is not None else None
        _validate_csv_headers(csv_fieldnames)
    except Exception as exc:
        msg = f"CSV文件处理失败: {exc}"
        raise ValidationError(msg) from exc

    instances_data = [
        normalized_row
        for row in csv_input
        if (normalized_row := _normalize_csv_row(row))
    ]

    if not instances_data:
        msg = "CSV文件为空或未包含有效数据"
        raise ValidationError(msg)

    return _create_instances(instances_data)


def _create_instances(instances_data: list[dict[str, Any]]) -> tuple[Response, int]:
    """调用批量创建服务并返回统一响应.

    Args:
        instances_data: CSV 解析出的实例数据列表.

    Returns:
        Response: 成功或失败的 JSON 响应.

    """
    operator_id = getattr(current_user, "id", None)
    result = batch_creation_service.create_instances(instances_data, operator_id=operator_id)
    message = result.pop("message", f"成功创建 {result.get('created_count', 0)} 个实例")
    return jsonify_unified_success(data=result, message=message)
