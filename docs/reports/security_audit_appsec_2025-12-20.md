# WhaleFall/鲸落 安全评审报告（以漏洞/bug 为核心）

- 日期：2025-12-20
- 评审范围（静态代码审计为主）：
  - 后端：`app/routes/**`、`app/services/**`、`app/utils/**`、`app/models/**`、`app/__init__.py`、`app/settings.py`
  - 前端：`app/templates/**`、`app/static/js/**`、`app/static/vendor/**`
  - 配置/部署：`env.production`、`docker-compose*.yml`、`Dockerfile.prod`、`nginx/**`、`requirements*.txt`、`pyproject.toml`、`uv.lock`、`package*.json`
- 说明：
  - 本报告重点聚焦“可被利用”的安全缺陷与高风险配置，不讨论代码风格。
  - 证据中的敏感值一律不在文档中展示（以 `<REDACTED>` 表示），但会给出准确的文件与行号。

---

## I. 威胁建模摘要

### A. 威胁建模（轻量）

**资产（数据/权限/系统能力）**

- 系统管理员权限、普通用户权限（`User.role` / 权限装饰器）
- 内部数据库（PostgreSQL/SQLite）中的：
  - 用户、实例、账户权限、分类/标签、同步会话、统一日志（`UnifiedLog`）
  - 外部数据库连接凭据（`Credential.password` 加密存储）
- 外部数据库连接能力（SQLServer/MySQL/PostgreSQL/Oracle 等适配器）
- 调度器能力（APScheduler 任务控制、手动执行、重载）
- 文件导入/导出能力（CSV 导入、CSV/JSON 导出）
- 日志系统与诊断能力（结构化日志入库、日志检索/导出）

**入口（路由/任务/导入导出/外部连接）**

- 页面路由：登录、控制台各管理页面（instances/tags/users/history/partition/scheduler 等）
- JSON API：`*/api/*` 系列（实例、账户同步/容量同步、连接测试、日志检索、分区管理、缓存管理等）
- 后台任务：`app/tasks/**`，以及 `/scheduler/*` 对 APScheduler 的管理入口
- 文件：实例 CSV 批量导入、多个 CSV/JSON 导出接口
- 外部连接：连接测试/同步会连接到用户配置的外部 DB 主机与端口

**信任边界（浏览器↔服务端↔DB↔外部 DB/第三方）**

- 浏览器（不可信输入） → Flask（需要认证/授权/CSRF/输入校验）
- Flask → 内部数据库（需最小权限 + 防注入 + 事务一致性）
- Flask → Redis（缓存/限流，需鉴权与网络隔离）
- Flask → 外部数据库（潜在“网络探测/横向移动”能力，需要强授权与审计）
- 代码仓库/镜像构建链路 → 生产环境（供应链与密钥管理边界）

---

## II. 攻击面清单（按入口类型分组）

### B. 攻击面盘点

**页面路由**

- `/auth/login`、`/dashboard/*`、`/instances/*`、`/tags/*`、`/users/*`
- `/history/logs/*`、`/history/sessions/*`
- `/partition/*`、`/scheduler/*`（后台/运维能力相关页面）

**JSON API**

- 认证相关：`/auth/api/login`、`/auth/api/refresh`、`/auth/api/me`、`/auth/api/csrf-token`
- 日志相关：`/history/logs/api/*`、`/files/api/log-export`
- 分区相关：`/partition/api/create`、`/partition/api/cleanup`、`/partition/api/*`
- 连接相关：`/connections/api/test`、`/connections/api/batch-test`
- 实例/账户/容量同步：`/instances/api/*`、`/databases/api/instances/<id>/sync-capacity`、`/accounts/sync/api/*`

**后台任务/调度**

- `app/scheduler.py` + `app/tasks/**`（容量采集、聚合、账户同步、分区任务等）
- `/scheduler/api/jobs/*`（查看/编辑/暂停/恢复/执行/重载任务）

**文件/导入导出**

- CSV 导入：`/instances/batch/api/create`
- CSV/JSON 导出：`/files/api/account-export`、`/files/api/instance-export`、`/files/api/database-ledger-export`、`/files/api/log-export`

