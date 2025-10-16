"""
响应工具函数单元测试
"""

import re
from typing import Any

import pytest
from flask import Flask

from app.constants.system_constants import ErrorCategory, ErrorSeverity, SuccessMessages
from app.errors import ValidationError
from app.utils.response_utils import (
    jsonify_unified_error_message,
    jsonify_unified_success,
    unified_error_response,
    unified_success_response,
)


@pytest.fixture
def flask_app() -> Any:
    """构造临时 Flask 应用，供 jsonify 系列函数使用"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


@pytest.mark.unit
def test_unified_success_response_default():
    """默认成功响应结构包含必要字段"""
    payload, status = unified_success_response()

    assert status == 200
    assert payload["error"] is False
    assert payload["message"] == SuccessMessages.OPERATION_SUCCESS
    assert re.match(r"\d{4}-\d{2}-\d{2}T", payload["timestamp"])
    assert "data" not in payload


@pytest.mark.unit
def test_unified_success_response_with_data():
    """成功响应包含 data 与 meta"""
    data = {"id": 1, "name": "test"}
    meta = {"page": 1}

    payload, status = unified_success_response(data=data, meta=meta, message="操作完成", status=201)

    assert status == 201
    assert payload["error"] is False
    assert payload["message"] == "操作完成"
    assert payload["data"] == data
    assert payload["meta"] == meta


@pytest.mark.unit
def test_jsonify_unified_success(flask_app: Any):
    """jsonify 版本的成功响应可直接返回 HTTP Response"""
    with flask_app.app_context():
        response, status = jsonify_unified_success(data={"key": "value"})

        assert status == 200
        json_data = response.get_json()
        assert json_data["error"] is False
        assert json_data["data"] == {"key": "value"}


@pytest.mark.unit
def test_unified_error_response_from_app_error():
    """AppError 子类可正确映射到 HTTP 状态码与分类"""
    error = ValidationError("参数错误")

    payload, status = unified_error_response(error)

    assert status == 400
    assert payload["error"] is True
    assert payload["category"] == ErrorCategory.VALIDATION.value
    assert payload["severity"] == ErrorSeverity.LOW.value
    assert payload["recoverable"] is True
    assert payload["message"] == "参数错误"


@pytest.mark.unit
def test_jsonify_unified_error_message(flask_app: Any):
    """直接通过消息生成错误响应"""
    with flask_app.app_context():
        response, status = jsonify_unified_error_message(
            "服务未就绪",
            status_code=503,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
        )

        assert status == 503
        data = response.get_json()
        assert data["error"] is True
        assert data["message"] == "服务未就绪"
        assert data["category"] == ErrorCategory.SYSTEM.value
        assert data["severity"] == ErrorSeverity.HIGH.value
