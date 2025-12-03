# 账户同步 API 404 问题分析

## 背景
- 页面：`/instances/<id>` 实例详情页，工具栏点击“同步账户”。
- 前端日志：
  - `detail.js` 输出“开始同步账户 …”
  - `http-u.js` 捕获 `POST http://10.10.66.45/accounts/sync/api/instances/89/sync 404 (NOT FOUND)`
  - `syncAccounts()` 捕捉异常并提示“账户同步失败”。

## 调用链
1. `detail.js:232-282` 触发 `syncAccounts()` → `instanceStore.actions.syncInstanceAccounts()`（或直接 `instanceService.syncInstanceAccounts()`）。
2. `InstanceManagementService.syncInstanceAccounts()`（`app/static/js/modules/services/instance_management_service.js:67-83`）拼装 URL：优先使用 `options.customUrl`，否则回退硬编码 `/accounts/sync/api/instances/${id}/sync`。
3. HTTP 客户端 `http-u.js` 发起请求，后端返回 404。
4. 错误在 `syncAccounts()` 的 `catch` 中统一处理。

## 后端路由现状
- 蓝图：`app/routes/accounts/sync.py` 定义 `accounts_sync_bp`，自身 `url_prefix="/sync"`。
- 注册：`register_blueprints()` 以 `(accounts_sync_bp, "/accounts")` 方式挂载 → 实际 URL `/accounts/sync/api/...`。
- 文档：`docs/api/API_ROUTES_DOCUMENTATION.md` 也记录为 `/accounts/sync/api/...`。

## 根因
1. **路径拼接脆弱**：蓝图内部 `/sync` + 注册时 `/accounts`，一旦部署环境遗漏外层前缀（例如运维误配或低版本分支仍旧 `url_prefix=None`），最终路由会变成 `/accounts/api/...`，与前端硬编码 `/accounts/sync/...` 不一致，直接 404。
2. **前端缺少单一真相源**：
   - 模板 `instances/detail.html` 通过 `data-sync-accounts-url` 注入真实 URL，但仅限这个页面；其他入口（例如批量操作、store 初始化时的兜底逻辑）没有注入，自动回落到硬编码字符串。
   - 多处脚本手写 `/accounts/sync`，维护成本高，一旦后端改动需逐文件更新，极易遗漏。
3. **缺乏守护**：
   - 没有集成测试覆盖 `POST /accounts/sync/api/instances/<id>/sync`。
   - Lint/脚本无法检测裸写路径或蓝图前缀漂移；`scripts/refactor_naming.sh` 无法发现这种 API 级错误。

## 重构方向
1. **统一路由前缀**
   - 将 `accounts_sync_bp` 的 `url_prefix` 直接设为 `/accounts/sync`，注册时不再叠加额外前缀，防止环境差异导致路径错乱。
   - 明确文档：蓝图自身携带完整前缀，部署层无需再拼接。若需 `/api` 全局前缀，应通过 `APPLICATION_ROOT` 或反向代理处理。
2. **前端配置化**
   - 在 `window.AppConfig` 或 `app/static/js/modules/config/api_endpoints.js` 中集中声明 `accounts.syncInstance`、`accounts.syncAll`，由后端模板统一注入。
   - `InstanceManagementService` 接受注入的 endpoint，不再硬编码；`detail.js` 和 `instance_store.js` 只读配置或 `data-*` 中同一字段，彻底移除 fallback。
3. **测试/守护**
   - 新增集成测试：命中单实例同步与批量同步接口，验证 200/JSON 结构，覆盖 404 与权限分支。
   - 为前端加入静态检查（eslint、自定义脚本）或简单单测，扫描 `app/static/js` 中裸写 `/accounts/sync`。
   - 在 CI 或 `make quality` 中加入 `flask routes | rg accounts/sync` 对比，防止路由变更未同步。

## 验证步骤（实施重构后）
1. `make install && make dev start-flask` 启动本地服务。
2. `curl -X POST http://127.0.0.1:5001/accounts/sync/api/instances/<id>/sync -H "X-CSRFToken:..."`，确认 200 与期望 JSON。
3. 浏览器手动触发“同步账户”，Network 面板应命中配置化 URL 且响应成功。
4. 运行 `pytest -k sync_accounts -m "unit or integration"`、`make quality`，并执行 `./scripts/refactor_naming.sh --dry-run` 确认命名检查通过。

## 风险/注意
- 改动蓝图前缀需同步 Nginx/OpenResty 转发路径。
- 需确保所有消费 `InstanceManagementService` 的页面都能注入新配置，否则旧脚本会抛“服务未初始化”。
- 清理文档与脚本中历史 `/accounts_sync/api/...` 记载，避免团队继续引用过期接口。
