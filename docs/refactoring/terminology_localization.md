# 注释中文化术语表

| 英文术语 | 中文建议 | 说明 |
| --- | --- | --- |
| structlog | structlog（保留缩写） | 专有名词，保留原拼写。 |
| handler | 处理器 | 如日志处理器、事件处理器。 |
| processor | 处理器 | 与 handler 类似，结合上下文翻译。 |
| queue worker | 队列工作线程 | 描述后台线程。 |
| payload | 载荷 / 数据负载 | 根据语境选一个。 |
| request context | 请求上下文 | Flask 术语。 |
| app context | 应用上下文 | Flask 术语。 |
| fallback | 回退方案 | 表示降级策略。 |
| scope | 范围 | 常用于聚合范围。 |
| runner | 执行器 | aggregation runner 等。 |
| period | 周期 | daily/weekly 等。 |
| status | 状态 | 成功、失败、跳过等。 |
| logger factory | 日志工厂 | 提供日志获取函数。 |
| debounce | 防抖 | 若涉及前端。 |
| throttling | 节流 | 若涉及前端。 |
| cache | 缓存 | 保留常用翻译。 |
| sync session | 同步会话 | 任务同步上下文。 |
| credential | 凭据 | 账号密码实体。 |
| partition | 分区 | 数据库分区。 |
| scheduler | 调度器 | APScheduler。 |
| blueprint | 蓝图 | Flask Blueprint。 |
| middleware | 中间件 | 如 Flask 扩展。 |
| validator | 校验器 | DataValidator 等。 |
| sanitizer | 清洗器/清理器 | sanitize input。 |
| hook | 钩子 | 事件钩子。 |
| repository | 仓储 | 如果引入 repository 层。 |
| metrics | 指标 | 日志或监控指标。 |
| fallback handler | 回退处理器 | 组合词。 |
| task | 任务 | Celery/定时任务。 |
| adapter | 适配器 | connection adapter。 |
| aggregator | 聚合器 | 统计聚合组件。 |
| bootstrap | 启动 / Bootstrap（框架） | 视上下文。 |
| render | 渲染 | 前端/模板渲染。 |

> 该表将随中文化进度动态扩展；如遇新的英文术语，可在 PR 中补充并说明用途。***
