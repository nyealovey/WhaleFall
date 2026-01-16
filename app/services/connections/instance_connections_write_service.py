"""Instances connections 写路径服务.

职责:
- 将 request payload 解析/规范化(parse_payload)与 schema 校验(validate_or_raise)收敛到 service 入口
- 产出 typed payload,供 API 层/业务编排层使用
"""

from __future__ import annotations

from app.schemas.instances_connections import (
    InstanceConnectionBatchTestPayload,
    InstanceConnectionParamsPayload,
    InstanceConnectionTestPayload,
)
from app.schemas.validation import validate_or_raise
from app.services.credentials import CredentialDetailReadService
from app.utils.request_payload import parse_payload


class InstanceConnectionsWriteService:
    """Instances connections 写路径入口."""

    def parse_connection_test_payload(self, payload: object | None) -> InstanceConnectionTestPayload:
        """解析并校验连接测试 payload."""
        sanitized = parse_payload(payload)
        return validate_or_raise(InstanceConnectionTestPayload, sanitized)

    def validate_connection_params_from_payload(self, payload: object | None) -> tuple[str, int]:
        """解析并校验连接参数,并验证可选 credential_id 是否存在."""
        sanitized = parse_payload(payload)
        parsed = validate_or_raise(InstanceConnectionParamsPayload, sanitized)
        if parsed.credential_id is not None:
            CredentialDetailReadService().get_credential_or_error(parsed.credential_id)
        return parsed.db_type, parsed.port

    def parse_batch_test_payload(self, payload: object | None) -> InstanceConnectionBatchTestPayload:
        """解析并校验批量连接测试 payload."""
        sanitized = parse_payload(payload, list_fields=["instance_ids"])
        return validate_or_raise(InstanceConnectionBatchTestPayload, sanitized)
