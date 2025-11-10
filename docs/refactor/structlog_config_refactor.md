# `app/utils/structlog_config.py` 重构方案

> 目标：拆解 700+ 行的 `structlog_config.py`，理清配置/处理器/便捷函数/错误增强之间的职责，降低重复代码，提升扩展性与可测试性。以下方案结合 `docs/reports/large_files_analysis.md` 中的发现，并补充针对性举措。

## 1. 现状速览

| 模块 | 现有内容 |
| --- | --- |
| SQLAlchemyLogHandler | 日志落库、批量缓冲、后台线程、上下文拼接 |
| StructlogConfig | processors 配置、`configure()` 入口、request/user/global context 处理器 |
| Logger factory | `get_system_logger`/`get_sync_logger` 等 10+ 个函数，仅封装 `get_logger("name")` |
| 错误增强 | `ErrorContext`、`enhanced_error_handler`、`_derive_error_metadata` 等 |
| 全局变量 | `request_id_var`、`user_id_var`、`_global_context` 等 |

痛点：所有内容堆在一个文件，职责交织；日志处理器、配置、工具函数之间缺乏清晰边界；大量重复函数和遗留逻辑（例如 `_global_context` 未被使用）。

## 2. 拆分建议

```
utils/
├── logging/
│   ├── __init__.py
│   ├── structlog_setup.py         # 负责 configure()、processors 注册
│   ├── log_handlers.py            # SQLAlchemyLogHandler、异步落库逻辑
│   ├── log_context.py             # request/user/global context 插件
│   ├── logger_factory.py          # 工厂注册表 + get_logger/by name
│   └── error_handler.py           # ErrorContext / enhanced_error_handler
└── structlog_config.py            # 兼容入口（import 新模块）
```

拆分后，外部 `from app.utils.structlog_config import get_sync_logger` 仍可使用，通过 `__all__` 转发即可。

## 3. 重点改造项

### 3.1 SQLAlchemyLogHandler
- **问题**：落库逻辑、线程、上下文拼装全部内嵌；异常处理只打印 `Error flushing logs`，未包含具体内容；对 `has_request_context()` 的依赖增加了耦合。
- **方案**：
  - 移入 `log_handlers.py`，将“数据序列化”与“数据库写入”分离：由 handler 生成标准 dict，交给 `UnifiedLogRepository` 写库。
  - 提供 hook 注入，支持在测试环境关闭线程或替换 handler。
  - 补充参数化配置（batch_size/flush_interval 从 Config 读取）。

### 3.2 Structlog processors
- **问题**：processors 列表写死在 `configure()` 内；`_get_handler()`/`_get_console_renderer()` 每次调用都实例化，难以测试。
- **方案**：
  - 在 `structlog_setup.py` 定义 PROCESSOR_PIPELINE，支持根据环境（DEV/PROD）启用控制台 renderer。
  - 将 request/user/global context 处理器放入 `log_context.py`，可复用/单测。
  - 允许通过配置关闭数据库写入（例如 `LOG_TO_DB=false`）。

### 3.3 Logger factory
- **问题**：`get_system_logger`、`get_api_logger` 等函数大量重复，只是绑定不同名称。
- **方案**：
  - 建立注册表 `LOGGER_PRESETS = {"system": {...}, "sync": {...}}`，使用 `get_logger(name, **overrides)`。
  - 兼容旧函数（调用 `return get_logger("sync")` 即可），但将生成逻辑集中，方便统一加字段。

### 3.4 错误增强模块
- **问题**：`ErrorContext` 和错误分类函数接入点不明，容易与 logging 配置耦合；放在同文件导致编译依赖庞大。
- **方案**：
  - 移到 `error_handler.py`，并与 API 层约定接口。
  - 在 `app.utils.errors` 或统一错误处理中 import 使用。

### 3.5 全局上下文清理
- `_global_context` 仅在 `_add_global_context` 使用，可替换为配置常量；若确实需要全局绑定（如部署信息），可暴露 `set_global_log_context()` API。
- `request_id_var`/`user_id_var` 保留，但应统一在 `log_context.py` 管理，避免重复导入。

## 4. 迁移步骤

1. **阶段一**：创建 `app/utils/logging/` 目录，搬迁 SQLAlchemy handler + context 插件，`structlog_config.py` 中 import 新模块；功能不变。
2. **阶段二**：实现 Logger factory 注册表 + `get_logger` 公共入口；旧的 `get_*_logger` 调用新函数，逐步淘汰重复代码。
3. **阶段三**：将 `ErrorContext` 及增强错误处理迁到独立文件；在引用处更新 import。
4. **阶段四**：调整 `configure()`，允许通过 Config 切换 handler/renderer；写单元测试验证 processors 顺序。
5. **阶段五**：文档更新 `docs/reports/large_files_analysis.md`、新增 `structlog` 使用指南。

## 5. 风险与兼容性

| 风险 | 缓解 |
| --- | --- |
| 大范围移动文件导致 import break | 在 `app/utils/structlog_config.py` 保留兼容导出：`from .logging.structlog_setup import configure, get_logger, ...` |
| 日志落库行为变化 | 保留原 `SQLAlchemyLogHandler` 默认行为，新增配置开关；上线前在测试环境观察日志 |
| 多线程 handler 在测试环境启动 | 为 handler 添加 `enabled`/`start_thread` 参数，测试时可禁用 |

## 6. 预期收益

- 文件体积控制在 200 行以内，拆分后各模块易于理解和测试。
- 可根据环境灵活切换处理器（例如本地仅输出到控制台，线上写数据库）。
- 统一的 logger factory 便于注入公共字段（如 trace_id），避免散布 `get_sync_logger` 风格函数。
