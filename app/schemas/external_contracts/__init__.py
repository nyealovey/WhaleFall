"""External contract adapters/normalizers.

说明：
- 该目录用于收敛外部依赖/采集驱动返回的“脏 dict”到 schema 单入口 canonicalization。
- Service/Adapter 层应尽量只做 IO 与编排，避免散落 `or` 兜底链与字段/形状兼容逻辑。
"""
