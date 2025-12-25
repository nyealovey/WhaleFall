# 编码规范

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-11-21  
> 更新：2025-12-25  
> 范围：仓库内所有 Python/JS/CSS/Jinja2 代码与脚本

## 目的

- 统一编码风格与工程约束，减少“代码能跑但不可维护”的长期成本。
- 通过固定的门禁与检查方式，把问题拦在合并前（而不是线上）。

## 适用范围

- Python：`app/`、`scripts/`、`tests/`
- 前端与模板：`app/static/`、`app/templates/`

## 规则（MUST/SHOULD/MAY）

### 1) 格式与风格

- MUST：Python 统一四空格缩进，单行长度 ≤120。
- MUST：提交前运行 `make format`（black + isort），避免在评审中讨论格式。
- SHOULD：导入顺序遵循“标准库 → 第三方 → 本地模块”，并把 `app` 视为一方导入根。

### 2) 日志与可观测性

- MUST：新代码禁止使用 `print`；统一使用结构化日志（structlog）。
- MUST：日志字段使用结构化参数（`logger.info(..., key=value)`），禁止用 f-string 拼接日志内容。
- SHOULD：在路由/任务/服务边界写入 `module/action/context` 等维度字段，保证可追踪。

### 3) 异常处理（路由层强约束）

- MUST：Flask 路由必须通过 `app/utils/route_safety.py` 的 `safe_route_call` 执行业务闭包。
- MUST：通过 `expected_exceptions` 透传可控业务错误（例如 `ValidationError`、`NotFoundError`），其余异常由 helper 统一包装为 `SystemError`。
- MUST NOT：在路由层手写 `try/except Exception` + 记录日志 + 返回错误响应的模板（会导致口径漂移与日志重复）。

### 4) 类型治理（共享结构强约束）

- MUST：共享的 `TypedDict/TypeAlias/Protocol` 集中在 `app/types/`，业务模块禁止临时声明 `dict[str, Any]` 结构。
- SHOULD：新增/调整共享类型后，对相关代码运行 `ruff check <files> --select ANN,ARG,RUF012` 与 `make typecheck`，避免 `Any` 回退。

### 5) 前端与样式（跨域硬约束）

- MUST：仅支持桌面端，禁止新增移动端 `@media` 适配样式。
- MUST：色彩统一由 `app/static/css/variables.css` 或既有 Token 输出，禁止在 CSS/HTML/JS 中硬编码 HEX/RGB/RGBA。
- MUST：所有 `filter_card` 渲染的搜索/下拉控件必须采用 `col-md-2 col-12` 栅格（如需突破必须在评审中说明）。
- SHOULD：UI 相关细则以 [UI 标准索引](./ui/README.md) 为准。

### 6) 测试（当前仓库基线）

- MUST：单元测试放在 `tests/unit/`，并使用 `@pytest.mark.unit` 标注。
- SHOULD：新增测试优先覆盖“服务层/工具函数/规则引擎”等可复用逻辑，而不是在视图层堆集成用例。

## 正反例

### 路由必须使用 `safe_route_call`

```python
from flask import Blueprint, Response

from app.types import RouteReturn
from app.utils.route_safety import safe_route_call

bp = Blueprint("demo", __name__)


@bp.route("/api/demo", methods=["GET"])
def get_demo() -> RouteReturn:
    def _execute() -> RouteReturn:
        return (Response("ok"), 200)

    return safe_route_call(
        _execute,
        module="demo",
        action="get_demo",
        public_error="获取演示数据失败",
        context={"route": "demo.get_demo"},
    )
```

### Docstring（中文 + Google 风格）

```python
def resolve_page_size() -> int:
    """解析分页每页数量.

    兼容历史字段并做范围裁剪.

    Returns:
        解析后的每页数量.

    """
    return 20
```

## 门禁/检查方式

- Python 格式化：`make format`
- Python Lint：`ruff check .`（或按改动范围执行 `ruff check <paths>`）
- Python 类型检查：`make typecheck`（等价于运行 pyright）
- 命名巡检：`./scripts/refactor_naming.sh --dry-run`
- JS 静态检查（如改动 `app/static/js`）：`./scripts/code_review/eslint_report.sh quick`
- 结果结构漂移门禁（如涉及结果封套/错误字段）：`./scripts/code_review/error_message_drift_guard.sh`

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 重写并收敛为“可执行的规则 + 门禁”，移除与现状不一致的 Make/目录说明。
