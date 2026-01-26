# Module: `app/utils/security`（redirect_safety/password_crypto_utils/sensitive_data/spreadsheet_formula_safety）

## Simplification Analysis

### Core Purpose

- `app/utils/redirect_safety.py`：`next` 等重定向目标的最小安全策略（防 Open Redirect）
- `app/utils/password_crypto_utils.py`：密码加解密（Fernet）与全局管理器初始化/获取
- `app/utils/sensitive_data.py`：日志/回显前对敏感字段统一脱敏
- `app/utils/spreadsheet_formula_safety.py`：CSV 导出时防 Spreadsheet Formula Injection
- 说明：速率限制已迁移到 `app/infra/rate_limiting.py`，并使用 Flask-Limiter 扩展（不再维护自研实现）

### Unnecessary Complexity Found

- `app/utils/sensitive_data.py:48`/`app/utils/sensitive_data.py:53`：默认敏感 key 已经是小写，仍然每次 `.lower()` + 额外中间变量 `key_lower` 属于可读性噪音（不改变行为）。

- `app/utils/password_crypto_utils.py:43`：`PasswordManager` 保存 `self.key` 但从不再使用；属于冗余状态（YAGNI）。
- `app/utils/password_crypto_utils.py:80`：异常路径每次 `get_system_logger()` 再赋值局部变量，属于重复样板（可用模块级 logger 复用）。

### Code to Remove

- `app/utils/sensitive_data.py:48`/`app/utils/sensitive_data.py:53`（已改写）- 去掉默认 key 的重复 lower 与中间变量
- `app/utils/password_crypto_utils.py:43`（已删除）- 未使用的 `self.key`
- `app/utils/password_crypto_utils.py:80`（已改写）- 模块级 `logger` 复用（净删局部变量样板）

- 说明：`app/utils/rate_limiter.py` 已整体移除，改用 Flask-Limiter；本模块仅保留真正“安全工具”职责。

### Simplification Recommendations

1. 工具函数保持“最小状态 + 最小样板”
   - Current: `PasswordManager` 保存无用 state；异常日志样板重复
   - Proposed: 移除无用字段；logger 复用
   - Impact: 更少状态、更少重复代码

### YAGNI Violations

- `PasswordManager.key`：无调用方

### Final Assessment

Complexity score: Low
Recommended action: 安全工具保持“最小可用”；速率限制由 Flask-Limiter 负责（避免自研扩展点）
