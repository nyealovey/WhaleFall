# Security Audit (security-sentinel)
> 状态: Draft
> 负责人: team
> 创建: 2026-01-10
> 更新: 2026-01-10
> 范围: Flask UI + API v1 + scheduler/tasks + templates/static + nginx config + env.example
> 方法: 静态安全审计(输入点, SQL 注入, XSS, authn/authz, secrets, headers) + 项目内门禁脚本 + `npm audit`

## 1. Executive summary

总体风险评级: High

主要原因:

- Session cookie 的 `Secure` 标志被硬编码为 False, 且示例 Nginx 配置监听 80, 组合风险较高.
- 多处 public endpoint 暴露了版本与依赖状态(health, openapi), 存在信息泄露面.
- 前端存在少量 `innerHTML` 注入动态字符串的路径, 若后端错误文案或用户输入可控, 可能触发 DOM XSS.

正向发现(安全基建较完善):

- CSRF: `CSRFProtect` + `require_csrf` 已在 UI 与多处 API 写操作中启用.
- Open redirect: `resolve_safe_redirect_target` 采取了站内路径白名单策略.
- 日志脱敏: `app/utils/logging/handlers.py` 对 token/cookie/authorization/csrf 等字段做 scrubbing.
- secrets guard: `./scripts/ci/secrets-guard.sh` 通过, `env.example` 未包含非空敏感值.
- npm audit: `npm audit --omit=dev` 显示 0 vulnerabilities.

## 2. Risk matrix

| Severity | Finding | Location(s) |
| --- | --- | --- |
| High | Session cookie 未设置 Secure | `app/__init__.py` |
| Medium | Public health/openapi 信息泄露面 | `app/api/v1/namespaces/health.py`, `app/api/v1/__init__.py` |
| Medium | 可能的 DOM XSS (innerHTML + 未转义动态字符串) | `app/static/js/modules/views/instances/statistics.js`, `app/static/js/modules/ui/modal.js` 等 |
| Medium | CORS + credentials 组合依赖配置正确性 | `app/__init__.py`, `app/settings.py` |
| Low | Raw SQL DDL 使用 f-string(需保证标识符来源受控) | `app/services/partition_management_service.py` |

## 3. Detailed findings

### S1 (High): `SESSION_COOKIE_SECURE` 被硬编码为 False

位置:

- `app/__init__.py:configure_security`

现状:

- `configure_security` 无条件设置:
  - `SESSION_COOKIE_SECURE = False`
  - `SESSION_COOKIE_HTTPONLY = True`
  - `SESSION_COOKIE_SAMESITE = "Lax"`

风险:

- 生产环境若存在 HTTP 访问路径(示例 Nginx 为 80), 浏览器可能在明文链路发送 session/remember cookie, 存在会话劫持风险.
- 同时项目包含 Flask-Login session + JWT 返回的混合模式(`app/services/auth/login_service.py`), session cookie 安全属性尤为关键.

建议修复:

1. 将 `SESSION_COOKIE_SECURE` 与 `REMEMBER_COOKIE_SECURE` 与 `settings.force_https` 或 `settings.is_production` 绑定, 禁止硬编码 False.
2. 若生产一定走 HTTPS, 在边界层启用 TLS 并加 HSTS(Strict-Transport-Security).
3. 明确 "API 使用 JWT header" vs "API 使用 session cookie" 的模式, 尽量减少双栈鉴权带来的配置复杂度.

### S2 (Medium): Public health 与 OpenAPI 暴露信息面

位置:

- `app/api/v1/namespaces/health.py`:
  - `/api/v1/health/ping`, `/api/v1/health/basic`, `/api/v1/health`, `/api/v1/health/detailed` 默认无鉴权.
- `app/api/v1/__init__.py`:
  - `/api/v1/openapi.json` 永远可访问(即使 docs UI 可配置关闭).

风险:

- 暴露 version, uptime, DB/Redis 连接状态等, 可能帮助攻击者做指纹识别与时机选择.
- 对内网健康检查是合理诉求, 但建议区分 "public minimal" 与 "authenticated detailed".

建议修复:

- 生产环境:
  - 保留 `/ping` 与 `/basic` 的最小信息(不含依赖状态与版本细节), 或仅允许来自可信网段.
  - `/health/detailed` 与 `/openapi.json` 默认需要 `api_login_required` 或 admin 权限.
- 若确需对外开放 OpenAPI, 明确这是产品行为并配套 WAF/速率限制.

### S3 (Medium): DOM XSS 风险点(innerHTML + 未转义动态字符串)

位置(示例):

- `app/static/js/modules/views/instances/statistics.js:510`
  - `notification.innerHTML = \`...${message}\``
- `app/static/js/modules/ui/modal.js:97`
  - `confirmButton.innerHTML = \`...${text}\``
