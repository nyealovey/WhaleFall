# 配置与密钥（Settings/.env/env.example）

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：配置读取（`app/settings.py`）、环境变量（`.env`/`env.example`）、部署注入与密钥管理

## 目的

- 把配置读取、默认值与校验收敛到单一入口（Settings），避免业务代码散落 `os.environ.get(...)`。
- 明确“哪些变量是密钥/敏感信息”，并通过门禁避免提交到仓库。

## 适用范围

- 应用配置：`app/settings.py`、`app/__init__.py`、部署脚本与 `docker-compose*.yml`。
- 环境文件：`.env`（未跟踪）、`env.example`（示例模板）。
- 所有会把配置写入日志/错误响应/审计记录的代码路径。

## 规则（MUST/SHOULD/MAY）

### 1) 单一真源（Settings）

- MUST：新增/修改配置项必须落在 `app/settings.py` 的 `Settings`（解析 + 默认值 + 校验）。
- MUST NOT：在业务模块中新增 `os.environ.get(...)` 读取配置（除非属于“密钥读取工具”的封装层，且在本文件明确记录）。
- SHOULD：`app/config.py` 为兼容层（已弃用），新代码不得依赖。

### 2) `.env` 与 `env.example`

- MUST：真实密钥只允许存在于未跟踪的 `.env` 或部署系统注入，禁止提交到仓库。
- MUST：`env.example` 仅作为模板示例，敏感项必须留空（或使用明确占位符且不含真实值）。
- SHOULD：新增配置项时同步更新：
  - `env.example`
  - `docker-compose.prod.yml`（如生产容器需要）
  - 相关文档（如 `docs/reference`）

### 3) 生产环境关键密钥（必须具备）

生产环境（`FLASK_ENV=production`）必须设置且保持稳定的典型密钥：

- MUST：`SECRET_KEY`（会话签名）
- MUST：`JWT_SECRET_KEY`（JWT 签名）
- MUST：`PASSWORD_ENCRYPTION_KEY`（用于数据库凭据加/解密；缺失会导致重启后无法解密已存储凭据）
- MUST：数据库与 Redis 口令（例如 `POSTGRES_PASSWORD`、`REDIS_PASSWORD`）

### 4) 日志与错误响应中的敏感信息

- MUST NOT：把密钥/口令/令牌/连接串原文写入日志、错误响应或审计记录。
- SHOULD：若必须排障，可记录“变量名/是否存在/长度/来源”等非敏感信息。

## 正反例

### 正例：新增配置项的推荐流程

1. 在 `app/settings.py` 增加字段与解析/校验（并定义默认值）。
2. 更新 `env.example` 增加说明与示例占位符。
3. 如影响部署，更新 `docker-compose.prod.yml` 或部署脚本。
4. 增加/更新 `docs/reference`（如果属于对外可见配置）。

### 反例：业务代码直接读取环境变量

```python
timeout = int(os.environ.get("SOME_TIMEOUT", "30"))
```

## 门禁/检查方式

- `env.example` 密钥门禁：`./scripts/ci/secrets-guard.sh`
- 环境变量完整性检查（可选）：`./scripts/setup/validate-env.sh`

## 变更历史

- 2025-12-25：新增标准文档，统一 Settings 单一真源与 `env.example` 密钥门禁策略。
