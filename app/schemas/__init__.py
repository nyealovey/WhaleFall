"""Pydantic schemas.

集中维护写路径的 payload schema, 用于:
- 类型转换与默认值
- 业务字段校验(输出中文错误文案)
- 兼容字段 alias 与 canonicalization
"""

