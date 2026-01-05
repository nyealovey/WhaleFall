"""Schema 基础设施."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PayloadSchema(BaseModel):
    """写路径 payload 的基础 schema.

    约定:
    - 默认忽略未知字段, 以兼容前端/客户端的扩展字段.
    - schema 负责业务校验与错误文案(中文), request payload adapter 负责基础规范化.
    """

    model_config = ConfigDict(extra="ignore")

