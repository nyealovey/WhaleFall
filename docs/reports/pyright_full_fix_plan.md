# Pyright 类型检查报告 (2025-12-11 16:12)

## 概览
- 诊断总数: **994** (错误 993, 警告 1)
- 受影响文件: **114** 个
- 详细报告: `docs/reports/pyright_full_2025-12-11_1612.txt`

## 规则分布
| 规则 | 数量 | 示例位置 | 处理建议 |
| --- | --- | --- | --- |
| reportAttributeAccessIssue | 302 | `app/__init__.py:120` | 为自定义 Flask 扩展和 `LoginManager` 属性定义子类/Protocol, 或用 `typing.cast` 标注新增字段 (`enhanced_error_handler`,`login_view`,`remember_cookie_*`)。 |
| reportArgumentType | 285 | `app/errors/__init__.py:355` | 避免把 `None` 或 SQLAlchemy `Column` 直接传入期望具体类型的函数; 先判空或将 `Column` 转换为原生值/`func.coalesce`。 |
| reportReturnType | 143 | `app/views/scheduler_forms.py:89` | 统一表单/视图返回 `Response`, 将 `(resp, status)` 包装为 helper 并在方法签名里声明。 |
| reportGeneralTypeIssues | 83 | `app/models/database_size_aggregation.py:144` | 禁止对 `Column` 做布尔判断或 `float()`，改用 `is not None`、`cast(float, value)`、`if column is not None`。 |
| reportCallIssue | 74 | `app/models/unified_log.py:122` | `UnifiedLog.create_log_entry` 调用使用了已移除的关键字; 同步 ORM 字段/工厂方法签名，或通过 dataclass 接收 `**payload`。 |
| reportOptionalMemberAccess | 34 | `app/routes/cache.py:35` | Service/manager 可能返回 `None`, 调用方法前需断言并在缺失时抛 `ValidationError` 或短路返回。 |
| reportIndexIssue | 12 | `tests/unit/utils/test_sensitive_data.py:23` | Mock 结构体必须实现 `__getitem__`, 测试里请改用真实 dict/list 或包装类。 |
| reportPossiblyUnboundVariable | 10 | `app/routes/partition.py:517` | 在 try/except 或条件外先初始化变量, 或拆出 helper 确保所有分支赋值。 |
| reportUndefinedVariable | 10 | `app/utils/data_validator.py:545` | 补齐 `Any`、`cls` 等定义, 需要的符号应从 `typing` 导入或作为参数传入。 |
| reportTypedDictNotRequiredAccess | 9 | `app/services/accounts_sync/accounts_sync_service.py:271` | 访问 TypedDict 可选字段前需 `if "key" in data` 判断, 或把字段声明为 `Required[]`。 |
| reportMissingImports | 8 | `app/views/classification_forms.py:15` | 调整导入路径或在 `pyrightconfig.json` 的 `extraPaths` 中加入 `app/forms`, 并安装 `pytest` stub。 |
| reportAssignmentType | 7 | `app/errors/__init__.py:159` | `LegacyAppErrorKwargs` 的字段需允许 `None`, 可把 TypedDict 定义改为 `str | None` 等, 并在 `_options_from_kwargs` 中确保类型匹配。 |
| reportOptionalSubscript | 6 | `tests/unit/services/test_classification_form_service.py:61` | 对可能为 `None` 的对象在取下标/索引前先 `assert obj is not None` 或提前返回。 |
| reportIncompatibleMethodOverride | 5 | `app/views/scheduler_forms.py:100` | 子类方法参数名必须与基类一致 (`resource_id`), 可以内部再转换为 `job_id`。 |
| reportUnboundVariable | 1 | `app/services/form_service/user_service.py:154` | 在函数顶部初始化 `resource: User | None = None`, 并确保所有分支赋值。 |
| reportUnusedExcept | 1 | `app/tasks/accounts_sync_tasks.py:130` | 捕获过宽 (`RuntimeError`) 导致 `PermissionSyncError` 分支永远不触发, 需改成更具体异常或移除多余 except。 |
| reportInvalidTypeVarUse | 1 | `app/types/query_protocols.py:10` | `QueryProtocol` 的 `TypeVar` 应设为 invariant (`TypeVar("T")`), 或在 `Protocol` 声明上标注 `covariant=False`。 |
| reportRedeclaration | 1 | `app/utils/safe_query_builder.py:50` | 避免在同一作用域重复声明 `parameters`, 改用新的变量名或 in-place 修改。 |
| reportInvalidTypeForm | 1 | `scripts/audit_colors.py:38` | 生成器函数声明返回 `Sequence[Path]` 不符, 应改为 `Generator[Path, None, None]` 或收集为 list 后返回。 |
| reportOperatorIssue | 1 | `scripts/code/safe_update_code_analysis.py:84` | `int | list` 不支持 `+= 1`, 需要在分支内区分类型或将容器结构固定。 |

## 建议动作
1. **框架扩展对齐**：在 `app/__init__.py` 中为自定义 Flask 应用和 LoginManager 属性定义 wrapper/Protocol, 并对 `current_app.login_manager` 使用 `typing.cast`, 先清空 300+ `reportAttributeAccessIssue`。  
2. **SQLAlchemy 列运算收敛**：聚合/统计模型 (`database_size_*`,`instance_size_*`,`unified_log`) 需改为使用表达式 API（`sqlalchemy.sql.expression`）或 `ColumnElement`，杜绝对列对象做布尔判断/直接 `float()`，同步解决部分 `reportArgumentType`。  
3. **TypedDict & 同步流程**：`accounts_sync_service`、权限 Diff 访问可选字段前添加存在性判断，必要时把字段改为 `Required`；同时让 `SyncStagesSummary` 可转为 `dict[str, Any]`（实现 `.to_dict()`），削减 `reportTypedDictNotRequiredAccess` 与相关 `reportArgumentType`。  
4. **视图/表单返回类型**：`scheduler_forms`、`resource_forms` 需统一返回 `Response`，将 `(response, status)` 改为 `make_response`，并确保覆盖方法签名与基类一致，解决 `reportReturnType`、`reportIncompatibleMethodOverride`。  
5. **测试与工具脚本**：在 `pyproject` 或 `requirements-dev` 中加入 `pytest` stub，修复 `test_sensitive_data` 等处的伪数据结构；`scripts/audit_colors.py`、`safe_update_code_analysis.py` 需按类型提示调整以消除生成器/运算错误。  
6. **运行策略**：每完成一批修复后执行 `npx pyright --warnings` 并在 CI 中上传最新报告，确保问题数量持续下降。  
