"""表单处理器集合.

说明:
- 这些 handler 作为 ResourceFormView 的依赖,负责:
  - 解析/规范化 payload
  - 调用 write services 执行写操作
  - 提供模板渲染所需的 build_context
- handler 不做 commit,事务边界统一由 safe_route_call 控制
"""

