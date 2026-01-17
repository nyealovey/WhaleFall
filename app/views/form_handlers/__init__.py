"""表单处理器(View layer).

说明:
- 这些 handler 实现 `ResourceFormHandler` 协议,供 `ResourceFormView` 调用.
- handler 自身不直接访问数据库, 统一调用 Service 完成 load/upsert 与选项读取.
"""
