# 统一日志示例

本目录包含使用项目统一日志工具的示例代码,方便在新增功能时参考.运行示例前,请确保已在项目根目录激活相应的 Python 环境(可直接使用 `make install` 安装依赖).

## 文件说明

| 文件 | 说明 |
| ---- | ---- |
| `unified_logging_example.py` | 展示如何绑定全局/请求上下文、记录结构化日志,以及如何与业务异常结合. |

## 快速运行

```bash
python examples/logging/unified_logging_example.py
```

执行后可以在控制台或日志存储介质中看到统一格式的结构化日志输出.

## 编写业务代码时的建议

1. **使用快捷方法**:优先使用 `log_info` / `log_warning` / `log_error` 等方法,避免直接访问底层 logger.
2. **绑定上下文**:全局信息(如服务名、环境)使用 `bind_context`,请求级信息(如 `request_id`、`user_id`)使用 `bind_request_context`.
3. **异常处理**:捕获业务异常时,通过 `log_warning` 或 `log_error` 记录 `exception`,并附带关键上下文字段,以便排查.
4. **及时清理**:请求结束后调用 `clear_request_context`,长期任务完成后调用 `clear_context`,防止上下文数据泄漏.
