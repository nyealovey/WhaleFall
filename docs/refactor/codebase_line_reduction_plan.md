# 代码体量削减重构方案

## 1. 背景与目标
- 2025-12-09 以 `python3` 脚本统计：仓库总计约 **131,577 行**；`app/` 目录（显式排除 `app/static/vendor`）约 **89,077 行**，`app/static/vendor` 独立占 **1,404 行**；前端 JS (`app/static/js`) 33,656 行、路由 10,790 行、服务层 17,901 行、工具模块 5,040 行。
- 文件粒度呈现高度重复：多处单文件 700~1,200 行（例如 `app/static/js/modules/views/instances/list.js` 1,270 行、`app/services/aggregation/aggregation_service.py` 919 行）。
- 目标：在 **功能完全等价** 的前提下于 2026-02-05 前削减 ≥30% 代码行数（约 27,000 行），并保持 `make quality`、`make test` 全量通过。

## 2. 范围与原则
1. **范围**：面向前端 Grid 页面、Vuex 风格 store、账户同步适配器、Form 服务、路由层、通用工具/任务模块；数据库模型、核心聚合逻辑、调度器协议为受保护资产，仅允许“瘦身式”调整。
2. **功能守恒**：所有 API、页面交互保持既有输入/输出；若需新增配置项，也必须默认与现行为等价。
3. **命名守卫**：新建/重命名文件须运行 `./scripts/refactor_naming.sh --dry-run`，输出必须为“无需要替换的内容”。
4. **规范复核**：沿用 AGENTS.md 要求，docstring、注释全部中文，筛选卡片使用 `col-md-2 col-12` 栅格，禁止硬编码颜色值。
5. **验证闭环**：阶段性交付需附 `make format && make quality && make test` 结果及新增/回归测试列表。

## 3. 重构策略
### 3.1 配置化前端骨架（预期 -12k 行）
- 构建 `gridPageFactory` 与 `createStore`，以 JSON/Schema 描述列定义、筛选器、批量动作、请求 URL、缓存策略。
- 迁移实例、账户、标签、历史、凭据等 ≥15 个 Grid 页面，预计把单页 JS 从 700~1,200 行压缩到 250 行以内。
- 组件级模块（图表、标签控制器、历史详情）通过 `manifest`/hook 注入自定义逻辑，防止抽象过度。

### 3.2 账户同步适配器表驱动（预期 -6k 行）
- 在 `app/services/accounts_sync/adapters` 引入 `AdapterMetadata`，包含字段映射、SQL 模板、差异钩子。
- `base_adapter.py` 负责模板渲染与 SQL 拼接；`factory.py` 根据数据库类型加载 metadata。
- 4 套适配器压缩为 “1 个渲染器 + 多个 metadata”，配套 `pytest -k accounts_sync` 验证。

### 3.3 Form Service 抽象（预期 -4k 行）
- 新增 `BaseFormService`，注入 `Model`, `Schema`, `policy_hooks`；通用 CRUD、审计、权限校验下沉至基类。
- 用 `pydantic` 或 `marshmallow` 取代 `utils/data_validator.py`、`utils/decorators.py` 中重复校验逻辑，保留差异化 hook。

### 3.4 路由 ViewSet 化（预期 -5k 行）
- 创建 `app/api/base_viewset.py`，封装分页、筛选解析、权限验证、统一响应。
- `app/routes/*` 仅实现业务动词函数（如 `list_instances`、`get_account`），去除重复序列化与错误处理代码。

### 3.5 工具与任务瘦身（预期 -3k 行）
- 逐步弃用自研速率限制、SQL 构造器、APScheduler 包装，改用成熟库：`pydantic`, SQLAlchemy Query Builder, APScheduler JobStore。
- 保留结构化日志、批处理等项目特有能力，实现“薄包装”。

### 3.6 缓冲空间（预期 -3k 行）
- 当主策略完成度 <30% 时，优先继续迁移组件 JS、统计 store、次要任务脚本，确保总削减量 ≥33k 行。

## 4. 实施阶段
| 阶段 | 时间范围 | 关键里程碑 |
| --- | --- | --- |
| 基线阶段 | 2025-12-10 ~ 2025-12-24 | 完成 `gridPageFactory` 原型、迁移实例列表；完成 PostgreSQL 适配器 metadata；上线 `BaseFormService` 并迁移 `credential_service`; 通过 `pytest -k accounts_sync`. |
| 扩展阶段 | 2025-12-25 ~ 2026-01-21 | Grid 页面/Store 全量迁移 ≥70%；账户适配器全部表驱动化；路由蓝图 (`routes/instances`, `routes/accounts`, `routes/tags`) 接入 ViewSet。 |
| 收敛阶段 | 2026-01-22 ~ 2026-02-05 | 工具/任务瘦身；执行全量 `make quality`, `make test`, `pytest --cov=app --cov-report=term-missing`; 输出《重构总结》与行数对比。 |

## 5. 影响与保障
- **功能影响**：配置化与表驱动策略都在原逻辑基础上加抽象，外部接口保持稳定；需重点验证批量操作、权限过滤、筛选卡片栅格、日志审计等关键链路。
- **性能**：统一 store/grid 后可集中优化缓存与批量请求；账户 SQL 模板需在开发库执行 `EXPLAIN ANALYZE`，防止回归。
- **协作**：在 `docs/refactor/` 增补 `grid_page_manifest.md` 与 `adapter_metadata_spec.md`，包含示例、接口约定；PR 模板新增“命名规范”“配置化覆盖”检查项。

## 6. 风险与缓解
| 风险 | 描述 | 缓解措施 |
| --- | --- | --- |
| 抽象过度导致可维护性下降 | Schema 过于复杂，定制逻辑被迫散落 | 采用“最低可用”原则，提供 escape hook；每个页面保留 10% 自定义脚本空间。 |
| SQL 模板化引入语义错误 | metadata 漏配字段或 SQL | 元数据与模板绑定单元测试；`tests/integration/accounts_sync` 做真实数据库校验。 |
| 重构周期拖延 | 阶段任务串行导致延期 | 两周一次复盘，必要时 Feature Flag 灰度上线；阻塞项先记录 fallback。 |
| 命名规范失守 | 新文件未通过脚本校验 | 将 `./scripts/refactor_naming.sh --dry-run` 纳入 CI gating，输出异常立即阻断。 |

## 7. 验收指标
1. 总行数 ≤ 92,500 行；`app/static/js` ≤ 23,000 行，`app/routes` ≤ 7,500 行，`app/services` ≤ 12,500 行。
2. Grid 页面新增/修改 80% 以上需求可通过配置完成，无需手写重复骨架。
3. 全量 `make quality`、`make test`、`pytest --cov=app --cov-report=term-missing` 通过，覆盖率 ≥80%。
4. 重构完成后 4 周内线上缺陷密度 ≤ 每周 1 例。
5. `./scripts/refactor_naming.sh --dry-run`、`make format`、`make quality` 成为 PR 必填验证项。

## 8. 执行要求
- 每阶段结束前更新本文件的进度章节，并在 `docs/refactor/` 下新增阶段总结。
- 提交前附带命令行输出截图或日志链接，确保审查可追溯。
- 任何争议命名/抽象方案需在架构例会上决定，避免私下分叉实现。
