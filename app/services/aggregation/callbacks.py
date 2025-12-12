"""聚合 Runner 的回调配置."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.models.instance import Instance


@dataclass(slots=True)
class RunnerCallbacks:
    """封装实例级聚合所需的回调集合."""

    on_instance_start: Callable[[Instance], None] | None = None
    on_instance_complete: Callable[[Instance, dict[str, Any]], None] | None = None
    on_instance_error: Callable[[Instance, dict[str, Any]], None] | None = None
