# Pyright 类型检查修复计划（基于 2025-12-15 11:53 报告）

最新报告: `docs/reports/pyright_full_2025-12-15_115353.txt`  
诊断总数: **1073**（`grep -c " - error:"`）  
受影响文件: **115**（路径行计数）  
主要规则数量：`reportAttributeAccessIssue` 323，`reportArgumentType` 322，`reportReturnType` 143，`reportCallIssue` 84，`reportGeneralTypeIssues` 71（其余见原报告）。

## 关键问题分组与修复策略

1) **错误类型定义过窄 (`app/errors/__init__.py`)**  
   - 问题：`LegacyAppErrorKwargs` 只接受必填字段，实际构造传入 `None`/缺省，触发 `reportAssignmentType`/`reportArgumentType`。  
   - 方案：将 TypedDict 中的 `severity`、`category`、`status_code` 等改为可选并提供默认，或在调用处补全必填字段（优先放宽 TypedDict 以减少调用面改动）。

2) **SQLAlchemy 列对象被布尔化/直接转换 (`app/models/database_size_aggregation.py` 等)**  
   - 问题：`Column[date|Decimal]` 参与 `if column` 或传给 `float/int` 构造，触发 `reportGeneralTypeIssues`/`reportArgumentType`。  
   - 方案：统一使用表达式 API：`column.is_(None)`/`column.isnot(None)` 判空；数值转换改为 `column.cast(Float/Integer)` 或在取值后再转换。逐块替换容量/统计相关模型中的聚合计算。

3) **ORM 查询方法缺少类型（大量 `reportAttributeAccessIssue`）**  
   - 问题：查询链上的 `is_`/`in_`/`contains`/`paginate`/`offset`/`with_entities` 被视为未知属性。  
   - 方案：新增本地 stub `app/types/stubs/sqlalchemy/orm.pyi` 覆盖常用 `Query`、`InstrumentedAttribute` 方法（或引入 `sqlalchemy-stubs`），并在热点模块必要处 `cast(Query[Any])` 兜底，避免大面积 `# type: ignore`。

4) **模型构造/解包签名不匹配 (`app/models/credential.py` 等)**  
   - 问题：TypedDict 解包包含模型未声明字段，报 `reportCallIssue`。  
   - 方案：仅传入模型声明字段，或在模型 `__init__` / 工厂函数中补充对应关键字参数并保持与 BaseModel 一致。

5) **第三方 stub 缺口 (`oracledb.is_thin` 及连接方法)**  
   - 问题：`is_thin`、`cursor`、`close` 未在 stub 中声明，导致 `reportAttributeAccessIssue`。  
   - 方案：在 `app/types/stubs/oracledb/__init__.pyi` 添加薄模式属性与基础连接/游标方法，或局部 `cast` 补注。

6) **零散返回值/可空访问/覆盖签名**  
   - 针对 `reportReturnType`、`reportOptionalMemberAccess`、`reportIncompatibleMethodOverride` 等残留，逐文件清理：补判空、校准覆盖方法签名，确保返回值与注解一致。

## 建议执行顺序（可分批验证）
1. **放宽错误 TypedDict**：修改 `LegacyAppErrorKwargs`，复跑 Pyright，收敛相关报错。  
2. **批量修正列布尔化**：优先 `database_size_aggregation.py` 及容量相关模型，改用表达式 API。  
3. **落地 ORM stub**：添加本地 sqlalchemy stub（或安装 `sqlalchemy-stubs`），复跑检查，期望大幅减少 `reportAttributeAccessIssue`。  
4. **模型构造修正**：处理 `credential` 等模型的 TypedDict 解包与签名对齐。  
5. **补齐第三方 stub**：覆盖 `oracledb` 常用属性/方法。  
6. **残留收口**：处理剩余 return/optional/override 类告警，确保改动文件无新增 Ruff/Pyright 告警。

## 验证与留存
- 每批改动后运行 `npx pyright --warnings`（可限定目录）与 `ruff check <files>`，生成新的报告快照并更新本计划。  
- 如果新增本地 stub，请在 `pyrightconfig.json` 配置 `extraPaths`/`typeshedPath` 指向 `app/types/stubs`，并保留 `app/py.typed`，确保 CI 能解析。  
- 阶段目标：完成 1-3 后将总错误数从 1073 降到 <500，再逐步清零。
