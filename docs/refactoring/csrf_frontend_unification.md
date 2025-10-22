# CSRF 校验与前端令牌交互统一方案

## 目标
- **后端**：所有需要 CSRF 的 JSON 写操作使用同一套校验逻辑，避免在各路由中手写 `validate_csrf`。
- **前端**：写操作默认复用统一的 `csrfManager`，不再在页面脚本中手动拼 `X-CSRFToken`。
- **文档与测试**：给出清晰的改造顺序和验收清单，减少重复实现与遗漏。

---

## 现状速览（2025-10）

| 组件 | 现状 | 问题 |
|------|------|------|
| `app/__init__.py` | 全局初始化 `CSRFProtect`，CORS 允许 `X-CSRFToken` | ✅ |
| `app/routes/auth.py` | 提供 `/api/csrf-token` 接口；部分接口内部直接 `validate_csrf` | ❌ 仅局部使用，其他 API 未统一 |
| 其他后端路由 | 未显式校验 CSRF（默认依赖表单 CSRF 或完全缺失） | ❌ JSON 写操作缺少统一入口 |
| `app/static/js/common/csrf-utils.js` | 提供 `window.csrfManager`、`getCSRFToken` 等工具 | ✅ 可作为唯一入口 |
| 各页面脚本 | 仍存在大量 `$('meta[name="csrf-token"]').attr('content')` 等手工注入 | ❌ 与 `csrf-utils` 重复 |
| 模板 | `base.html` 注入 `<meta name="csrf-token" ...>`，提供 `window.getCSRFToken` fallback | ✅ |

> 结论：后端缺统一装饰器，前端工具存在但使用方式不一致 —— 需要一次聚合清理。

---

## 统一方案设计

### 1. 后端：新增通用装饰器

在 `app/utils/decorators.py` 中新增 `require_csrf`，集中处理 JSON/表单写操作并复用现有日志逻辑：

```python
from flask_wtf.csrf import CSRFError, validate_csrf

CSRF_HEADER = "X-CSRFToken"
SAFE_CSRF_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

def _extract_csrf_token() -> str | None:
    token = request.headers.get(CSRF_HEADER)
    if token:
        return token

    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            token = payload.get("csrf_token")
            if token:
                return token

    return request.form.get("csrf_token")


def require_csrf(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method.upper() in SAFE_CSRF_METHODS:
            return view(*args, **kwargs)

        token = _extract_csrf_token()
        if not token:
            raise AuthorizationError("缺少 CSRF 令牌", message_key="CSRF_MISSING")

        try:
            validate_csrf(token)
        except CSRFError as exc:
            raise AuthorizationError("CSRF 令牌无效，请刷新后重试", message_key="CSRF_INVALID") from exc

        return view(*args, **kwargs)

    return wrapped
```

使用方式：
```python
from app.utils.decorators import require_csrf

@blueprint.route("/api/examples", methods=["POST"])
@login_required
@require_csrf
def create_example():
    ...
```

- JSON 写操作 → 统一走 `_extract_csrf_token()`，避免各路由重复 `request.headers.get(...)`。
- 表单写操作 → 仍支持 `csrf_token` 隐藏字段，兼容 Flask-WTF。
- 错误处理 → 统一抛 `AuthorizationError`，全局错误处理器已能输出结构化响应。

### 2. 前端：唯一入口 `csrfManager`

`app/static/js/common/csrf-utils.js` 已提供：
- `csrfManager.getToken()` / `window.getCSRFToken()` 获取缓存令牌
- `csrfManager.addTokenToRequest(options)`
- `csrfManager.post|put|delete`

统一要求：
1. 写操作统一使用 `csrfManager` 或包装后的 `csrfFetch`。
2. 清理页面脚本中手动 `$('meta[name="csrf-token"]').attr('content')` 逻辑。
3. 保留 `<meta name="csrf-token">` 作为后备来源，供 `csrf-utils.js` 初始读取。

示例封装（可选）：
```js
// app/static/js/common/csrf-fetch.js
export async function csrfFetch(url, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    return fetch(url, options);
  }

  const finalOptions = await window.csrfManager.addTokenToRequest({
    credentials: "include",
    ...options,
  });

  return fetch(url, finalOptions);
}
```

---

## 落地步骤

1. **建立后端装饰器**
   - [x] 在 `app/utils/decorators.py` 中实现/完善 `require_csrf`。
   - [x] 在 `app/routes/auth.py` 等现有手动校验处替换为装饰器。
   - [x] 扫描写接口（POST/PUT/PATCH/DELETE），逐步加装饰器。
   - [ ] 在路由豁免清单记录无需 CSRF 的接口（健康检查、开放 WebHook 等；**调度器控制接口属于敏感写操作，不应豁免**）。

2. **统一前端调用**
   - [ ] 以 `app/static/js/common/csrf-utils.js` 为基础，为所有写操作封装统一入口。
   - [ ] 清理页面脚本，改用 `csrfManager` 或 `csrfFetch`。
   - [ ] 登录/刷新流程中确保调用 `/api/csrf-token`，更新 `csrf-utils.js` 的缓存逻辑。

3. **统一错误处理**
   - [ ] 全局错误处理器（`app/errors`）确认能识别 `AuthorizationError` 并返回统一结构。
   - [ ] 前端在统一请求封装里处理 `403/CSRF_INVALID`，提示用户刷新令牌。

4. **验收清单**
   - [x] `rg -n "validate_csrf" app/routes/` → 仅保留装饰器内部使用。
   - [ ] `rg -n "meta\\[name=\"csrf-token\"\\]" app/static/js` → 确认页面脚本不再直接读取。
   - [ ] 手动验证：令牌缺失、令牌过期、跨页跳转、登录/登出流程。
   - [ ] 更新文档 & 编写基础测试（单元 + 集成）。

---

## 兼容与豁免策略

- **后台任务/健康检查**：GET/只读接口无需 CSRF。
- **第三方回调**：使用签名验证（HMAC 等），不要混用 CSRF。
- **跨域场景**：在统一封装中明确 `credentials` 策略；文档说明 `SameSite` 策略和需要手动处理的场景。

---

## 参考代码位置

- 后端初始化：`app/__init__.py` (`CSRFProtect`, CORS header)
- 令牌接口：`app/routes/auth.py:get_csrf_token`
- 统一装饰器：`app/utils/decorators.py` (`require_csrf`)
- 前端工具：`app/static/js/common/csrf-utils.js`
- 模板注入：`app/templates/base.html` (`meta[name="csrf-token"]`)

---

通过这次统一：
1. 后端不再散落 `validate_csrf` 调用；
2. 前端写操作全部走一个入口；
3. 文档、测试与豁免清单一体化维护，减少踩坑与重复编码。
