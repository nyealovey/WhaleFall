# Connection Adapters 重构说明

## 背景

旧版 `app/services/connection_adapters/connection_factory.py` 同时承载四种数据库（MySQL/PostgreSQL/SQL Server/Oracle）连接的具体实现，导致：

- 单文件超 500 行，阅读与调试困难。
- 任意一个数据库驱动的修改都会触发整个文件的合并冲突。
- 无法按数据库粒度编写/复用工具函数，也不利于单元测试。

## 目标

1. 将各数据库的连接逻辑拆分到独立模块，彼此隔离。
2. 提供一个共享的 `DatabaseConnection` 抽象类，统一接口（connect/disconnect/test/execute/get_version）。
3. 让 `ConnectionFactory` 仅负责「类型 -> 适配器」的映射，避免与底层驱动强耦合。

## 新目录结构

```
app/services/connection_adapters/
├── adapters/
│   ├── __init__.py
│   ├── base.py                  # DatabaseConnection 抽象 & 公共工具
│   ├── mysql_adapter.py         # MySQL 连接实现
│   ├── postgresql_adapter.py    # PostgreSQL 连接实现
│   ├── sqlserver_adapter.py     # SQL Server 连接实现
│   └── oracle_adapter.py        # Oracle 连接实现
├── connection_factory.py        # 工厂，仅维护类型映射
└── connection_test_service.py   # 原测试服务，逻辑保持不变
```

## 主要改动

- **抽象基类**： 在 `adapters/base.py` 定义 `DatabaseConnection`，所有适配器实现统一接口；同时提供 `get_default_schema()` 供多种数据库复用。
- **适配器拆分**： 将原文件中各 `*Connection` 类分别移动至 `adapters/` 子模块，对应文件仅负责自身驱动引入、连接、日志与版本解析。
- **工厂精简**： `ConnectionFactory` 只保留类型映射与辅助方法，引用 `adapters` 中的类，避免重复逻辑。
- **兼容性**： `connection_test_service` 继续通过工厂创建连接，不需额外修改；其错误处理及版本解析保持原状。

## 升级建议

1. 若后续新增数据库类型，只需在 `adapters/` 下新建文件并在 `adapters/__init__.py` + `ConnectionFactory.CONNECTION_CLASSES` 注册即可。
2. 建议补充每个适配器的单元测试（模拟驱动异常场景），防止未来驱动升级导致回归。
3. 若连接需要共享更多工具（如重试、超时装饰器），可在 `base.py` 内继续扩展，避免散落在各适配器中。

## 已知影响

- 依赖路径从 `app.services.connection_adapters.connection_factory` 导出的连接类不再可用；外部应始终通过 `ConnectionFactory` 访问，因此无需额外变更。
- 代码生成/自动导入脚本请更新以适配新目录结构（若有）。

此文档描述截至 `3ec4c469` 提交的结构。若后续继续扩展适配器，请在本文件追加变更记录。