- `app/static/js/modules/views/instances/modals/batch-create-modal.js:102`
  - file.name 进入 innerHTML

风险:

- 若 `message/text` 来源包含可控 HTML(例如后端 error message 拼接了用户输入, 或某些 API 直接透传), 则可触发 DOM XSS.

PoC 思路:

- 若任一 API 返回 `message = "<img src=x onerror=alert(1)>"` 且被传入 `showErrorNotification(message)`, 则会执行.

建议修复:

- 统一策略: dynamic string 一律走 `textContent` 或 `escapeHtml`.
- 若必须渲染 HTML 片段, 只允许来自 "本地模板函数" 的静态片段, 禁止透传服务端字符串, 并加注释说明来源与约束.
- 对所有 `innerHTML =` 做一次针对 `${...}` 的扫描与收敛, 形成 lint/guard.

### S4 (Medium): CORS + credentials 依赖配置正确性

位置:

- `app/__init__.py:initialize_extensions`:
  - 对 `/api/v1/**` 启用 CORS, `supports_credentials=True`, `origins=settings.cors_origins`
- `app/settings.py:_load_web_settings`:
  - `CORS_ORIGINS` 仅做 CSV 解析, 未做安全校验.

风险:

- 若误配置 `CORS_ORIGINS=*` 或包含不可信 origin, 在 "cookie/session 参与鉴权" 的场景下会扩大跨站风险面.
- 当前系统既有 session 又返回 JWT, 需要明确 "API 鉴权是否依赖 cookie". 如果不依赖, 建议关闭 credentials.

建议修复:

- 在 settings 校验中显式禁止 `*` 与空 origin.
- 若 API 使用 Authorization header 的 JWT, 评估将 `supports_credentials` 设为 False.
- 配套 CSRF: 对 cookie-based 写操作保留 CSRF 校验, 对纯 bearer token 的 API 走不同策略.

### S5 (Low): Raw SQL DDL 使用 f-string, 需保证标识符来源严格受控

位置:

- `app/services/partition_management_service.py`:
  - `CREATE TABLE ... PARTITION OF ...`
  - `DROP TABLE IF EXISTS ...`
  - `COMMENT ON TABLE ...`

现状:

- 目前 partition_name 来自 prefix + date 格式化, table_name 来自内部配置, 在默认路径下不可被用户直接控制.

风险:

- 一旦未来引入可控标识符(例如从请求参数直传 partition/table name), 将立即变为 SQL 注入风险点(DDL 注入).

建议修复:

- 保持当前 "仅 date 输入" 的 API 形态, 禁止直接传入 table/partition name.
- 在执行前对 partition_name 做严格 regex 校验(例如 `^[a-z0-9_]+$`), 并对 table_name 做 allowlist.

## 4. Security checklist (snapshot)

- [x] Inputs validated/sanitized: 部分(分页参数与多个 payload 有显式校验, 但前端仍存在未转义 innerHTML 点)
- [x] No hardcoded secrets: 通过 `secrets-guard` 与抽样检索未发现非空密钥写死
- [x] Authn/authz present: UI 使用 Flask-Login + decorators, API 使用 `api_login_required`/`api_permission_required`/`jwt_required`
- [~] SQL injection protection: ORM 为主, 少量 DDL raw SQL 需持续保持输入受控
- [~] XSS protection: Jinja 默认转义较好, 前端 DOM XSS 需要收敛
- [ ] HTTPS enforcement: Nginx 示例为 80, 且 cookie secure 未开启, 需补齐生产配置
- [x] CSRF enabled: `CSRFProtect` + `require_csrf` 覆盖多处写操作
- [ ] Security headers: 未见 CSP/HSTS/XFO/XCTO 等统一配置
- [x] Error messages avoid secrets: 日志 scrubbing 覆盖 token/cookie/authorization/csrf 等关键字段
- [~] Dependency audit: npm 0 vulnerabilities, Python 未执行漏洞扫描(缺少 `pip-audit`)

## 5. Remediation roadmap (prioritized)

1. High: 修复 `SESSION_COOKIE_SECURE`(以及 remember cookie secure), 生产启用 TLS + HSTS.
2. Medium: 收敛所有 `innerHTML` 动态插值点, 统一使用 `escapeHtml`/`textContent`.
3. Medium: 生产环境限制 `/api/v1/health/detailed` 与 `/api/v1/openapi.json` 的访问策略.
4. Medium: 为 `CORS_ORIGINS` 增加安全校验, 明确是否需要 `supports_credentials`.
5. Low: 对 raw SQL DDL 标识符加 regex/allowlist 约束, 防止未来演进引入注入面.
6. Optional: 引入 Python 依赖漏洞扫描(例如 `pip-audit`)并固化到 CI.