**外部连接/适配器**

- 连接测试与同步：`ConnectionFactory`、各 DB adapter（SQLServer/MySQL/PostgreSQL/Oracle）

**依赖/静态 vendor**

- Python：`requirements.txt`（hash 锁定）、`requirements-prod.txt`、`uv.lock`
- 前端 vendor：`app/static/vendor/**`（Axios/Lodash/Bootstrap/Grid.js 等）
- 部署：`Dockerfile.prod`、`docker-compose.prod.yml`、`nginx/**`

---

## III. 漏洞/安全 bug 清单（按严重度分组）

### C. 漏洞扫描（逐维度覆盖，重点给出可利用路径与证据）

> 注：以下每条均包含“攻击路径 / 证据 / 影响 / 根因 / 修复 / 验证”。如需我进一步为某条漏洞提供 PoC 脚本或自动化测试用例模板，可继续指定。

#### 安全检查维度覆盖清单（1-9，不跳过）

1) 认证（Authentication）  
   - 发现：会话 Cookie `Secure` 关闭（High-4）、登录日志记录明文口令（Critical-3）、环境误配回退风险（IV-1）。  
2) 授权（Authorization / Access Control）  
   - 发现：日志中心/导出仅登录可访问（Critical-3）、分区危险操作仅 `view`（High-6）。  
3) 输入校验与注入（Injection）  
   - 发现：连接测试回显底层异常（High-7，信息泄露类）、分区清理参数缺少边界（High-6）；未发现明显命令注入/反序列化（基于 `rg` 搜索无 `subprocess/os.system/pickle/yaml.load` 直接使用）。  
4) CSRF/CORS 与浏览器安全  
   - 发现：Logout 支持 GET 导致登出 CSRF（Low-13）；缺失 CSP/HSTS/Frame-Options 等安全头（Medium-11）。  
5) 文件与导入导出安全  
   - 发现：CSV 导出缺少公式注入防护（Medium-9）；日志导出权限过宽且 limit 无上限（Critical-3 / IV-4）。  
6) 错误处理与信息泄露  
   - 发现：连接测试错误回显（High-7）、健康检查泄露系统状态（Medium-10）、日志系统落库字段缺少脱敏（Critical-3）。  
7) 依赖与供应链  
   - 发现：生产依赖存在 CVE（Medium-12）；仓库中存在私钥与生产口令（Critical-1/2）。  
8) 安全配置与部署  
   - 发现：生产 compose 暴露 5432/6379（High-5）；Cookie 策略未按环境区分（High-4）；健康检查对公网暴露（Medium-10）。  
9) 业务逻辑安全  
   - 发现：分区 cleanup 可被滥用触发大范围 DROP（High-6）；连接测试可被滥用进行内网探测（High-7）；`success` 字段缺失默认视为成功（IV-5，误导监控/审计）。  

---

### Critical

#### 1) 生产环境敏感信息被提交到仓库（DB/Redis 密码、SECRET_KEY、JWT_SECRET_KEY、凭据加密密钥）

- 证据：
  - `env.production:22`（`POSTGRES_*`）、`env.production:29`（`REDIS_PASSWORD`）
  - `env.production:34`（`SECRET_KEY`）、`env.production:35`（`JWT_SECRET_KEY`）
  - `env.production:39` / `env.production:40`（`PASSWORD_ENCRYPTION_KEY` 重复且出现明文值）
- 攻击路径：
  1. 攻击者获取代码仓库只读权限/备份泄露/CI 日志泄露；
  2. 直接使用泄露的数据库/Redis/应用密钥登录生产资源（或伪造 Session/JWT）；
  3. 横向读取业务数据、日志、凭据，或直接篡改数据与配置。
- 影响：
  - 生产数据库与缓存可能被直接接管；
  - `SECRET_KEY/JWT_SECRET_KEY` 泄露后，可导致会话/令牌伪造与权限提升；
  - `PASSWORD_ENCRYPTION_KEY` 泄露后，外部数据库凭据的加密存储形同虚设（拿到密文即可解密）。
