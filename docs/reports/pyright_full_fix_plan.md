# Pyright 类型检查修复计划（基于 2025-12-16 13:24 报告）

最新报告: `docs/reports/pyright_full_2025-12-16_132407.txt`  
诊断总数: **91 errors / 1 warning**（`grep -c " - error:"` / `grep -c " - warning:"`）  
受影响文件: **13**（段落计数）。相较 13:00 报告 **-137 errors / 0 warnings / -23 文件**，此前的 Flask 基类与装饰器类型问题已基本收敛，剩余集中在 CSRF 装饰器应用、少量路由返回值及测试用例。

## 关键问题分组与修复策略

1) **CSRF 装饰器与 RouteCallable 类型不匹配**  
   - 文件：`app/routes/auth.py`、`app/routes/users.py`。`require_csrf` 期望同步可调用，但 `as_view` 返回 `RouteCallable`（可能 Awaitable），传入后被判定不兼容。  
   - 处理要点：参照 `accounts/classifications` 修复方式，对 `as_view` 结果先 `cast(Callable[..., ResponseReturnValue], ...)` 再链式套 `require_csrf/login_required`；或扩展 `require_csrf` 支持 `Awaitable[ResponseReturnValue]` 并保持返回值透传。

2) **实例详情路由返回类型不符**  
   - 文件：`app/routes/instances/detail.py:381`。装饰器 `ReturnType` 与函数签名 `tuple[Response, int]` 不一致。  
   - 处理要点：将包装函数注解/返回值改为 `tuple[Response, int]`，必要时用 `cast` 保持链式装饰器的精确类型。

3) **脚本与 stub 类型告警**  
   - `scripts/code/safe_update_code_analysis.py`: 同一变量混用整数计数与列表，导致 `+=/append/sort` 报错。需拆分变量或定义结构体（dataclass/TypedDict）分别承载计数与列表。  
   - `app/types/stubs/sqlalchemy/orm.pyi`: `InstrumentedAttribute` 的 TypeVar 需标记 `covariant=True` 或添加注释说明，消除协变性 warning。

4) **测试缺少 pytest stub 与可选下标错误**  
   - 文件：`tests/unit/services/test_*.py`、`tests/unit/utils/test_*.py`、`tests/unit/services/test_sqlserver_adapter_permissions.py` 等。症状包括 `pytest` import missing、可选值下标/索引类型不匹配、伪 Session 构造参数类型错误。  
   - 处理要点：  
     - 在 `tests/conftest.py` 或各文件显式 `import pytest`，确保 pyright 能解析 stub；必要时将 tests 目录加入 `pyrightconfig.json` 的 `extraPaths`。  
     - 对可选/未知值先判空或使用 `cast`；为 Session/Client 构造轻量 stub 类满足所需属性；将示例数据改为可索引 dict/list，避免对 `None` 或标量取下标。

## 建议执行顺序
1. 优先修复 **auth/users 的 CSRF 类型问题**（cast 或扩展装饰器），快速消除路由阻断。  
2. 调整 **instances/detail** 的返回类型与装饰器适配。  
3. 处理 **脚本 + stub**（safe_update_code_analysis.py、orm.pyi）以清零 warning 与运算/属性错误。  
4. 批处理 **测试文件**：补齐 pytest stub、构造 Dummy Session/数据，修正可选下标与样例结构。  
5. 回跑 `npx pyright --warnings`（全量或针对改动文件），确认 0 报错后再执行 `make quality` / `make test`。

## 备注
- 新类型/别名仍集中于 `app/types/`；若扩展 `require_csrf` 支持 Awaitable，需确保包装函数返回 `ResponseReturnValue | Awaitable[ResponseReturnValue]` 的一致性。  
- 更新计划后，请在 PR 描述注明以 13:24 报告为基线，并记录消除的错误数量，便于后续对比。  
