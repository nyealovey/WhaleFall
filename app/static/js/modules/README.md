# Modules 目录说明

该目录用于承载逐步抽离出的前端分层代码.目录命名与实现需遵循 `docs/Obsidian/standards/core/gate/naming.md`:

- `services/`:存放业务服务层,文件名使用 `snake_case`,导出 CapWords 类或工厂函数.每个服务只负责封装接口调用、参数序列化、错误转换,不直接操作 DOM.
- 未来的 `stores/`、`views/` 等子目录也需保持同样的命名策略,并在对应 README 中补充准则.

所有服务应:
1. 通过构造函数或工厂函数接收 `httpClient`(默认为 `window.httpU`),避免重复依赖全局变量.
2. 暴露清晰的方法(如 `list`, `detail`, `create`),内部统一处理查询参数和错误.
3. 在需要全局可用时,通过 `window.ServiceName = ServiceName;` 暂时挂载,便于现有脚本引用.

随着模块化构建工具的引入,这些服务可以直接迁移为 ES Modules,但命名和职责保持不变.
