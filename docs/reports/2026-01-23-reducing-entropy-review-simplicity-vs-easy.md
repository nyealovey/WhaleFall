> **Status**: Draft
> **Owner**: Codex（reducing-entropy）
> **Created**: 2026-01-23
> **Updated**: 2026-01-23
> **Mindset**: Simplicity vs Easy（简单 vs 熟悉）
> **Success Metric**: 用“删入口/删路径/删依赖”降低概念数量与总代码量（不是“更强的工程化”）
> **Scope**: `/Users/apple/Github/WhaleFall`（构建/运行/部署/依赖/工具链）

# reducing-entropy 审查报告：Simplicity vs Easy (2026-01-23)

## 1. 核心原则（本报告的判定标准）

- **Simple（简单）**：概念不纠缠、路径少、边界清晰（客观）
- **Easy（熟悉）**：因为习惯/方便而引入的额外工具链与路径（主观）

“easy 的多路径”几乎总会带来熵：更多脚本、更多配置、更多故障面、更多人肉知识。

本报告只关注：哪些“并行路径”应该被删掉以换取净减。

## 2. 发现与删减建议（按收益排序）

### 2.1 P0：多套运行入口并行（Makefile + 多 compose + 独立脚本）

复杂度来源（证据）：

- Makefile 体系并行：`Makefile:1`、`Makefile.dev:1`、`Makefile.prod:1`、`Makefile.flask:1`
- compose 并行：`docker-compose.dev.yml:1`、`docker-compose.prod.yml:1`、`docker-compose.flask-only.yml:1`
- 独立启动脚本：`start_uv.sh:1`

可删/可合并的最小路径（推荐）：

- 只保留两条主路径：
  - dev：`Makefile.dev` + `docker-compose.dev.yml`
  - prod：`Makefile.prod` + `docker-compose.prod.yml`
- 删除“flask-only”路径与独立脚本：
  - `Makefile.flask:1`（127 行）
  - `docker-compose.flask-only.yml:1`（54 行）
  - `start_uv.sh:1`（65 行）
- 顶层 `Makefile` 保留“分发器”即可（`make dev ... / make prod ...`），砍掉重复的快捷目标块（几十行量级）

预期净减少：至少 **246~286 行 + 1 份 compose**（并减少一整条入口路径）

风险：

- 如果有人依赖 flask-only（host 网络）部署，会失去这条路径

验证：

- dev：`make dev start` / `make dev stop`、`uv run python app.py`
- prod：`make prod start` / `make prod stop`

### 2.2 P0：生产部署存在“双路径”（Makefile.prod vs scripts/deploy）

复杂度来源（证据）：

- deploy 脚本目录：`scripts/deploy/deploy-prod-all.sh:1`、`scripts/deploy/deploy-prod-base.sh:1`、`scripts/deploy/deploy-prod-flask.sh:1`、`scripts/deploy/update-prod-flask.sh:1`
- 4 个脚本合计 **1,947 行**（`wc -l scripts/deploy/*.sh`）
- 同时 `Makefile.prod:1` 也提供 deploy/start/stop/update 等

可删/可合并的最小路径：

- 只保留一条“生产部署真源”（二选一）：
  1) 保留 `Makefile.prod`，删除 `scripts/deploy/*`（净减最大）
  2) 保留 `scripts/deploy/*`，删除 `Makefile.prod` 中重叠目标（净减略小，但可能保留更多脚本能力）

预期净减少：最多 **1,947 行**（如果删掉 deploy 脚本整套）

风险：

- `deploy-prod-all.sh` 可能包含额外初始化/健康检查/账号初始化等逻辑；删前必须确认已被 `Makefile.prod` 等价覆盖

验证：

- 选定唯一部署路径后，完整走一次部署/更新
- 核心健康接口（例如 `/api/v1/health/basic`）可用

### 2.3 P0：Python 依赖口径重复（pyproject + requirements 导出 + 双 dev 组）

复杂度来源（证据）：

- `pyproject.toml:42` 存在 `[project.optional-dependencies].dev`
- `pyproject.toml:230` 存在 `[dependency-groups].dev`（重复一份 dev 依赖组）
- 同时存在 `requirements.txt:1`（1186 行）与 `requirements-prod.txt:1`（85 行）
- `Makefile:73` 还保留 uv/pip 双安装路径

