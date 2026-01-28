"""Schema 基础设施."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class PayloadSchema(BaseModel):
    """写路径 payload 的基础 schema.

    约定:
    - 默认忽略未知字段, 以兼容前端/客户端的扩展字段.
    - schema 负责业务校验与错误文案(中文), request payload adapter 负责基础规范化.
    """

    model_config = ConfigDict(extra="ignore")


class QuerySchema(BaseModel):
    """读路径 query 参数的基础 schema.

    约定:
    - 默认拒绝未知字段，避免“拼错参数却被静默忽略”的隐患
    - 禁止直接传入 offset（统一通过 page/limit 计算），避免绕过分页策略
    """

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _reject_offset(cls, data: Any) -> Any:
        if not isinstance(data, Mapping) or "offset" not in data:
            return data

        # flask-restx reqparse 会把未传入的参数也放进 dict（值为 None）。
        # 这里把“空 offset”当作不存在；只有显式传入 offset 才报错。
        offset_value = data.get("offset")
        if offset_value is None:
            mutable = dict(data)
            mutable.pop("offset", None)
            return mutable
        if isinstance(offset_value, str) and not offset_value.strip():
            mutable = dict(data)
            mutable.pop("offset", None)
            return mutable

        raise ValueError("不支持 offset")