- 根因：
  - 将“生产环境示例文件”作为真实密钥载体提交到仓库，违反密钥不入库原则；
  - 缺少 secret scanning（如 gitleaks）与提交门禁。
- 修复：
  - 最小修复（立即）：
    - 立刻从仓库移除敏感值（替换为占位符），并在生产侧**全部轮换**：Postgres/Redis 密码、`SECRET_KEY`、`JWT_SECRET_KEY`、`PASSWORD_ENCRYPTION_KEY`。
    - 检查并清理 Git 历史（仅删除文件本身不等于清除历史泄露）。
  - 结构性修复（中期）：
    - 用密钥管理系统/容器 secret（Docker secrets/K8s secrets/Vault）注入，`env.production` 仅保留“变量清单 + 示例值占位”。
  - 长期治理：
    - 加入 secret scanning（pre-commit + CI），阻断 `SECRET_KEY=...`、`BEGIN PRIVATE KEY`、常见密码模式。
- 验证：
  - 仓库侧：`rg -n "SECRET_KEY=|POSTGRES_PASSWORD=|REDIS_PASSWORD=|PASSWORD_ENCRYPTION_KEY=" env.production`
  - 生产侧：
    - 轮换后，确认旧密钥无法再通过 JWT/Session 验证；
    - 数据库/Redis 使用旧口令连接失败。

---

#### 2) TLS 私钥被提交到仓库（潜在中间人/伪造风险）

- 证据：`nginx/local/ssl/key.pem:1`（文件内容为 PEM 私钥头）
- 攻击路径：
  1. 攻击者获取仓库（或镜像构建产物）；
  2. 若该私钥被用于任何环境的 TLS（尤其是生产或被用户信任的证书链），攻击者可伪造服务或解密流量。
- 影响：
  - TLS 身份可信度破坏（服务端身份被伪造）、潜在 MITM；
  - 供应链风险：镜像/包中携带私钥，扩大泄露面。
- 根因：
  - 将私钥与项目代码一起版本控制；
  - 缺少对 `*.pem`/`BEGIN PRIVATE KEY` 的提交门禁。
- 修复：
  - 最小修复（立即）：
    - 立刻删除仓库中的私钥文件并轮换相关证书/密钥（假设已泄露）。
    - `.gitignore` 增加 `nginx/local/ssl/*.pem` 等。
  - 结构性修复（中期）：
    - 证书与私钥改为运行时挂载（secret/volume），不进入镜像层与仓库。
  - 长期治理：
    - secret scanning 覆盖 PEM/PKCS#8 关键字。
- 验证：
  - 仓库：确保不存在 `BEGIN PRIVATE KEY` 命中（`rg -n "BEGIN (RSA )?PRIVATE KEY" -S .`）
  - 部署：确认 TLS 证书/密钥来自 secret 挂载而非镜像层。

---

#### 3) 低权限用户可读取全量日志 + 日志中包含明文密码/密钥（可直接接管系统）

- 证据：
  - 日志检索接口仅要求登录（无权限细分）：
    - `app/routes/history/logs.py:281`（`/api/search`）、`app/routes/history/logs.py:420`（`/api/detail/<log_id>`）等
  - 日志导出接口仅要求登录：
    - `app/routes/files.py:540`（`/files/api/log-export`）
  - 登录路由记录 `request.form`（含密码）：
    - `app/routes/auth.py:65`、`app/routes/auth.py:165`（`form_data=dict(request.form)`）
  - 未配置 `PASSWORD_ENCRYPTION_KEY` 时会把生成的密钥写入日志：
    - `app/utils/password_crypto_utils.py:50`（`generated_key`/`env_var` 入日志）
  - 数据库日志 handler 会把事件字典的任意字段落库（未做字段级脱敏）：
    - `app/utils/logging/handlers.py:244`（`for key, value in event_dict.items(): ... context[key] = value`）