可删/可合并的最小路径（推荐：uv 单一真源）：

- 依赖真源只保留：`pyproject.toml` + `uv.lock`
- 删除导出 requirements：
  - `requirements.txt:1`
  - `requirements-prod.txt:1`
- `pyproject.toml` 里只保留一套 dev 依赖定义（不要两份）
- `Makefile` 去掉 pip fallback（否则等于支持两条安装路径）

预期净减少：至少 **1,271 行**（requirements 两文件）+ 若干重复 dev 依赖声明

风险：

- 若某些 CI/服务器仍用 `pip install -r requirements.txt`，需要迁移到 `uv sync --frozen`

验证：

- `uv sync --frozen`
- `uv run pytest -m unit`
- `docker build -f Dockerfile.prod .`（确保镜像仍能用 uv 安装依赖）

### 2.4 P1：多数据库支持是“easy 的扩展”，但在代码与镜像层都极重

复杂度来源（证据）：

- 多 DB driver 依赖：`pyproject.toml:1`（pymysql/pymssql/oracledb/pyodbc 等）
- 生产镜像安装 Oracle Instant Client：`Dockerfile.prod:63`
- adapter 家族并行（仅示例的几块就已是大头）：
  - `app/services/accounts_sync/adapters/*.py:1`（约 3,197 行）
  - `app/services/connection_adapters/adapters/*.py:1`（约 969 行）
  - `app/services/database_sync/adapters/*.py:1`（约 1,210 行）
  - `app/services/database_sync/table_size_adapters/*.py:1`（约 556 行）

可删/可合并的最小路径（强前提：业务确认只需要 PostgreSQL）：

- 删除非 PostgreSQL 的 adapter 文件
- 从 `pyproject.toml` 移除非 PostgreSQL 的驱动依赖
- 从 `Dockerfile.prod` 删除 Oracle Instant Client 安装段（`Dockerfile.prod:63` 起）

预期净减少：**数千行代码 + 显著降低镜像构建复杂度**

风险：

- 这是“功能删减”（会直接失去 MySQL/SQLServer/Oracle 支持），必须先确认业务范围

验证：

- 仅跑 PostgreSQL 的核心流程：实例连接测试、账户同步、容量采集、表尺寸采集、任务调度

### 2.5 P1：Node 工具链只为 ESLint（可选删减项）

复杂度来源（证据）：

- `package.json:1`、`eslint.config.cjs:1`、`scripts/ci/eslint-report.sh:1`
- `package-lock.json:1`（3036 行）

可删/可合并的最小路径：

- 若 ESLint 非硬门禁：删除整套 Node lint 工具链与相关 CI 入口

预期净减少：约 **3,208 行 + 1 套工具链**

风险：

- 失去 JS 静态检查（需要用 code review/更少 JS 入口来兜底）

验证：

- CI/本地流程不再调用 ESLint，且 Python 质量门禁照常通过

### 2.6 P2：测试入口重复（Makefile.dev vs scripts/test）

复杂度来源（证据）：

- `scripts/test/run-unit-tests.sh:1`（217 行）做了大量包装
- 但 `Makefile.dev` 已有直接跑 `uv run pytest -m unit` 的入口

可删/可合并的最小路径：

- 二选一：
  - 追求最小代码量：删 `scripts/test/run-unit-tests.sh`
  - 追求便利：让 `Makefile.dev` 只调用脚本并删掉重复入口（但这通常不如直接删脚本省）

预期净减少：**217 行**

风险：

- 可能失去自动生成 `.env.test.local` 的便利（需要确认脚本里是否承担该职责）

验证：

- `uv run pytest -m unit` 能稳定运行

## 3. 需要你确认的决策点（决定能删多少）

1) 生产部署的唯一真源：`Makefile.prod` 还是 `scripts/deploy/*`？
2) 是否必须保留 MySQL/SQLServer/Oracle 支持？
3) ESLint 是否硬门禁？（可否删 Node 工具链）
4) 是否必须保留 pip 安装路径？（否则可收敛为 uv 单一路径）
5) 是否有人在用 flask-only（host 网络）部署？

这些决策会直接决定“可净删的行数规模”（从几百行到上万行）。

