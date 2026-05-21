"""账户归属范围类型."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import ValidationError

SUPPORTED_ACCOUNT_SCOPE_OWNER_TYPES = {"instance", "sqlserver_ag"}


@dataclass(frozen=True, slots=True)
class AccountScope:
    """账户统计/分类使用的归属范围."""

    owner_type: str
    owner_id: int

    @property
    def value(self) -> str:
        """前端筛选值."""
        return f"{self.owner_type}:{self.owner_id}"


def parse_account_scope(raw_value: object, *, legacy_instance_id: int | None = None) -> AccountScope | None:
    """解析前端传入的账户范围.

    支持新格式 `instance:<id>` / `sqlserver_ag:<id>`；保留 `instance_id`
    兼容入口并映射为 `instance:<id>`。
    """
    if isinstance(raw_value, str) and raw_value.strip():
        owner_type, sep, owner_id_raw = raw_value.strip().partition(":")
        if sep != ":":
            raise ValidationError("account_scope 必须为 owner_type:owner_id 格式")
        normalized_owner_type = owner_type.strip().lower()
        if normalized_owner_type not in SUPPORTED_ACCOUNT_SCOPE_OWNER_TYPES:
            raise ValidationError("account_scope owner_type 不支持")
        try:
            owner_id = int(owner_id_raw)
        except ValueError as exc:
            raise ValidationError("account_scope owner_id 必须为整数") from exc
        if owner_id <= 0:
            raise ValidationError("account_scope owner_id 必须大于 0")
        return AccountScope(owner_type=normalized_owner_type, owner_id=owner_id)

    if legacy_instance_id is not None:
        return AccountScope(owner_type="instance", owner_id=int(legacy_instance_id))
    return None