- 攻击路径（现实可行的链路）：
  1. 攻击者注册/获取一个低权限账号（或窃取任意普通账号）；
  2. 调用日志接口读取或导出日志：
     - `GET /history/logs/api/search?limit=200`
     - `GET /files/api/log-export?format=json`
  3. 从日志中获取：
     - 其他用户登录时写入的 `password`（明文），实现账号接管；
     - 若存在，获取 `PASSWORD_ENCRYPTION_KEY` 等密钥信息，扩大解密能力；
  4. 用拿到的管理员口令登录，执行高危操作（调度、分区、凭据管理等）。
- 影响：
  - 账号接管（包括管理员）、权限提升；
  - 密钥泄露导致外部数据库凭据体系失效；
  - 日志内容还可能包含外部 DB 连接错误堆栈（进一步暴露网络与系统细节）。
- 根因：
  - 日志权限未按“最小可见性”划分（日志中心/导出接口未限制到 admin/审计员）；
  - 认证链路记录了敏感字段（密码），且日志入库无脱敏机制；
  - 密钥缺失时把生成密钥写入日志，属于“高危回退实现”。
- 修复：
  - 最小修复（立即）：
    1. **立刻收紧日志读取权限**：`/history/logs/*` 与 `/files/api/log-export` 至少加 `@admin_required` 或新增 `audit_log.view` 权限并仅授予管理员。
    2. **移除登录请求的 `form_data` 日志**，或对 `password`/`token`/`secret` 字段做强制脱敏后再记录。
    3. **禁止把生成的 `PASSWORD_ENCRYPTION_KEY` 写入日志**（只记录“缺失”与“需要配置”的告警即可）。
    4. 回滚/清理现有日志中的敏感字段（至少对存量日志进行清理/迁移，避免“修复后仍可导出历史口令”）。
  - 结构性修复（中期）：
    - 在日志管道（`DatabaseLogHandler`）增加字段级 scrubber（统一过滤 `password`、`secret`、`token`、`key`、`Authorization`、Cookie 等）。
    - 给日志查询接口加审计：记录谁在读、读了多少、导出范围。
  - 长期治理：
    - 制定“日志分级与脱敏规范”，并将其写入 ADR/Docs（见第 V 节）。
- 验证：
  - 权限验证：用普通用户访问 `GET /history/logs/api/list` 应返回 403/重定向；
  - 日志脱敏验证：
    - 人为触发一次登录/连接错误后，检查 `UnifiedLog.context` 中不应出现 `password`/`PASSWORD_ENCRYPTION_KEY` 等字段；
  - 回归：管理员仍可使用日志中心排障（但无法看到敏感明文）。

---

### High

#### 4) 会话 Cookie 未设置 Secure（生产环境下可被窃听/降级劫持）

- 证据：`app/__init__.py:179`（`SESSION_COOKIE_SECURE = False` 固定写死）
- 攻击路径：
  1. 用户在非 HTTPS 或被降级到 HTTP 的链路访问站点；
  2. 攻击者在同网段/代理/恶意 Wi-Fi 抓包获取 session cookie；
  3. 复用 cookie 直接接管会话。
- 影响：会话劫持、权限提升（取决于被劫持账号权限）。
- 根因：
  - 安全配置未区分生产/开发环境；`force_https`/环境变量未参与 cookie 安全策略。
- 修复：
  - 最小修复（立即）：
    - 生产环境强制 `SESSION_COOKIE_SECURE=True`，并配合反向代理强制 HTTPS（重定向 + HSTS）。
  - 结构性修复（中期）：
    - 将 cookie 策略纳入 `Settings`，按 `is_production/force_https` 决定。
- 验证：
  - 访问任意页面，检查响应 `Set-Cookie`：应包含 `Secure; HttpOnly; SameSite=Lax/Strict`。

---

#### 5) 生产 Docker Compose 将 Postgres/Redis 端口暴露到宿主机（扩大攻击面）

- 证据：`docker-compose.prod.yml:24`（`"5432:5432"`）、`docker-compose.prod.yml:51`（`"6379:6379"`）
- 攻击路径：
  1. 攻击者扫描到宿主机对外开放的 5432/6379；
  2. 结合弱口令/口令泄露（见 Critical-1）或配置错误实现数据库/缓存接管。
