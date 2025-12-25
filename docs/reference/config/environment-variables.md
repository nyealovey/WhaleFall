# WhaleFall 环境变量（必填/可选/默认值）说明

> 更新时间：2025-12-19  
> 目标：把“哪些环境变量必须配置、哪些可选、默认值是什么”讲清楚，统一以 `app/settings.py` 为准，减少理解成本。  
> 说明：本文件按**当前代码的读取方式**整理；其中少数项目前存在“重复变量名/策略冲突”，已在备注中明确并给出推荐统一口径。

## 1. 总体规则（你需要先知道的）

- WhaleFall 会在 `Settings.load()` 时调用 `python-dotenv` 的 `load_dotenv()`（`create_app()` 默认会调用 `Settings.load()`），因此本地开发通常用根目录 `.env` 配置环境变量（`.env` 已被 `.gitignore` 忽略，避免泄露）。
- 建议将生产环境变量通过容器编排/K8s Secret/CI 注入，不要把真实密钥写进仓库。

## 2. 生产环境“最小必填集”（建议口径）

> 下面这些不配齐，会导致应用无法启动或核心能力不可用（尤其是凭据解密）。

| 环境变量 | 是否必填（生产） | 默认值 | 说明 |
|---|---:|---|---|
| `SECRET_KEY` | 是 | 无（开发模式缺失会随机生成） | Flask 会话签名密钥。生产必须固定。 |
| `JWT_SECRET_KEY` | 是 | 无（开发模式缺失会随机生成） | JWT 签名密钥。生产必须固定。 |
| `PASSWORD_ENCRYPTION_KEY` | 是 | 无（开发环境缺失会生成“临时密钥”） | **用于加/解密数据库凭据**。生产不设置会导致重启后无法解密已存储密码。 |
| `DATABASE_URL` | 是 | 无（非 production 环境会回退 SQLite） | 主数据库连接串。生产建议使用 PostgreSQL。 |
| `CACHE_REDIS_URL` | 条件必填 | `redis://localhost:6379/0`（仅当 `CACHE_TYPE=redis` 且非 production 时回退） | 当缓存选择 Redis 时必填；否则不会使用。 |

> 备注：`env.example` 提供了该变量的占位，但生产环境请用安全方式生成/存储并通过部署系统注入。

## 3. 应用启动与运行参数（Web/WSGI）

| 环境变量 | 是否必填（生产） | 是否必填（开发） | 默认值 | 说明 |
|---|---:|---:|---|---|
| `FLASK_ENV` | 建议 | 否 | `development`（`app.py`/`wsgi.py` 会 setdefault） | 影响 debug 行为与部分配置分支。推荐生产设置为 `production`。 |
| `FLASK_DEBUG` | 否 | 否 | `true`（仅 `app.py` 默认） | `app.py` 的开发服务器 debug 开关。 |
| `FLASK_HOST` | 否 | 否 | `127.0.0.1` | 绑定地址（`app.py`/`wsgi.py`）。 |
| `FLASK_PORT` | 否 | 否 | `5001` | 绑定端口（`app.py`/`wsgi.py`）。 |

## 4. 安全与认证

| 环境变量 | 是否必填（生产） | 默认值 | 说明 |
|---|---:|---|---|
| `SECRET_KEY` | 是 | 无（开发缺失会随机生成） | Flask session/cookie 签名。 |
| `JWT_SECRET_KEY` | 是 | 无（开发缺失会随机生成） | JWT token 签名。 |
| `JWT_ACCESS_TOKEN_EXPIRES` | 否 | `3600`（秒） | 访问令牌过期时间（秒）。 |
| `JWT_REFRESH_TOKEN_EXPIRES` | 否 | `2592000`（秒） | 刷新令牌过期时间（秒）。 |
| `JWT_REFRESH_TOKEN_EXPIRES_SECONDS` | 否（不推荐使用） | `2592000`（秒） | **变量名存在重复**：`Settings` 优先读 `JWT_REFRESH_TOKEN_EXPIRES`，其次读 `JWT_REFRESH_TOKEN_EXPIRES_SECONDS`。建议统一保留一个。 |
| `BCRYPT_LOG_ROUNDS` | 否 | `12` | 密码哈希 cost（越大越慢更安全）。 |
| `LOGIN_RATE_LIMIT` | 否 | `10` | 登录限流：窗口内允许次数。 |
| `LOGIN_RATE_WINDOW` | 否 | `60`（秒） | 登录限流：窗口大小（秒）。 |
| `FORCE_HTTPS` | 否 | `false` | 为 `true` 时偏好 `https` scheme（配合反向代理头）。 |
| `CORS_ORIGINS` | 否 | `http://localhost:5001,http://127.0.0.1:5001` | 允许跨域源列表（逗号分隔）。仅在你真的跨域部署前端时需要重点配置。 |
| `PERMANENT_SESSION_LIFETIME` | 否 | `3600`（秒） | Flask-Login 记住我/会话相关超时。 |

## 5. 主数据库与连接池

| 环境变量 | 是否必填（生产） | 默认值 | 说明 |
|---|---:|---|---|
| `DATABASE_URL` | 是（production 必填） | `sqlite:///userdata/whalefall_dev.db`（非 production 环境回退） | SQLAlchemy 连接串。生产建议 Postgres；开发可回退 SQLite。 |
| `DB_CONNECTION_TIMEOUT` | 否 | `30`（秒） | 连接池等待超时。 |
| `DB_MAX_CONNECTIONS` | 否 | `20` | 连接池大小。 |
| `DATABASE_SIZE_RETENTION_MONTHS` | 否 | `12`（月） | 容量统计保留月份。 |

