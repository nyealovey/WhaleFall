---
title: WhaleFall 脚本规范
aliases:
  - scripts-standards
tags:
  - standards
  - standards/general
status: active
enforcement: guide
created: 2025-12-25
updated: 2026-01-25
owner: WhaleFall Team
scope: "`scripts/` 目录下所有脚本"
related:
  - "[[standards/README]]"
---

# WhaleFall 脚本规范

---

## 1. 目的

- 统一脚本的目录结构与命名规范，消除"脚本散落、职责不清"的问题。
- 明确不同类型脚本的编写标准，便于维护与复用。
- 提供门禁/检查方式，确保新增脚本符合规范。

---

## 2. 适用范围

本规范适用于 `scripts/` 目录下的所有脚本，包括：

- Shell 脚本（`.sh`）
- Python 脚本（`.py`）
- 其他可执行脚本

---

## 3. 目录结构（标准）

`scripts/` 下按"运行时机/用途"划分子目录，而非按"技术组件"划分：

当前目录结构与入口命令以 `scripts/README.md` 为准(标准不保留长目录树).

### 3.1 目录职责定义

| 目录 | 职责 | 运行时机 | 运行者 |
|------|------|----------|--------|
| `ci/` | 代码门禁、风格检查、类型检查 | PR 提交前 / CI 流水线 | 开发者 / CI |
| `setup/` | 环境安装、依赖初始化、环境验证 | 首次部署 / 环境重建 | 运维 |
| `deploy/` | 生产环境部署、版本更新 | 发布时 | 运维 |
| `ops/` | 日常运维操作（容器/Nginx/数据库/缓存） | 日常运维 | 运维 |
| `admin/` | 系统管理操作（密码/安全/审计） | 按需 | 管理员 |
| `dev/` | 开发辅助（代码统计/文档生成） | 开发时 | 开发者 |
| `test/` | 测试运行、测试数据准备、冒烟测试 | 开发/部署后验证 | 开发者 / CI |

### 3.2 约束

- **禁止**在 `scripts/` 下新增与上述并列的"新一级目录"。如确需新增，必须先更新本规范并在 PR 中说明理由。
- **根目录**（`scripts/`）仅保留 `README.md`，不放置脚本文件。
- **二级目录**（如 `ops/docker/`）按需创建，避免过度嵌套（最多三级）。

---

## 4. 命名规范

### 4.1 文件名

| 规则 | 说明 | 正例 | 反例 |
|------|------|------|------|
| MUST | 全小写 `kebab-case` 或 `snake_case` | `deploy-prod-all.sh`、`reset_admin_password.py` | `DeployProd.sh`、`resetAdminPassword.py` |
| MUST | 扩展名明确（`.sh`/`.py`） | `deploy-prod-flask.sh` | `deploy-prod-flask` |
| SHOULD | 动词开头，表达操作意图 | `reset_admin_password.py`、`cleanup-prod.sh` | `admin_password.py`、`prod.sh` |
| SHOULD | 门禁脚本以 `_guard.sh` 结尾 | `error_message_drift_guard.sh` | `error_message_drift.sh` |
| SHOULD | 报告脚本以 `_report.sh` 结尾 | `ruff_report.sh`、`pyright_report.sh` | `ruff.sh` |

### 4.2 目录名

- MUST：全小写 `snake_case` 或 `kebab-case`（与现有保持一致）。
- MUST NOT：空格、中文、大小写混用。

---

## 5. 脚本结构规范

### 5.1 Shell 脚本（`.sh`）

判定点:

- `scripts/ci/**`(门禁/报告脚本) MUST 具备: `#!/usr/bin/env bash` + `set -euo pipefail` + `--help` 用法说明.
- 其他脚本 SHOULD 具备上述元素, 但允许按场景取舍(例如一次性 dev 脚本可简化).
- 门禁脚本 MUST 以退出码表达通过/失败(0 通过, 非 0 失败).