- 影响：数据库/缓存被远程访问、数据泄露与篡改、进一步 RCE（取决于 DB/Redis 使用方式）。
- 根因：默认把内部依赖服务暴露在宿主机网络，而非仅在内部网络可达。
- 修复：
  - 最小修复（立即）：
    - 生产环境移除端口映射或绑定到 `127.0.0.1`，并用防火墙/安全组限制来源。
  - 结构性修复（中期）：
    - 将 DB/Redis 放入专用私网或托管服务；只允许应用容器访问。
- 验证：
  - 外部网络无法连接 5432/6379；容器内部仍可通过 service name 访问。

---

#### 6) 分区管理高危操作仅需 `view` 权限 + 参数缺少边界校验（可触发大范围 DROP）

- 证据：
  - 路由权限：`app/routes/partition.py:582`（`/api/create`）、`app/routes/partition.py:633`（`/api/cleanup`）仅 `@view_required`
  - 清理参数无最小值约束：`app/routes/partition.py:645`（`retention_months` 仅 `int()` 转换）
  - 实际 DROP 逻辑：`app/services/partition_management_service.py:326`（`cleanup_old_partitions`），`app/services/partition_management_service.py:357`（`retention_months * 31` 直接参与 cutoff 计算）
- 攻击路径：
  1. 普通用户（具备 `view`）调用：
     - `POST /partition/api/cleanup`，传入 `{"retention_months": -1}` 或极小值；
  2. 服务计算 `cutoff_date` 为未来日期，筛出大量分区并执行 `DROP TABLE`。
- 影响：
  - 大规模数据丢失（历史分区被删除）、业务不可用；
  - 误操作难回滚（若无备份/审计/审批流程）。
- 根因：
  - 将“危险写操作”错误归类为只读权限；
  - 缺少输入边界与二次确认/审批（尤其是 cleanup）。
- 修复：
  - 最小修复（立即）：
    - `/partition/api/create`、`/partition/api/cleanup` 改为 `@update_required` 或单独的 `partition.manage` 权限；
    - 对 `retention_months` 加最小/最大边界（例如 `1 <= retention_months <= 36`），并对极端值直接拒绝；
    - cleanup 增加“dry-run 预览 + 二次确认”（至少返回将删除列表与数量，需要显式确认参数）。
  - 结构性修复（中期）：
    - 为分区操作引入审批/审计（记录操作者、删除范围、工单号）。
- 验证：
  - 普通用户访问上述接口应 403；
  - 传入 `retention_months=-1/0/999` 应返回 400 且不会执行 DROP；
  - 管理员在确认流程后仍可正常清理。

---

#### 7) 连接测试接口回显底层异常（潜在泄露连接串/用户名/网络信息），且可被滥用做内网探测

- 证据：
  - 对外返回原始异常：`app/services/connection_adapters/connection_test_service.py:164`（`message = f"连接失败: {error_message}"`）
  - 批量测试将异常拼进响应：`app/routes/connections.py:302`（`"测试失败: {exc!s}"`）
  - 连接测试支持自定义 host/port：`app/routes/connections.py:123`（`/api/test` 新连接模式）
- 攻击路径：
  1. 低权限用户调用 `/connections/api/test`，提交任意内网 IP/端口；
  2. 根据响应耗时与错误回显，推断内网端口开放情况（横向扫描）；
  3. 若底层驱动异常包含 DSN/用户名等，直接泄露更多敏感信息。
- 影响：
  - 内网资产探测、辅助横向移动；
  - 敏感信息泄露（host/user/连接串片段/驱动堆栈）。
- 根因：
  - 将诊断信息直接返回给客户端，而不是“对外最小化 + 内部日志保留”；
  - 外部连接能力缺少强授权与速率限制（尤其是新连接模式）。
