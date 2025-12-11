"""通用结构化数据类型别名.

统一 JSON/Mapping 风格的类型,方便在视图、服务等模块中共享定义,避免重复声明.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from decimal import Decimal
from typing import Protocol, TypeAlias, TypedDict

ScalarValue: TypeAlias = str | int | float | bool | None
PayloadValue: TypeAlias = ScalarValue | Sequence[ScalarValue] | Mapping[str, ScalarValue]
PayloadMapping: TypeAlias = Mapping[str, PayloadValue]
MutablePayloadDict: TypeAlias = dict[str, PayloadValue]
FormErrorMapping: TypeAlias = Mapping[str, Sequence[str] | str]
NumericLike: TypeAlias = int | float | Decimal | str | None
ColorToken: TypeAlias = str
ColorHex: TypeAlias = str
ColorName: TypeAlias = str
CssClassName: TypeAlias = str


class ColorOptionDict(TypedDict):
    """颜色下拉选项结构."""

    value: ColorToken
    name: ColorName
    description: str
    css_class: CssClassName


class CategoryOptionDict(TypedDict):
    """通用值-标签选项结构."""

    value: str
    label: str


ContextValue: TypeAlias = (
    ScalarValue | Sequence["ContextValue"] | Mapping[str, "ContextValue"] | ColorOptionDict | CategoryOptionDict
)
ContextMapping: TypeAlias = Mapping[str, ContextValue]
ContextDict: TypeAlias = dict[str, ContextValue]
JsonValue: TypeAlias = ScalarValue | Sequence["JsonValue"] | Mapping[str, "JsonValue"]
JsonDict: TypeAlias = dict[str, JsonValue]
StructlogEventDict: TypeAlias = MutableMapping[str, JsonValue]
LoggerExtra: TypeAlias = Mapping[str, JsonValue]


class LoggerProtocol(Protocol):
    """结构化日志协议,统一 logger 的最小接口."""

    def bind(self, **kwargs: JsonValue) -> LoggerProtocol: ...

    def new(self, **kwargs: JsonValue) -> LoggerProtocol: ...

    def debug(self, event: str, *args: object, **kwargs: JsonValue) -> object: ...

    def info(self, event: str, *args: object, **kwargs: JsonValue) -> object: ...

    def warning(self, event: str, *args: object, **kwargs: JsonValue) -> object: ...

    def error(self, event: str, *args: object, **kwargs: JsonValue) -> object: ...

    def exception(self, event: str, *args: object, **kwargs: JsonValue) -> object: ...


__all__ = [
    "ScalarValue",
    "PayloadValue",
    "PayloadMapping",
    "MutablePayloadDict",
    "ContextValue",
    "ContextMapping",
    "ContextDict",
    "FormErrorMapping",
    "NumericLike",
    "ColorToken",
    "ColorHex",
    "ColorName",
    "CssClassName",
    "ColorOptionDict",
    "CategoryOptionDict",
    "JsonValue",
    "JsonDict",
    "StructlogEventDict",
    "LoggerExtra",
    "LoggerProtocol",
]