长模板见: [[reference/examples/scripts-templates#Shell 脚本模板|Shell 脚本模板(长示例)]]

### 5.2 Python 脚本（`.py`）

判定点:

- `scripts/ci/**` 与会写数据的 admin/ops 脚本 SHOULD 具备: shebang + module docstring(含用法) + 统一 `main() -> int` 退出码.
- 应通过 argparse 声明参数, 方便 `--help` 与 CI 集成.

长模板见: [[reference/examples/scripts-templates#Python 脚本模板|Python 脚本模板(长示例)]]

---

## 6. 分类规范

### 6.1 CI 门禁脚本（`ci/`）

**职责**：CI 流水线或本地提交前的代码检查。

**命名约定**：
- 检查类：`*-guard.sh`（如 `error-message-drift-guard.sh`）
- 报告类：`*-report.sh`（如 `ruff-report.sh`）

**必须包含**：
- `--help` 参数
- 退出码：0 表示通过，非 0 表示失败
- 基线机制（如需）：`--update-baseline` 参数

**示例结构**：
```bash
#!/usr/bin/env bash
# xxx 门禁：检查 xxx 是否符合规范

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASELINE_FILE="${ROOT_DIR}/ci/baselines/xxx.txt"

# 支持 --update-baseline 参数
if [[ "${1:-}" == "--update-baseline" ]]; then
    # 更新基线
    exit 0
fi

# 检查逻辑
# ...

# 输出结果
echo "检查通过"
exit 0
```

### 6.2 环境安装脚本（`setup/`）

**职责**：首次部署时的环境安装、依赖初始化、环境验证。

**命名约定**：
- 安装类：`install-*.sh`
- 初始化类：`init-*.sh`（如 `init-database.sh`）
- 验证类：`validate-*.sh`（如 `validate-env.sh`）

**必须包含**：
- 幂等性（重复执行不报错）
- 依赖检查（缺失时给出安装指引）
- 成功/失败的明确提示

### 6.3 部署脚本（`deploy/`）

**职责**：生产环境部署、版本更新。

**命名约定**：
- 全量部署：`deploy-*.sh`（如 `deploy-prod-all.sh`）
- 热更新：`update-*.sh`（如 `update-prod-flask.sh`）

**必须包含**：
- 版本号（在脚本头部注释）
- 环境检查（Docker、环境变量等）
- 确认提示（危险操作前）
- 回滚说明（注释或文档）
- 日志输出（带颜色/图标）

### 6.4 运维脚本（`ops/`）

**职责**：日常运维操作（容器管理、Nginx、数据库、缓存）。

**子目录命名约定**：
- `ops/docker/`：容器管理
  - `start-*.sh`、`stop-*.sh`、`cleanup-*.sh`
- `ops/nginx/`：Nginx 管理
  - `nginx-*.sh`、`ssl-*.sh`
- `ops/db/`：数据库运维
  - `backup-*.sh`、`restore-*.sh`
- `ops/cache/`：缓存运维
  - `redis-*.sh`

**必须包含**：
- 环境变量加载（`.env`）
- 服务状态检查
- 错误处理与回滚

### 6.5 管理脚本（`admin/`）

**职责**：系统管理操作（密码管理、安全审计）。

**子目录**：
- `admin/password/`：密码重置、查看
- `admin/security/`：敏感数据脱敏、安全审计

**安全约束**：
- 禁止在日志中输出明文密码/密钥
- 必须使用 Flask app context（Python 脚本）
- 必须记录操作日志
- 必须支持 `--dry-run` 参数（涉及数据修改时）

### 6.6 开发辅助脚本（`dev/`）

**职责**：本地开发使用的辅助工具。

**子目录**：
- `dev/code/`：代码统计、质量分析
- `dev/docs/`：文档生成、报告导出

**特点**：
- 不影响生产环境
- 可以有更宽松的错误处理
- 建议提供 `--verbose` 参数

### 6.7 测试脚本（`test/`）

**职责**：测试运行、测试数据准备、冒烟测试。

**命名约定**：
- 测试运行：`run-*.sh`（如 `run-unit-tests.sh`、`run-integration-tests.sh`）
- 冒烟测试：`smoke-*.sh`（如 `smoke-api.sh`、`smoke-health.sh`）
- 数据准备：`prepare-*.sh`（如 `prepare-fixtures.sh`）

**子目录**：
- `test/fixtures/`：测试数据、夹具文件

**必须包含**：
- 退出码：0 表示测试通过，非 0 表示失败
- 测试结果摘要输出
- 支持 `--verbose` 参数（详细输出）

**示例**：
```bash
#!/usr/bin/env bash
# 运行单元测试

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 运行 pytest
pytest -m unit "$@"
```

---

## 7. 规则（通用规范）

### 7.1 `scripts/ci/**` 门禁/报告脚本必须遵守(强约束)

| 规则 | 说明 |
|------|------|
| MUST | 脚本头部包含 shebang（`#!/usr/bin/env bash` 或 `#!/usr/bin/env python3`） |
| MUST | Shell 脚本使用 `set -euo pipefail`（严格模式） |
| MUST | 提供 `--help` 参数 |
| MUST | 使用退出码表示执行结果（0 成功，非 0 失败） |
| MUST | 错误信息输出到 stderr（`>&2`） |
| MUST | 路径使用相对于脚本目录或项目根目录的方式，避免硬编码绝对路径 |

### 7.2 其他脚本建议遵守(避免过度要求)

| 规则 | 说明 |
|------|------|
| SHOULD | 脚本头部包含 shebang（`#!/usr/bin/env bash` 或 `#!/usr/bin/env python3`） |
| SHOULD | Shell 脚本优先使用 `set -euo pipefail`（严格模式） |
| SHOULD | 提供 `--help` 参数(尤其是可能被他人复用的脚本) |
| SHOULD | 使用退出码表示执行结果（0 成功，非 0 失败） |
| SHOULD | 错误信息输出到 stderr（`>&2`） |
| SHOULD | 路径使用相对脚本目录或项目根目录, 避免硬编码绝对路径 |
| SHOULD | 使用颜色输出提升可读性 |
| SHOULD | 提供 `--dry-run` 参数（涉及写操作时） |
| SHOULD | 提供 `--verbose` 参数（调试时） |
| SHOULD | 危险操作前要求用户确认 |
| SHOULD | 长时间操作显示进度 |
| SHOULD | 脚本内包含使用示例 |

### 7.3 禁止

| 规则 | 说明 |
|------|------|
| MUST NOT | 硬编码敏感信息（密码、密钥） |
| MUST NOT | 使用 `cd` 改变工作目录后不恢复 |
| MUST NOT | 忽略命令执行结果（除非明确需要） |
| MUST NOT | 在日志中输出敏感信息 |

### 7.4 正反例

正例:

- Shell 脚本包含 shebang + `set -euo pipefail`, 并实现 `--help`.
- 写操作脚本提供 `--dry-run`, 且危险操作前要求确认.

反例:

- 缺少 shebang/严格模式, 执行失败后仍继续跑完(难排查).
- 直接 `rm -rf` 或写库操作无确认/无 dry-run.

---

## 8. 文档要求

### 8.1 脚本内文档

`scripts/ci/**` SHOULD 在头部包含(便于审查与复用):

- 简要说明（一行）
- 用法说明
- 参数/选项说明
- 示例（可选）

### 8.2 目录 README

每个子目录建议包含 `README.md`，说明：

- 目录用途
- 包含的脚本列表及简要说明
- 常用命令示例

---

## 9. 门禁/检查方式

### 9.1 现有门禁（迁移后路径）

| 门禁脚本 | 检查内容 | 运行命令（迁移后） |
|----------|----------|----------|
| `account-classification-auto-tasks-guard.sh` | account classification auto task 的关键分支防回归（`if not accounts:` 守护） | `./scripts/ci/account-classification-auto-tasks-guard.sh` |
| `api-layer-guard.sh` | API 层越界依赖/直查库/直触 DB | `./scripts/ci/api-layer-guard.sh` |
| `api-v1-ns-expect-guard.sh` | API v1 namespaces：`request.get_json()` 必须配 `@ns.expect(...)` | `./scripts/ci/api-v1-ns-expect-guard.sh` |
| `browser-confirm-guard.sh` | 禁止 `confirm()` 弹窗（统一 `UI.confirmDanger`） | `./scripts/ci/browser-confirm-guard.sh` |
| `btn-close-aria-guard.sh` | `btn-close` 可访问名称（`aria-label="关闭"`） | `./scripts/ci/btn-close-aria-guard.sh` |
| `button-hierarchy-guard.sh` | 按钮层级：禁止全局 `.btn { border: none/0 }` | `./scripts/ci/button-hierarchy-guard.sh` |
| `component-style-drift-guard.sh` | 组件样式漂移：禁止 pages 层重复定义共享组件类 | `./scripts/ci/component-style-drift-guard.sh` |
| `css-token-guard.sh` | CSS Token：禁止 `var(--xxx)` 引用未定义 token | `./scripts/ci/css-token-guard.sh` |
| `danger-button-semantics-guard.sh` | 危险按钮语义：禁止 `text-danger` 伪装危险按钮 | `./scripts/ci/danger-button-semantics-guard.sh` |
| `db-session-commit-allowlist-guard.sh` | `db.session.commit()` 位置 allowlist（全局） | `./scripts/ci/db-session-commit-allowlist-guard.sh` |
| `db-session-commit-services-drift-guard.sh` | services `commit()` 漂移（baseline，禁止新增） | `./scripts/ci/db-session-commit-services-drift-guard.sh` |
| `db-session-rollback-allowlist-guard.sh` | `db.session.rollback()` allowlist（禁止 services/repositories，infra 严格白名单） | `./scripts/ci/db-session-rollback-allowlist-guard.sh` |
| `db-session-route-write-guard.sh` | routes 直写 `db.session.*`（add/delete/commit/flush） | `./scripts/ci/db-session-route-write-guard.sh` |
| `db-session-write-boundary-guard.sh` | 写操作事务边界组合门禁 | `./scripts/ci/db-session-write-boundary-guard.sh` |
| `error-message-drift-guard.sh` | `error/message` 互兜底漂移（baseline，禁止新增） | `./scripts/ci/error-message-drift-guard.sh` |
| `eslint-report.sh` | JavaScript 代码风格报告 | `./scripts/ci/eslint-report.sh quick` |
| `frontend-contracts-guard.sh` | 前端分层/注入/迁移 contracts 防回归（从 tests 迁移为门禁） | `./scripts/ci/frontend-contracts-guard.sh` |
| `forms-layer-guard.sh` | 防止 `app/forms/**` 体系回归（跨层依赖/DB/query） | `./scripts/ci/forms-layer-guard.sh` |
| `grid-wrapper-log-guard.sh` | 禁止 GridWrapper 常驻 `console.log` | `./scripts/ci/grid-wrapper-log-guard.sh` |
| `inline-handler-guard.sh` | 模板 inline handler（baseline，禁止新增） | `./scripts/ci/inline-handler-guard.sh` |
| `inline-px-style-guard.sh` | 模板 inline px 布局（baseline，禁止新增） | `./scripts/ci/inline-px-style-guard.sh` |
| `ops-legacy-guard.sh` | 运维/部署脚本 legacy 回归（旧 health 路径、迁移残留） | `./scripts/ci/ops-legacy-guard.sh` |
| `or-fallback-pattern-guard.sh` | 高风险 `or` 兜底形态（禁字段 alias 链/禁 silent fallback） | `./scripts/ci/or-fallback-pattern-guard.sh` |
| `pagination-param-guard.sh` | 分页参数一致性（必须用 `limit`） | `./scripts/ci/pagination-param-guard.sh` |
| `pyright-guard.sh` | Pyright baseline（禁止新增 diagnostics） | `./scripts/ci/pyright-guard.sh` |
| `pyright-report.sh` | Python 类型检查报告 | `./scripts/ci/pyright-report.sh` |
| `refactor-naming.sh` | 命名巡检（重命名建议/报告） | `./scripts/ci/refactor-naming.sh --dry-run` |
| `repositories-route-safety-import-guard.sh` | repositories 禁止依赖 `app.infra.route_safety` | `./scripts/ci/repositories-route-safety-import-guard.sh` |
| `routes-safe-route-call-guard.sh` | routes 含 route 定义的模块必须使用 `safe_route_call(...)` | `./scripts/ci/routes-safe-route-call-guard.sh` |
| `ruff-report.sh` | Python 代码风格报告 | `./scripts/ci/ruff-report.sh style` |
| `ruff-style-guard.sh` | Ruff(style) baseline（禁止新增 D/I/PLC/G violations） | `./scripts/ci/ruff-style-guard.sh` |
| `secrets-guard.sh` | `env.example` 禁止写入真实密钥/口令 | `./scripts/ci/secrets-guard.sh` |
| `services-repository-enforcement-guard.sh` | Service 直查库/query（baseline，禁止新增） | `./scripts/ci/services-repository-enforcement-guard.sh` |
| `settings-env-read-guard.sh` | settings 之外禁止读取环境变量（os.environ.get/os.getenv） | `./scripts/ci/settings-env-read-guard.sh` |
| `tag-selector-filter-id-guard.sh` | 可复用组件固定 DOM id 回归（TagSelectorFilter） | `./scripts/ci/tag-selector-filter-id-guard.sh` |
| `tasks-layer-guard.sh` | tasks 直查库/直写库（允许 commit/rollback 作为边界入口） | `./scripts/ci/tasks-layer-guard.sh` |
| `ui-standards-audit-guard.sh` | UI standards audit 聚合门禁（hex 颜色/固定 id/Grid.js 直用等） | `./scripts/ci/ui-standards-audit-guard.sh` |

### 9.2 建议新增门禁

- 检测 `scripts/` 下是否存在不合规目录名
- 检测脚本是否包含 shebang
- 检测脚本是否包含 `--help` 参数

---

---

## 10. 变更历史

| 日期 | 变更内容 |
|------|----------|
| 2025-12-25 | 初始版本：按"运行时机/用途"重新设计目录结构 |
| 2026-01-08 | 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter |
| 2026-01-09 | scripts 目录结构迁移: 迁移映射/步骤/兼容性过渡(一次性记录, 用后可删) |
| 2026-01-15 | 新增门禁：补充 `inline-handler-guard.sh`（模板 inline handler 回归） |
| 2026-01-25 | 减负: 区分 `scripts/ci/**`(强约束) 与其他脚本(建议), 并补齐 `scripts/ci` 门禁清单 |
