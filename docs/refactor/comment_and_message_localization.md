# 注释与提示中文化重构方案

## 1. 背景

仓库中仍大量存在英文 docstring、行内注释以及用户可见的提示/错误信息。常见问题包括：

- 顶部 docstring、`Args:/Returns:` 段落为纯英文，阅读体验不一致。
- 不同模块的术语翻译随意，例如 handler/processor/scope 等各有不同翻译。
- `ValidationError`、Flash 消息、日志提示等仍保留英文，用户或运维需要二次理解。

为统一语言风格，同时保持 Google 风格 docstring 结构，需要一个系统性的中文化方案。

## 2. 改造目标

| 目标 | 说明 |
| --- | --- |
| Docstring 中文化 | 所有 docstring 采用中文描述；保留 Google 风格（`Args/Returns/Raises`），但说明文字使用中文。 |
| 提示文本中文化 | Flash、API message、日志提示、异常 message 等全部改为中文；内部枚举值可保留英文。 |
| 术语一致 | 依照术语表统一翻译（如 handler→处理器、scheduler→调度器）。 |
| 可追踪 | 通过 Todo 清单与术语表记录进度，避免遗漏。 |

## 3. 范围

1. **基础设施**：`app/utils/logging/`、`app/scheduler.py`、`app/utils/decorators.py`、`app/utils/rate_limiter.py` 等。
2. **服务/任务层**：`app/services/**`、`app/tasks/**`、`app/routes/**`。
3. **常量与错误信息**：`app/constants/**`、`ErrorMessages`、`ValidationError`、`flash`、日志提示。
4. **文档/报告**：`docs/reports/*`、`docs/refactor/*`（包含本方案）。

## 4. 执行步骤

1. **维护术语表**：`docs/refactor/terminology_localization.md` 记录英文→中文对照，PR 时若新增术语需同步更新。
2. **扫描工具**：
   - `rg -n "Args:" app`、`rg -n "Returns:" app` 定位 docstring。
   - `rg -n '"[^"]*[A-Za-z][^"]*"' app`+关键词(`error|warning|message`) 查找英文提示。
3. **模块化改造**：
   - 第一阶段：基础模块（logging/scheduler/decorator/rate_limiter）；
   - 第二阶段：服务与任务（aggregation、account_sync、capacity、database_sync 等）；
   - 第三阶段：routes/API 和文档。
4. **提交策略**：
   - 每个 PR 专注一组目录，commit message 标注 “docstring+文本中文化，无逻辑变更”；
   - 在 PR 描述中附“已对照术语表”说明。

## 5. 处理原则

- **Docstring**：中文描述 + Google 风格段落，例如：

  ```python
  def foo(bar: int) -> str:
      """示例函数。

      Args:
          bar: 输入整数。

      Returns:
          str: 处理后的字符串。
      """
  ```

- **日志/异常**：message 使用中文；如运维依赖英文关键字，可在同一字段追加括号说明或保留英文枚举字段（例如 `failure_reason="not_authenticated"`）。
- **Flash/API 提示**：全部改用中文句式，必要时保留英文术语在括号内。
- **文档**：章节标题、表格列、说明均使用中文；英文缩写可置于括号说明。

## 6. Todo 清单（示例）

1. `app/services/account_sync/*`：docstring、日志、`ValidationError` 提示中文化（进行中，核心协调器已确认无残留英文，持续巡检新增模块）。
2. `app/services/connection_adapters/*`：连接失败/版本查询等提示翻译；docstring 中文描述（2025-11-11 完成首次梳理）。
3. `app/services/database_sync/*`：inventory manager、persistence 等模块中文化（2025-11-11 已补齐过滤器/协同模块 docstring 与提示）。
4. `app/tasks/capacity_*/*.py`：任务函数 docstring 与日志提示统一中文。
5. `app/constants/**`：`FlashCategory`、`HttpHeaders` 等工厂函数 docstring 添加中文说明。
6. `app/routes/**`：视图函数 docstring、Flash 提示翻译；统一日志 message（2025-11-11 全量巡检完成）。
7. `app/utils/data_validator.py` 等工具模块：docstring 中文、异常 message 中文。
8. `docs/reports/*`：确保统计、说明章节使用中文术语。

## 7. 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 术语翻译不一致 | 术语表统一，由 reviewer 校对；必要时在 README 列出关键对照。 |
| 日志告警依赖英文关键字 | 在 message 附 “（scheduler not running）” 等英文别名，或保留英文字段。 |
| 大量改动影响 blame | 分模块提交，强调“无逻辑改动”。 |
| 新增英文再次混入 | 后续可添加 lint（如脚本检测 `Args:` 中是否包含中文），防止回归。 |

## 8. 验收标准

- `rg -n "Args:" app` 输出的每个 docstring 说明均为中文，且仍保留结构。
- `rg -n '"[^"]*[A-Za-z][^"]*"' app` 仅剩术语/内部枚举，不出现用户可见的英文提示。
- 文档与 README 中说明均为中文，术语与代码一致。

---

按照本方案执行，可在不影响逻辑的前提下完成注释与提示信息的全面中文化，降低沟通成本，提升团队协作效率。***

## 9. 最新进展

- 2025-11-11：完成 `app/routes/**` 中全部 docstring、验证错误及日志提示的中文化，`logs`、`files` 等模块的英文异常信息已翻译。
- 2025-11-11：完成 `app/services` 下 account_classification、aggregation、cache_service、connection_adapters、database_sync/database_filters 等模块的 docstring 与提示中文化，并统一缓存/调度相关文案。
- 2025-11-11：补充 `app/templates` 公共注释/提示、`app/config.py` 环境变量错误提示、`app/utils/structlog_config.py` 以及基础工具模块的中文化，并复核 `app/scheduler.py` 的日志与提示文字。
