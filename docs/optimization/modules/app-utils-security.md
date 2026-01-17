# Module: `app/utils/security`（rate_limiter/redirect_safety/password_crypto_utils/sensitive_data/spreadsheet_formula_safety）

## Simplification Analysis

### Core Purpose

- `app/utils/rate_limiter.py`：登录/密码重置等敏感接口的速率限制（JSON API 与页面路由共用）
- `app/utils/redirect_safety.py`：`next` 等重定向目标的最小安全策略（防 Open Redirect）
- `app/utils/password_crypto_utils.py`：密码加解密（Fernet）与全局管理器初始化/获取
- `app/utils/sensitive_data.py`：日志/回显前对敏感字段统一脱敏
- `app/utils/spreadsheet_formula_safety.py`：CSV 导出时防 Spreadsheet Formula Injection

### Unnecessary Complexity Found

- `app/utils/rate_limiter.py:273`/`app/utils/rate_limiter.py:395`：`@overload` 仅服务类型提示，运行期无收益；且维护成本高、干扰阅读（YAGNI）。
- `app/utils/rate_limiter.py:291`/`app/utils/rate_limiter.py:413`：`login_rate_limit/password_reset_rate_limit` 支持“直接传 func”与“装饰器工厂”两种调用方式，仓库实际调用链中只需要“装饰器工厂”（`@xxx()` / `xxx()(func)`）。保留双形态属于 YAGNI。
- `app/utils/rate_limiter.py:315`/`app/utils/rate_limiter.py:444`：`has_app_context()` 分支属于“看起来兜底”，但该装饰器本身依赖 `request`，正常路径必然在请求上下文内；保留分支只增加噪音。

- `app/utils/sensitive_data.py:48`/`app/utils/sensitive_data.py:53`：默认敏感 key 已经是小写，仍然每次 `.lower()` + 额外中间变量 `key_lower` 属于可读性噪音（不改变行为）。

- `app/utils/password_crypto_utils.py:43`：`PasswordManager` 保存 `self.key` 但从不再使用；属于冗余状态（YAGNI）。
- `app/utils/password_crypto_utils.py:80`：异常路径每次 `get_system_logger()` 再赋值局部变量，属于重复样板（可用模块级 logger 复用）。

### Code to Remove

- `app/utils/rate_limiter.py:273`/`app/utils/rate_limiter.py:395`（已删除）- `@overload` 块（Estimated LOC reduction: ~18）
- `app/utils/rate_limiter.py:291`/`app/utils/rate_limiter.py:413`（已改写）- 去掉 `func` 直传形态，收敛为装饰器工厂（并移除 `if func is None` 分支：`app/utils/rate_limiter.py:390`/`app/utils/rate_limiter.py:515`）
- `app/routes/auth.py:27`（已更新）- 对齐新调用方式：`password_reset_rate_limit()(...)`

- `app/utils/rate_limiter.py:315`/`app/utils/rate_limiter.py:444`（已删除）- `has_app_context()` 伪兜底分支（净删大量缩进与重复赋值）
- `app/utils/sensitive_data.py:48`/`app/utils/sensitive_data.py:53`（已改写）- 去掉默认 key 的重复 lower 与中间变量
- `app/utils/password_crypto_utils.py:43`（已删除）- 未使用的 `self.key`
- `app/utils/password_crypto_utils.py:80`（已改写）- 模块级 `logger` 复用（净删局部变量样板）

- Estimated LOC reduction: ~63 LOC（净删；`git diff --numstat` 合计 -63）

### Simplification Recommendations

1. 仅保留“仓库真实调用链”需要的装饰器形态
   - Current: `rate_limiter` 同时支持 `decorator(func)` 与 `decorator()(func)` 两套接口
   - Proposed: 统一为装饰器工厂（`@xxx()` / `xxx()(func)`）
   - Impact: API 面更小、更一致；删除 overload 与分支后阅读成本显著下降

2. 删除“看似兜底但无实际收益”的分支
   - Current: `has_app_context()` 分支与 `request` 依赖并存，兜底不成立
   - Proposed: 直接依赖请求上下文，减少分支与缩进
   - Impact: 更少路径需要理解/测试；不改变真实运行场景行为

3. 工具函数保持“最小状态 + 最小样板”
   - Current: `PasswordManager` 保存无用 state；异常日志样板重复
   - Proposed: 移除无用字段；logger 复用
   - Impact: 更少状态、更少重复代码

### YAGNI Violations

- `rate_limiter` 的 overload 与双调用形态：无新增收益，且扩大维护面
- `has_app_context()` 分支：无真实运行期收益（与 `request` 依赖冲突）
- `PasswordManager.key`：无调用方

### Final Assessment

Total potential LOC reduction: ~63 LOC（已落地）
Complexity score: Medium → Low
Recommended action: 保持安全工具“最小可用”形态；新增分支/扩展点必须先出现明确调用方与测试用例