## 6. 缓存（Flask-Caching + 业务缓存 TTL）

| 环境变量 | 是否必填（生产） | 默认值 | 说明 |
|---|---:|---|---|
| `CACHE_TYPE` | 否（建议生产用 `redis`） | `simple` | 可选：`simple` / `redis`。 |
| `CACHE_REDIS_URL` | 条件必填 | `redis://localhost:6379/0`（当 `CACHE_TYPE=redis` 时） | Redis 连接串。 |
| `CACHE_DEFAULT_TIMEOUT` | 否 | `300`（秒） | Flask-Caching 默认超时。 |
| `CACHE_DEFAULT_TTL` | 否 | `604800`（7 天） | 业务缓存默认 TTL（见 `cache_service`）。 |
| `CACHE_RULE_EVALUATION_TTL` | 否 | `86400`（1 天） | 规则评估缓存 TTL。 |
| `CACHE_RULE_TTL` | 否 | `7200`（2 小时） | 规则缓存 TTL。 |
| `CACHE_ACCOUNT_TTL` | 否 | `3600`（1 小时） | 账户相关缓存 TTL。 |

## 7. 文件上传

| 环境变量 | 是否必填（生产） | 默认值 | 说明 |
|---|---:|---|---|
| `UPLOAD_FOLDER` | 否 | `userdata/uploads` | 上传目录。 |
| `MAX_CONTENT_LENGTH` | 否 | `16777216`（16MB） | Flask 请求体大小上限。 |

## 8. 调度器（APScheduler）

| 环境变量 | 是否必填（生产） | 默认值 | 说明 |
|---|---:|---|---|
| `ENABLE_SCHEDULER` | 否 | `true` | 是否启动内置调度器。若你计划“Web 与 Scheduler 分进程”，建议在 Web 进程设为 `false`。 |

## 9. 外部数据库适配器默认连接参数（用于连接测试/同步）

> 这些通常不是“必填”，更像是“默认值”；真正连接时通常依赖实例/凭据配置。

| 环境变量 | 是否必填（生产） | 默认值 | 说明 |
|---|---:|---|---|
| `SQL_SERVER_HOST` | 否 | `localhost` | SQL Server 默认 host。 |
| `SQL_SERVER_PORT` | 否 | `1433` | SQL Server 默认端口。 |
| `SQL_SERVER_USERNAME` | 否 | `sa` | SQL Server 默认用户名。 |
| `SQL_SERVER_PASSWORD` | 否 | 空字符串 | SQL Server 默认密码。 |
| `MYSQL_HOST` | 否 | `localhost` | MySQL 默认 host。 |
| `MYSQL_PORT` | 否 | `3306` | MySQL 默认端口。 |
| `MYSQL_USERNAME` | 否 | `root` | MySQL 默认用户名。 |
| `MYSQL_PASSWORD` | 否 | 空字符串 | MySQL 默认密码。 |
| `ORACLE_HOST` | 否 | `localhost` | Oracle 默认 host。 |
| `ORACLE_PORT` | 否 | `1521` | Oracle 默认端口。 |
| `ORACLE_SERVICE_NAME` | 否 | `ORCL` | Oracle 默认服务名。 |
| `ORACLE_USERNAME` | 否 | `system` | Oracle 默认用户名。 |
| `ORACLE_PASSWORD` | 否 | 空字符串 | Oracle 默认密码。 |

### 9.1 Oracle 客户端库定位（可选）

| 环境变量 | 是否必填 | 默认值 | 说明 |
|---|---:|---|---|
| `ORACLE_CLIENT_LIB_DIR` | 否 | 空 | 显式指定 Oracle client `lib` 目录。 |
| `ORACLE_HOME` | 否 | 空 | 指定 Oracle 安装目录，代码会尝试 `${ORACLE_HOME}/lib`。 |
| `DYLD_LIBRARY_PATH` | 否 | 空 | macOS 下动态库路径；应用会在可用时尝试注入（仅用于兼容）。 |

## 10. 功能开关

| 环境变量 | 是否必填（生产） | 默认值 | 说明 |
|---|---:|---|---|
| `COLLECT_DB_SIZE_ENABLED` | 否 | `true` | 是否启用容量采集任务。 |
| `AGGREGATION_ENABLED` | 否 | `true` | 是否启用聚合统计任务。 |

## 11. 仅脚本/内部占位使用（可忽略但建议了解）

| 环境变量 | 是否必填 | 默认值 | 说明 |
|---|---:|---|---|
| `DEFAULT_ADMIN_PASSWORD` | 否 | 空 | `scripts/admin/password/show_admin_password.py` 会优先显示该值（避免只能看到哈希）。 |
| `WHF_PLACEHOLDER_CREDENTIAL_SECRET` | 否 | 随机生成 | 凭据表单服务创建空实例时使用的“占位密码”，避免硬编码。 |

## 12. Docker/部署脚本常见变量（与应用变量不同层）

> 这些通常由 `docker-compose*.yml`、部署脚本消费，用于拼接 `DATABASE_URL` / `CACHE_REDIS_URL` 等应用变量。

| 环境变量 | 典型用途 |
|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Postgres 容器初始化 + 拼接 `DATABASE_URL` |
| `REDIS_PASSWORD` | Redis 容器密码 + 拼接 `CACHE_REDIS_URL` |
| `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` | 容器/构建阶段网络代理 |
