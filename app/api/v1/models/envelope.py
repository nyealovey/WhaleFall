"""OpenAPI: JSON Envelope Models.

说明:
- 仅用于文档表达; 实际响应仍以 `jsonify_unified_success` / 全局错误处理器为准.
"""

from __future__ import annotations

from flask_restx import Namespace, fields


def get_error_envelope_model(ns: Namespace):
    """注册/获取错误封套 Model."""
    model_name = "ErrorEnvelope"
    if model_name in ns.models:
        return ns.models[model_name]

    return ns.model(
        model_name,
        {
            "success": fields.Boolean(required=True, description="是否成功", example=False),
            "error": fields.Boolean(required=True, description="是否错误", example=True),
            "error_id": fields.String(required=True, description="错误ID", example="a1b2c3d4"),
            "category": fields.String(required=True, description="错误分类", example="system"),
            "severity": fields.String(required=True, description="严重程度", example="medium"),
            "message_code": fields.String(required=True, description="错误码", example="INVALID_REQUEST"),
            "message": fields.String(required=True, description="可展示的错误摘要", example="请求参数无效"),
            "timestamp": fields.String(required=True, description="时间戳(ISO8601)", example="2025-01-01T00:00:00"),
            "recoverable": fields.Boolean(required=True, description="是否可恢复", example=True),
            "suggestions": fields.List(
                fields.String, required=True, description="建议列表", example=["请检查输入参数"]
            ),
            "context": fields.Raw(required=True, description="结构化上下文信息", example={}),
            "extra": fields.Raw(required=False, description="非敏感诊断字段(可选)", example={}),
        },
    )


def make_success_envelope_model(ns: Namespace, name: str, data_model=None):
    """构建成功封套 Model, data_model 可选."""
    envelope_fields: dict[str, fields.Raw] = {
        "success": fields.Boolean(required=True, description="是否成功", example=True),
        "error": fields.Boolean(required=True, description="是否错误", example=False),
        "message": fields.String(required=True, description="可展示的成功摘要", example="操作成功"),
        "timestamp": fields.String(required=True, description="时间戳(ISO8601)", example="2025-01-01T00:00:00"),
        "meta": fields.Raw(required=False, description="元数据(可选)", example={}),
    }

    if data_model is None:
        envelope_fields["data"] = fields.Raw(required=False, description="响应数据(可选)", example={})
    else:
        envelope_fields["data"] = fields.Nested(data_model, required=False, description="响应数据(可选)")

    return ns.model(name, envelope_fields)