- 修复：
  - 最小修复（立即）：
    - 对外错误消息改为固定文案（例如“连接失败，请检查网络/凭据/白名单”），把 `error_message` 仅写入受控日志；
    - 新连接模式（自定义 host/port）至少要求管理员权限或额外权限（`connection.test`）；
    - 给 `/connections/api/test`、`/connections/api/batch-test` 增加速率限制与审计。
  - 结构性修复（中期）：
    - 增加允许连接的网段/域名白名单（阻断对 `127.0.0.1`、metadata 网段、内网关键地址的探测）。
- 验证：
  - 触发连接失败时，客户端响应不包含驱动原始异常文本；
  - 低权限用户无法对任意 host/port 发起测试；
  - 日志中仍保留必要诊断信息（且脱敏）。

---

### Medium

#### 8) 登录 `next` 参数未校验，存在开放重定向（Open Redirect）

- 证据：`app/routes/auth.py:206`（`next_page = request.args.get("next")`）、`app/routes/auth.py:207`（`redirect(next_page)`）
- 攻击路径：
  1. 攻击者构造链接：`/auth/login?next=https://attacker.example/phish`
  2. 受害者登录成功后被重定向到攻击者站点，易被二次钓鱼或诱导下载。
- 影响：钓鱼与社工成功率提升；在部分场景可配合 OAuth/SSO 流量劫持（若未来接入）。
- 根因：未对 `next` 做“同源/相对路径”校验。
- 修复：
  - 最小修复（立即）：只允许站内相对路径（例如以 `/` 开头且不包含 `//`），否则忽略并跳转到默认首页。
  - 长期治理：统一封装安全的 `safe_redirect(next_url)` helper。
- 验证：
  - `next=https://...` 不再跳转到外站；
  - `next=/dashboard/` 仍可正常跳转。

---

#### 9) CSV 导出缺少公式注入（CSV Injection）防护

- 证据：
  - `app/routes/files.py:198`（`writer.writerow([... username_display, instance.name, ...])`）
  - `app/routes/files.py:430`（实例导出字段直接写入）
- 攻击路径：
  1. 攻击者将可控字段（如实例名/标签/描述/用户名等）写成 `=HYPERLINK("https://...","click")`、`@SUM(...)` 等；
  2. 管理员导出 CSV 并用 Excel 打开时触发公式执行（取决于客户端策略）。
- 影响：客户端侧数据外带、钓鱼跳转、在特定环境下进一步代码执行（取决于 Office 安全策略）。
- 根因：导出前未对单元格做“公式前缀”规避。
- 修复：
  - 最小修复（立即）：对导出字段做防护：若以 `= + - @` 开头，则前置 `'` 或空格（同时保留可读性）。
  - 长期治理：导出模块统一做 `sanitize_csv_cell()`，并加单元测试。
- 验证：
  - 构造含 `=...` 的实例名导出后，CSV 单元格应被转义（Excel 打开不再作为公式执行）。

---

#### 10) 详细健康检查接口对公网暴露过多系统信息（有利于侦察）

- 证据：
  - `app/routes/health.py:59`（`/health/api/detailed` 无认证，返回数据库/缓存/系统资源详细信息）
  - `app/routes/health.py:120`（`/health/api/health` 无认证，返回 DB/Redis 状态与 uptime）
- 攻击路径：匿名请求健康接口即可获取内部组件状态、资源使用率、版本信息等。
- 影响：辅助攻击者选择攻击窗口、判断依赖拓扑与可用性；为 DoS/爆破提供决策信息。
- 根因：健康接口未区分“外部探活”与“内部诊断”两类需求。
- 修复：
  - 最小修复（立即）：
    - `/api/detailed` 改为仅内网或需管理员；
    - 对外探活接口仅返回最小字段（例如 `status` + `timestamp`）。
  - 结构性修复（中期）：引入监控专用 token/白名单来源校验。
- 验证：公网访问 `/health/api/detailed` 不再返回详细组件信息。

---

#### 11) 缺失关键安全响应头（CSP/HSTS/Clickjacking 等）

