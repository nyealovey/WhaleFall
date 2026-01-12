from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Self

class _BaseMetric:
    def labels(self, *labelvalues: str, **labelkwargs: str) -> Self: ...

class Counter(_BaseMetric):
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = ...,
        **kwargs: Any,
    ) -> None: ...
    def inc(self, amount: float = ...) -> None: ...

class Histogram(_BaseMetric):
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] = ...,
        **kwargs: Any,
    ) -> None: ...
    def observe(self, amount: float) -> None: ...
