---
title: 数据库驱动与连接方式
aliases:
  - database-drivers
tags:
  - reference
  - reference/database
status: active
created: 2025-09-07
updated: 2025-12-26
owner: WhaleFall Team
scope: 主数据库(SQLAlchemy)与外部实例连接(连接测试/同步)
related:
  - "[[reference/database/README|数据库参考]]"
  - "[[reference/config/environment-variables]]"
  - "[[reference/database/database-permissions-overview]]"
---

# 数据库驱动与连接方式

> [!info] Purpose
> 说明主数据库(`DATABASE_URL`)与外部实例连接(`db_type`)使用的驱动, 适配器入口与默认行为.

> [!info] SSOT
> - 主库配置: [[reference/config/environment-variables]] 与 `app/settings.py`.
> - 外部实例适配器: `app/services/connection_adapters/connection_factory.py` + `app/services/connection_adapters/adapters/**`.

## 主数据库(WhaleFall 自身)

| 场景 | 入口 | 驱动/依赖 | 默认值/示例 | 备注 |
| --- | --- | --- | --- | --- |
| 主库(SQLAlchemy) | `DATABASE_URL` | PostgreSQL: `psycopg[binary]`; 开发回退 SQLite(内置) | `postgresql+psycopg://...` | production 必填; 非 production 缺失会回退到 `<project_root>/userdata/whalefall_dev.db`(见 `app/settings.py`) |

## 外部实例(连接测试/同步)

| db_type | 连接适配器 | Python 包(来自 `pyproject.toml`) | 说明 |
| --- | --- | --- | --- |
| `mysql` | `app/services/connection_adapters/adapters/mysql_adapter.py` | `pymysql>=1.1.2` | `connect_timeout=20s`, `read/write_timeout=300s`; 未提供 `database_name` 时使用默认 schema |
| `postgresql` | `app/services/connection_adapters/adapters/postgresql_adapter.py` | `psycopg[binary]>=3.2.10` | `connect_timeout=20s`; 使用 `statement_timeout=300000ms`; 未提供 `database_name` 时回退 `postgres` |
| `sqlserver` | `app/services/connection_adapters/adapters/sqlserver_adapter.py` | `pymssql>=2.3.7` | 当前仅支持 `pymssql`; `login_timeout=20s`, `timeout=300s`; 未提供 `database_name` 时回退 `master` |
| `oracle` | `app/services/connection_adapters/adapters/oracle_adapter.py` | `oracledb>=3.3.0` | 支持 thin/thick; 未提供 `database_name` 时回退 `ORCL`; 客户端库定位见下文 |

> [!note]
> 仓库依赖中包含 `pyodbc>=5.2.0`, 但当前连接适配器未使用(SQL Server 以 `pymssql` 为准).

## 默认值与约束

- 支持的 `db_type` 值由 `app/services/connection_adapters/connection_factory.py` 固化(目前: `mysql/postgresql/sqlserver/oracle`).
- 外部实例的默认 schema/database 名称优先从 `DatabaseTypeConfig.default_schema` 获取(`app/services/connection_adapters/adapters/base.py::get_default_schema`); 部分适配器在缺失时再做硬回退(见上表).
- Oracle 客户端初始化(thick mode)会按顺序尝试以下路径(命中一个即可):
  1. `ORACLE_CLIENT_LIB_DIR`
  2. `${ORACLE_HOME}/lib`
  3. `app/services/oracle_client/lib`(如仓库内提供)
- macOS 本地开发的动态库路径: 应用不会在运行时修改 `DYLD_LIBRARY_PATH`; 如需 Oracle thick mode 客户端库, 请在启动前配置(优先 `ORACLE_CLIENT_LIB_DIR`/`ORACLE_HOME`).

## 示例

### 主库连接串示例(PostgreSQL + psycopg3)

```bash
DATABASE_URL=postgresql+psycopg://user:password@host:5432/whalefall
```

### 外部实例连通性验证

- UI/接口入口: `/connections/api/test`(需要登录与 CSRF; 具体请求字段见路由实现 `app/routes/connections.py`).
- 推荐先通过连接测试确保驱动/网络/凭据可用, 再启用账户同步与容量采集.

## 版本/兼容性说明

- Oracle thin/thick 的差异主要体现在客户端库依赖与特性可用性; 当前适配器会在非 thin 模式下尝试初始化客户端库, 并对 "已初始化" 场景做防御性处理.
- SQL Server 目前以 `pymssql` 为唯一实现; 如未来切换到 `pyodbc`, 需要补充驱动选择与回滚策略, 并同步更新本文件与权限脚本.

## 常见错误

- 启动时报缺少驱动(`ModuleNotFoundError`): 按仓库约定安装依赖(`make install`/`uv sync`), 并确认虚拟环境生效.
- SQL Server 在 macOS 上连接失败或驱动报错: 优先确认 FreeTDS/系统依赖是否齐备; 必要时使用 Docker/容器环境规避本机构建差异.
- Oracle 报 `DPI-1047`/客户端库找不到: 优先设置 `ORACLE_CLIENT_LIB_DIR` 或 `ORACLE_HOME`, 并确认目录存在且包含 `libclntsh` 等必要库文件.