- 证据：代码中未发现统一设置 `Content-Security-Policy` / `Strict-Transport-Security` / `X-Frame-Options` 等响应头（仅常量定义：`app/constants/http_headers.py`）
- 攻击路径：点击劫持（iframe 嵌入）、弱 CSP 导致 XSS 防护缺失、HTTPS 降级风险（无 HSTS）。
- 影响：前端安全基线薄弱，放大其他漏洞的可利用性。
- 根因：缺少统一的 `after_request` 安全头策略（或 Nginx 层未配置）。
- 修复：
  - 最小修复（立即）：在 Nginx 或 Flask `after_request` 添加安全头（优先从 Nginx 实施）：
    - `X-Frame-Options: DENY` 或 CSP `frame-ancestors 'none'`
    - `X-Content-Type-Options: nosniff`
    - `Referrer-Policy: same-origin`（按业务调整）
    - `Strict-Transport-Security`（仅 HTTPS 站点）
    - CSP（从 report-only 开始逐步收紧）
- 验证：`curl -I` 检查头存在且符合预期。

---

#### 12) 依赖存在已知 CVE（需升级）

- 证据：
  - `requirements-prod.txt:17`（`filelock==3.19.1`）
  - `requirements-prod.txt:66`（`urllib3==2.5.0`）
  - `requirements-prod.txt:70`（`werkzeug==3.1.3`）
  - 安全扫描结果（本地运行）：`uv tool run pip-audit -r requirements-prod.txt --disable-pip --no-deps --skip-editable`
    - `filelock 3.19.1`：CVE-2025-68146（修复版本 `3.20.1`）
    - `urllib3 2.5.0`：CVE-2025-66418 / CVE-2025-66471（修复版本 `2.6.0`）
    - `werkzeug 3.1.3`：CVE-2025-66221（修复版本 `3.1.4`）
- 影响：取决于具体漏洞细节与调用路径，通常属于供应链风险与潜在 RCE/信息泄露入口（需按 CVE 细节评估）。
- 根因：生产依赖未及时跟进安全更新；缺少持续 CVE 门禁。
- 修复：
  - 最小修复（立即）：升级上述包到修复版本，并更新 `uv.lock/requirements`。
  - 长期治理：在 CI 增加 `pip-audit`/OSV 扫描与每月依赖更新节奏。
- 验证：升级后重新运行 `pip-audit` 应 0 命中。

---

### Low

#### 13) Logout 允许 GET，存在“登出 CSRF”（可被跨站触发）

- 证据：
  - `app/routes/auth.py:262`（`/auth/api/logout` 支持 `GET`）
  - `app/utils/decorators.py:310`（`GET` 属于 `SAFE_CSRF_METHODS`，CSRF 校验直接跳过）
- 攻击路径：攻击者在第三方站点放置 `<img src="https://target/auth/api/logout">` 即可让已登录用户被动登出。
- 影响：可用性/体验层面的骚扰（一般不导致数据泄露，但会造成会话中断）。
- 根因：将状态变更操作暴露为 GET 且未强制 CSRF。
- 修复：
  - 最小修复：移除 GET，仅允许 POST；或 GET 也强制 CSRF（不推荐）。
- 验证：GET 请求不再触发登出。

---

### D. 修复路线图（<= 8 条行动项，按“高收益/低风险”优先）

1. 立即移除仓库中的所有敏感信息（`env.production`、`nginx/local/ssl/key.pem` 等），并完成生产密钥/口令轮换 + Git 历史清理。
2. 立刻收紧日志读取与导出权限（至少 admin），并清理/脱敏现有日志中的密码与密钥字段。
3. 修复认证链路日志：禁止记录 `request.form` 原始数据；在日志管道增加统一 scrubber（password/token/secret/key/cookie/authorization）。
4. 生产环境启用 `SESSION_COOKIE_SECURE=True` + HTTPS 强制（HSTS），并补齐基础安全响应头（优先 Nginx 层）。
5. 分区管理接口改为 `partition.manage`/`update_required`，并对 `retention_months` 加边界校验 + dry-run/二次确认。
6. 连接测试接口对外错误信息最小化，新增授权/限流/白名单，防止内网探测与敏感信息回显。
7. 导出 CSV 增加公式注入防护；日志导出限制格式与最大条数，避免 DoS。
8. 依赖升级与 CVE 门禁：升级 `filelock/urllib3/werkzeug` 到修复版本并将 `pip-audit` 纳入 CI。

