# 项目级审计报告（2025-12-05）

## 范围与方法
- 依据《项目级审计作业手册》，对配置、安全、依赖与初始化流程进行快速走查。
- 采用静态阅读与命名脚本参考，未运行自动化测试/压测（时间受限）。

## 发现与分级

| ID | 级别 | 描述 | 证据 | 解决建议 |
| --- | --- | --- | --- | --- |
| SEC-01 | P0 | 配置导入阶段强制要求 `DATABASE_URL` 与 `CACHE_REDIS_URL`，未设置时直接抛 `ValueError`，与 `create_app` 的 SQLite/本地 Redis 默认策略冲突，导致本地/CI 无法启动。 | `app/config.py:75-84` | 将强制校验改为惰性检查或提供与 `create_app` 一致的安全默认值（如开发/CI 使用 SQLite、本地 Redis），并在生产环境通过环境开关强制校验。 |
| SEC-02 | P1 | `configure_session_security` 将 `SESSION_COOKIE_SECURE` 固定为 `False`，生产环境仍允许 HTTP 传输会话 Cookie，存在劫持风险。 | `app/__init__.py:270-278` | 依据环境切换：生产/`FORCE_HTTPS=true` 时设为 `True`，开发环境可保持 `False`；同步更新文档与默认 `.env` 示例。 |
| SEC-03 | P1 | JWT 过期配置使用整数秒而非 `timedelta`，与 Config 类期望不一致，可能导致过期时间被误解或失效。 | `app/__init__.py:163-167` | 将 `JWT_ACCESS_TOKEN_EXPIRES`、`JWT_REFRESH_TOKEN_EXPIRES` 设为 `timedelta(seconds=...)`，并确保环境变量解析为 int 后转换。 |
| SEC-04 | P2 | `csrf.init_app(app)` 重复调用两次，增加调试复杂度，潜在副作用不明。 | `app/__init__.py:303` 与 `app/__init__.py:336` | 保留一次初始化即可，建议在 `initialize_extensions` 中保留，移除后续重复调用。 |
| DEP-01 | P2 | 依赖同时声明 `psycopg[binary]` 与 `psycopg2-binary`，存在重复驱动与潜在冲突。 | `pyproject.toml:29` 与 `pyproject.toml:41` | 仅保留一种（建议保留新版 `psycopg[binary]`），删除 `psycopg2-binary`，并验证数据库连接。 |

## 下一步建议
- 按级别优先处理：先落地 SEC-01/02/03（P0/P1），再清理 SEC-04 与 DEP-01。
- 修复后运行 `make test`、`make quality`、`./scripts/refactor_naming.sh --dry-run`，并在 PR 描述记录验证步骤。
- 若修复涉及配置策略，需同步更新 `README`/`env.*` 示例与运维文档。

> 注：本次为快速走查，建议后续补充自动化扫描（bandit、pip-audit、pytest --cov）以完善覆盖。
