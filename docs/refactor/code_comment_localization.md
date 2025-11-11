# 代码注释中文化重构方案

## 1. 背景

目前仓库中存在大量英文注释、文档片段与提示字符串（例如 `app/utils/structlog_config.py` 顶部的 “Structured logging configuration and helpers...”）。混用中英文容易在评审、维护以及本地化协作时造成理解成本，也难以保证文档风格一致。为提升可读性与运维效率，需要一份 “注释中文化” 的系统性改造方案。

## 2. 现状痛点

1. **入口提示不友好**：关键模块顶部 docstring（如 structlog、aggregation、scheduler 等）仍是纯英文，阅读者需要额外翻译才能理解。
2. **注释语气不统一**：单个函数内既有英文 inline comment，又有中文说明，容易让代码审阅停顿。
3. **文档术语混乱**：部分重构/报告文件的章节标题、表格列仍用英文或前后混搭，降低整体专业度。
4. **多语言字符串未标准化**：例如 `log_info`、配置提示等常量还保留英文，影响日志检索与告警定位。

## 3. 重构目标

| 目标 | 说明 |
| --- | --- |
| 中文优先 | 代码注释、docstring、文档章节以中文为主，必要时附英文对照。 |
| 术语一致 | 保持与设计文档相同的术语（如 “日志处理器”“实例聚合”），减少自由翻译。 |
| 可回溯 | 通过脚本或清单标记已完成模块，避免遗漏。 |
| 不影响运行 | 仅修改注释/字符串，不改逻辑；如需改日志文本，需同步告知运维。 |

## 4. 方案设计

### 4.1 范围划分

1. **核心模块**：`app/utils/structlog_config.py`、`app/services/aggregation/aggregation_service.py`、`app/tasks/*.py`、`app/routes/*.py` 等。
2. **文档/报告**：`docs/reports/*`、`docs/refactor/*`、`docs/architecture/*`。
3. **日志/提示文本**：`log_info/log_error` 和 `ValidationError` 的 message；需要评估是否涉及 UI 呈现。

### 4.2 执行步骤

1. **建立术语表**：先梳理 structlog、aggregation、scheduler 等模块中常用英文词汇（例：`handler`、`runner`、`period`），确认统一翻译。
2. **模块化推进**：
   - 第一步：处理基础设施（`utils/logging/`、`scheduler` 等），确保 docstring、注释、日志文本统一。
   - 第二步：处理业务服务（`services/aggregation`、`tasks/capacity_*` 等）。
   - 第三步：补齐文档和报告。
3. **工具辅助**：
   - 使用 `rg`/`python` 脚本扫描双引号或注释中的ASCII词，生成清单。
   - 每个模块改完后运行 `git diff --stat`，确认只涉及注释/字符串。
4. **评审与验收**：
   - PR 描述需附 “已校对中文术语清单”。
   - 关键模块（structlog、aggregation）由对应 owner 复核，避免误翻技术名词。

### 4.3 处理原则

- **函数/类 docstring**：改为完整中文句子，如 “`"""Structured logging configuration..."""` → `"""结构化日志配置及相关辅助函数。"""`”。
- **行内注释**：保留中英文含义一致的简短说明，避免添加冗长段落；若需要保留英文术语，可写成 “`# handler（日志处理器）负责...`”。
- **日志/异常 message**：优先中文；若对接外部系统或需要关键词匹配，可保留英文描述作为附加字段（例如 `message="调度器未启动 (scheduler not running)"`）。
- **文档标题**：全部采用中文，英文缩略词可置于括号或附注。

## 5. 依赖与风险

| 风险 | 缓解措施 |
| --- | --- |
| 术语翻译不一致 | 先冻结术语表，明确 reviewer；必要时在 README 中列出对应关系。 |
| 日志检索受影响 | 针对告警系统依赖的关键字，改动前征求运维确认，或保留英文别名。 |
| 大量修改影响 blame | 分模块、分 PR 提交，且在 commit message 中说明 “注释中文化无逻辑变更”。 |

## 6. 里程碑

1. **Week 1**：完成术语表 + `utils/logging/`、`scheduler` 相关中文化。
2. **Week 2**：服务层（aggregation、capacity）和任务脚本注释中文化。
3. **Week 3**：文档/报告更新；同步 README/贡献指南说明 “注释统一使用中文”。
4. **结项**：新增 CI 检查（例如简单的 lint 规则），阻止再出现 “Structured logging config ...” 类英文 docstring。

---

通过以上步骤，可在不影响运行的前提下完成全面中文化，让团队成员在审阅与维护时有统一语言环境，也方便后续编写中文技术文档与 PR 描述。***
