

# CSRF 与前端统一方案

目标
- 为所有有状态写操作（POST/PUT/PATCH/DELETE）统一一套 CSRF 校验模式。
- 保持一个轮子：后端统一使用 `Flask-WTF CSRFProtect` + 统一装饰器；前端统一使用 `X-CSRFToken` 头传递令牌。
- 提供清晰的落地步骤，避免多处各玩一套。

后端统一方案
- 全局启用：继续在 `app/__init__.py` 初始化 `CSRFProtect`，并在 CORS 中允许 `X-CSRFToken`。
- 令牌发放：统一使用 `/api/csrf-token` 接口提供令牌；前端缓存于 Cookie 或内存。
- 写操作校验：为所有 JSON 写操作统一使用 `@require_json_csrf`（示例装饰器见下），表单写操作沿用 Flask-WTF 自带 CSRF。
 - 错误返回样式：统一为增强错误结构（`enhanced_error_handler` 输出，包含 `error_id/category/severity/message/timestamp` 等字段）。

示例装饰器（后端）
```python
# app/utils/security_csrf.py
from functools import wraps
from flask import request
from flask_wtf.csrf import validate_csrf, CSRFError

def require_json_csrf(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 统一从 Header 读取 X-CSRFToken
        token = request.headers.get("X-CSRFToken")
        if not token:
            # 缺少令牌，交由全局错误处理器统一输出
            raise CSRFError("CSRF_MISSING")
        try:
            validate_csrf(token)
        except CSRFError:
            # 校验失败，交由全局错误处理器统一输出
            raise
        return f(*args, **kwargs)
    return wrapper
```

前端统一方案
- 令牌获取：应用启动或登录成功后请求一次 `/api/csrf-token`；统一使用 `app/static/js/common/csrf-utils.js` 的 `window.csrfManager` 管理令牌。
- Fetch 封装：写操作自动注入 `X-CSRFToken` 头，可使用 `csrfManager.addTokenToRequest` 或内置 `post/put/delete` 方法。
```js
// app/static/js/common/csrf-fetch.js（示例）
async function csrfFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const needCsrf = ['POST','PUT','PATCH','DELETE'].includes(method);
  const finalOptions = needCsrf ? await window.csrfManager.addTokenToRequest(options) : options;
  return fetch(url, finalOptions);
}

// 使用示例：
// 1) 通用写操作
await csrfFetch('/api/tags/batch', { method: 'POST', body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } });
// 2) 便捷方法
await window.csrfManager.post('/api/tags/batch', payload);
```

落地步骤
1) 路由治理：为所有 `/api/*` 的写操作统一加 `@require_json_csrf`；`auth.py` 现有逻辑保持不变但迁移到统一装饰器。
2) 响应统一：CSRF 失败由全局错误处理器输出增强错误结构（`enhanced_error_handler`）。
3) 前端改造：接入统一的 `csrf-utils.js`；登录后立即获取并缓存令牌。
4) 文档与测试：补充端到端用例（成功、缺失、错误令牌）。

兼容性与豁免
- 内部健康检查或只读 GET 接口无需 CSRF；如需豁免，明确标注并在统一清单维护。
- 第三方回调（Webhook）如不支持 CSRF，应转为签名校验，不混用 CSRF 与签名两套轮子。

统一校验清单（示例）
- 已统一：`auth.login`, `auth.logout`, `credentials.create/edit/toggle/delete`, `instances.create/edit/delete`, `scheduler.job control`, `tags.create/edit/delete/batch`。
- 待统一：个别历史接口（如 `storage_sync` 旧版、早期 `cache` 清理端点），按模块逐步补齐。

## 目标
- 统一 CSRF 获取与注入流程：页面加载获取令牌、表单隐藏字段、AJAX `X-CSRFToken` 头。
- 明确需要 CSRF 的路由列表（页面与 API），并在文档中维护。
- 对 CSRF 失败进行统一错误提示与恢复建议（重新获取令牌）。

## 现状
- CSRF 初始化在 `app/__init__.py`；API 提供 `/api/csrf-token`（`auth.py`）。
- 前端已在 `app/templates/base.html` 注入 `<meta name="csrf-token" content="{{ csrf_token() }}">`；统一工具位于 `app/static/js/common/csrf-utils.js`。

## 风险
- 令牌传递不统一导致偶发 403 或绕过风险。
- Cookie `SameSite` 策略与跨站场景处理不一致。

## 优先级与改进
- P0：统一前端集成与路由清单；文档与示例代码齐备。
- P1：Cookie 安全策略文档化（`SameSite=Strict/Lax`），跨域场景建议。
- P2：CSRF 失败统一响应与前端处理模式。

## 产出与检查清单
- 前端示例代码片段（表单/AJAX）；路由清单与排除项。
- 错误提示与恢复交互建议。

## 涉及代码位置
- 后端：`app/__init__.py`（CSRFProtect/CORS 初始化）
- 后端：`app/utils/security_csrf.py`（统一 JSON 写操作的 CSRF 装饰器）
- 后端：`app/routes/*.py`（所有写操作路由）
- 前端：`app/static/js/common/csrf-utils.js`（统一令牌管理与请求注入）、`app/templates/base.html`（令牌注入）