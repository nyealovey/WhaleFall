# Pyright 类型检查修复计划（基于 2025-12-15 16:49 报告）

最新报告: `docs/reports/pyright_full_2025-12-15_164915.txt`  
诊断总数: **593 errors / 8 warnings**（`grep -c " - error:"`）  
受影响文件: **~70-80**（路径行计数）  
主要规则分布：`reportArgumentType`、`reportAttributeAccessIssue` 仍是主力，其次为 General/Return 类型。

### 规则命中统计（16:49 报告）
- reportArgumentType: **199**
- reportAttributeAccessIssue: **166**
- reportReturnType: **35**
- reportCallIssue: **61**
- reportGeneralTypeIssues: **35**
- reportIndexIssue: **35**
- reportOptionalMemberAccess: **11**
- reportOptionalSubscript: **14**
- reportTypedDictNotRequiredAccess: **9**
- reportMissingImports: **9**

## 关键问题分组与修复策略

1) **账户分类链路**  
   - `app/services/account_classification/cache.py`: 切片/Mapping 误用、规则列表类型不匹配 (`Mapping` vs `dict`).  
   - `mysql_classifier.py`/`sqlserver_classifier.py`: 对可能为 None 的可迭代直接遍历，及列表返回类型不匹配。  
   - `repositories.py`: SQLAlchemy `joinedload/join` 传入 RelationshipProperty 导致 ArgumentType。

2) **账户同步适配器**  
   - `postgresql_adapter.py`/`sqlserver_adapter.py`: 权限快照字段未在 `PermissionSnapshot` 定义；`setdefault` 键不匹配；`execute_query` 未标明接口。  
   - `account_query_service.py`: 关系 join/onclause 类型错误。

3) **测试缺失依赖与取下标**  
   - 多个 unit tests 缺少 `pytest` 解析（环境/配置）；部分测试对字典/对象使用 `__getitem__` 导致 Index/ArgumentType。需要补充测试依赖 stub 或调整测试数据类型。

4) **继续收敛 General/Index**  
   - 针对 35 条 General/Index Issues，优先处理账户分类/同步路径中的迭代与下标问题，剩余类比处理。

## 建议执行顺序（可分批验证）
1. **分类缓存/规则**：修正 `account_classification/cache.py` 的索引与规则列表类型；运行专属 pyright。  
2. **分类器迭代安全**：`mysql_classifier.py`/`sqlserver_classifier.py` 处理 None/非序列输入，统一返回 `list[str]`。  
3. **Repository & Query**：在 `repositories.py`、`account_query_service.py` 对关系属性使用 `cast(Query[Any], ...)` 或 `joinedload` 正确参数。  
4. **同步适配器字段**：扩充 `PermissionSnapshot` 字段满足 postgres/sqlserver 用例；`execute_query` 以协议/`cast` 兜底；`setdefault` 键统一。  
5. **测试层**：为 `pytest` 添加 dev 依赖或在配置中忽略测试 MissingImports；同时修正测试数据的索引/下标访问以匹配类型。  
6. **回归验证**：按改动文件跑 `npx pyright --warnings` 与 `ruff check`，必要时生成新的全量报告并更新本计划。

## 验证与留存
- 每批改动后运行 `npx pyright --warnings`（可限定目录）与 `ruff check <files>`，生成新的报告快照并更新本计划。  
- 如果新增本地 stub，请在 `pyrightconfig.json` 配置 `extraPaths`/`typeshedPath` 指向 `app/types/stubs`，并保留 `app/py.typed`，确保 CI 能解析。  
- 阶段目标：完成 1-4 后将总错误数从 ~688 进一步压降，优先清空 AttributeAccess/返回类型高频路由，再逐步清零。

## reportArgumentType 集中修复方案（226 条）
重点来源与处理策略：
- **路由装饰器/注册参数不匹配**：`auth.py` 等使用 `login_required`/自定义装饰器后传入 `add_url_rule`，类型推断为 `_Wrapped[...]`。方案：引入 `RouteCallable` 并 `cast`，或通过 ParamSpec 包装自定义装饰器保持原签名。
- **返回值形态与注解不一致**：`safe_route_call` 包装后仍注解为 `Response`，实际返回 `tuple[Response,int]`。方案：定义统一 `RouteReturn = Response | tuple[Response, int]`，并在返回处 `cast(RouteReturn, safe_route_call(...))`。
- **模型/TypedDict 形参类型窄化**：`database_type_config`、`sync_session` 等函数返回/接受更窄类型导致参数不匹配。方案：放宽 TypedDict/返回值注解或在调用点做显式转换（`dict(...)`/`cast`）。
- **Context/Mapping 变体**：`safe_route_call` 的 `context` 期望 `ContextDict`，调用方传 `dict[str, object]`。方案：统一导入 `ContextDict` 并用 `cast(ContextDict, {...})` 或调整值类型到 `ContextValue`。
- **SQLAlchemy 表达式参数**：将 `bool`/`object` 直接传入 `filter`、`join`、`order_by` 触发参数类型错误。方案：先 `cast(ColumnElement[bool], column.is_(...))` 或通过 `cast(Query[Any], query)` 后再调用链式方法。

执行顺序建议（argumentType 专项）：
1) 路由层：`app/routes/auth.py`、`cache.py`、`dashboard.py`、`health.py`、`partition.py`、`main.py`、`instances/statistics.py` —— 统一 `RouteCallable` 与返回类型。
2) 模型/服务：`database_type_config.py`、`sync_session.py`、`sync_instance_record.py` —— 放宽返回类型或显式转换。
3) Query/SQLAlchemy：容量、标签、分区等涉及 `filter/join/order_by` 的文件 —— 使用 `ColumnElement`/`InstrumentedAttribute` 兜底。
4) Context/Mapping：对 `safe_route_call` 传参的上下文统一 `ContextDict` 或 `Mapping[str, ContextValue]`。
