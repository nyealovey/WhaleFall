# 输入验证与权限装饰器去冗余计划

本文聚焦于**删除未使用的验证与装饰器代码**，使文档和仓库代码状态保持一致，避免后续开发被陈旧方案误导。

## 1. 当前使用情况快照

- **DataValidator** (`app/utils/data_validator.py`)：在 `app/routes/instances.py:196`、`:274`、`:480` 等处用于实例数据校验，是当前后端的主力验证工具。
- **DataValidator 扩展** (`app/utils/data_validator.py`)：提供 `sanitize_form_data`、`validate_required_fields`、`validate_db_type`、`validate_credential_type` 等通用安全验证能力，已在凭据、实例、标签路由中复用。
- **Decorators 模块** (`app/utils/decorators.py`)：`login_required`、`admin_required`、`permission_required` 及派生的 `view/create/update/delete_required`、`scheduler_view_required`、`scheduler_manage_required` 均被实际路由引用（例如 `app/routes/scheduler.py:38`、`:268`）。
- **InputValidator 与旧函数** (`app/utils/validation.py`)：未被任何模块导入，`rg -n "from app.utils.validation" app/ tests/` 返回 0；其中的 `validate_instance_data`、`validate_credential_data` 与 `DataValidator` 的实现重复。
- **已移除装饰器/辅助函数**：`login_required_json`、`validate_json`、`rate_limit` 已从 `app/utils/decorators.py` 删除；速率限制请使用 `app/utils/rate_limiter.py`。

## 2. 待删除代码清单

| 类别 | 定位 | 现状 | 处理建议 |
|------|------|------|----------|
| JSON 登录装饰器 | `app/utils/decorators.py` `login_required_json` | ✅ 已删除 | - |
| JSON 验证装饰器 | `app/utils/decorators.py` `validate_json` | ✅ 已删除 | - |
| 速率限制装饰器 | `app/utils/decorators.py` `rate_limit` | ✅ 已删除 | - |
| 输入验证模块 | `app/utils/validation.py` `InputValidator` 及 `validate_*` 函数 | ✅ 已删除 | - |
| 重复的实例/凭据验证 | `app/utils/validation.py` `validate_instance_data`、`validate_credential_data` | ✅ 已删除 | - |

> **确认方式**  
> - `rg -n "login_required_json" app/ tests/`  
> - `rg -n "@validate_json" app/`  
> - `rg -n "from app.utils.validation" app/ tests/`  
> - `rg -n "validate_instance_data(" app/ --type py | grep -v "data_validator"`  
> 以上命令当前均无匹配结果。

## 3. 清理实施步骤

1. **移除 decorators 中的未用装饰器**
   - 删除 `login_required_json`、`rate_limit`、`validate_json` 函数及相关注释。
   - grep 验证无残留：`rg -n "login_required_json|@rate_limit|@validate_json" app/`.

2. **移除 validation.py 中的冗余代码**
   - 若确认无下游依赖，可整 file 删除；否则仅移除 `validate_instance_data`、`validate_credential_data`、`InputValidator`。
   - 删除前再次确认：`rg -n "InputValidator" app/ tests/`、`rg -n "validate_request_data" app/`.
   - 删除后运行 `pytest -k data_validator` 快速抽查涉及验证的测试。

3. **同步文档与示例**
   - 更新 `examples/validation/standard_api_templates.py` 等示例，去除对已删除装饰器的引用。
   - 清理旧文档中的指令（例如 `docs/refactoring/decorator_usage_analysis.md` 中的 @validate_json 推荐）。

4. **保留的验证链说明**
   - REST 入参：使用各路由局部逻辑 + `DataValidator`。
   - 表单/凭据：复用 `DataValidator` 内的表单清理与凭据校验函数。
   - 权限控制：继续依赖 `app/utils/decorators.py` 的 `login_required` / `permission_required` 等。

## 4. 验收检查列表

- [x] `app/utils/decorators.py` 中仅保留被路由引用的装饰器，`rg` 未发现被删除函数的残留。
- [x] `app/utils/validation.py` 被移除或精简后，仓库无 `InputValidator` 相关引用。
- [x] 示例与文档不再提及 `@validate_json`、`@rate_limit`、`login_required_json`。
- [ ] `make test` 通过（至少跑 `pytest -k "decorators or validation"`）。
- [ ] `make quality` 无新增 lint/mypy 报错。

## 5. 后续可选优化

1. 若未来需要 JSON 验证，可基于 Marshmallow/Pydantic 在局部实现，不再回退到旧的装饰器。
2. 若需要速率限制，统一接入 `app/utils/rate_limiter.py` 的 `RateLimiter.rate_limit`，避免重复实现。
3. 后续路由若需管理员鉴权，直接复用 `app/utils/decorators.admin_required`，避免局部重复实现。

完成以上步骤后，仓库中仅保留真正使用的验证逻辑，后续关于“验证统一”的讨论可在此基础上继续推进。