---

## IV. 防御/兼容/回退/适配逻辑中的安全风险点（重点关注 or/||/兜底）

> 这些点往往“为了好用/兼容”引入隐性风险，建议通过显式分支 + 监控命中率 + 逐步清理旧路径来治理。

1) 位置：`app/settings.py:133` / `app/settings.py:152`  
   - 类型：回退  
   - 描述：`FLASK_ENV` 未正确设置时会进入 debug 默认值路径，并允许随机生成 `SECRET_KEY/JWT_SECRET_KEY`（开发友好但生产误配风险高）。  
   - 建议：生产启动前增加“硬门禁”（例如检测容器/ENV 标识），避免因环境变量缺失导致进入开发回退。

2) 位置：`app/utils/password_crypto_utils.py:50`  
   - 类型：回退  
   - 描述：未设置 `PASSWORD_ENCRYPTION_KEY` 时生成临时密钥，并把密钥与导出命令写入日志（等价于泄露主密钥）。  
   - 建议：仅记录“缺失”告警，不记录密钥本身；生产环境强制缺失即失败（当前 `Settings._validate` 已有，但仍应避免日志泄露与非生产误用）。

3) 位置：`app/__init__.py:179`  
   - 类型：兼容/回退  
   - 描述：`SESSION_COOKIE_SECURE` 固定为 False，可能是为本地 HTTP 兼容，但生产会话安全直接降级。  
   - 建议：改为按 `settings.force_https/settings.is_production` 决定；若必须兼容 HTTP，仅在 development 显式允许。

4) 位置：`app/routes/files.py:220`  
   - 类型：防御缺失（参数兜底）  
   - 描述：日志导出 `limit` 仅做默认值兜底，无最大值限制，容易被滥用造成 DB/内存压力。  
   - 建议：设置上限（例如 5000），并对导出增加分页或异步任务。

5) 位置：`app/routes/accounts/sync.py:113`  
   - 类型：回退  
   - 描述：`is_success = bool(normalized.pop("success", True))` 默认把缺失 `success` 的结果视为成功，可能掩盖失败并误导审计/监控。  
   - 建议：默认应为 False；并在缺失字段时记录告警以定位返回 schema 漂移。

---

## V. 安全规范缺口清单（建议写成文档/ADR）

1) **密钥与配置管理规范**  
   - 生产密钥/口令禁止入库；示例配置文件必须为占位符；必须配合 secret scanning 与密钥轮换流程（含 Git 历史清理指引）。

2) **日志分级与脱敏规范**  
   - 禁止记录密码/令牌/密钥/连接串/PII；定义“可对外展示字段”和“仅内部可见字段”；日志查询与导出必须最小授权并审计。

3) **鉴权/授权统一入口与权限矩阵**  
   - 明确角色与权限点（view/create/update/delete + 域权限如 `partition.manage`、`audit_log.view`、`connection.test`）；高危操作强制 admin 或专用权限。

4) **错误返回与信息泄露控制**  
   - 客户端错误消息最小化；底层异常只入受控日志；禁止把驱动异常/连接串回显给前端。

5) **CSRF/CORS 策略**  
   - JSON API 的 CSRF 约束、跨域 Origin 白名单策略、`supports_credentials` 使用边界；禁止对高危接口开放跨域。

6) **浏览器安全基线**  
   - 必须设置 CSP（分阶段）、HSTS（HTTPS 环境）、点击劫持防护（frame-ancestors）、nosniff 等。

7) **导入导出安全规范**  
   - CSV 公式注入防护；导出权限控制；导出量/速率限制；导入文件大小/编码/异常路径处理规范。

8) **依赖与供应链治理**  
   - 锁定版本与哈希；定期 CVE 扫描；升级节奏与回归策略；镜像构建链路的来源可信与最小化。
