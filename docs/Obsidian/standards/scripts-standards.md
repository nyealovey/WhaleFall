---
title: WhaleFall 脚本规范
aliases:
  - scripts-standards
tags:
  - standards
  - standards/general
status: active
created: 2025-12-25
updated: 2026-01-09
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

- 必须具备: `#!/usr/bin/env bash` + `set -euo pipefail` + `--help` 用法说明.
- 门禁脚本必须以退出码表达通过/失败(0 通过, 非 0 失败).

长模板见: [[reference/examples/scripts-templates#Shell 脚本模板|Shell 脚本模板(长示例)]]

### 5.2 Python 脚本（`.py`）

判定点:

- 必须具备: shebang + module docstring(含用法) + 统一 `main() -> int` 退出码.
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
- 安装类：`install-*.sh`（如 `install-oracle-client.sh`）
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

## 7. 通用规范

### 7.1 必须遵守

| 规则 | 说明 |
|------|------|
| MUST | 脚本头部包含 shebang（`#!/usr/bin/env bash` 或 `#!/usr/bin/env python3`） |
| MUST | Shell 脚本使用 `set -euo pipefail`（严格模式） |
| MUST | 提供 `--help` 参数 |
| MUST | 使用退出码表示执行结果（0 成功，非 0 失败） |
| MUST | 错误信息输出到 stderr（`>&2`） |
| MUST | 路径使用相对于脚本目录或项目根目录的方式，避免硬编码绝对路径 |

### 7.2 建议遵守

| 规则 | 说明 |
|------|------|
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

---

## 8. 文档要求

### 8.1 脚本内文档

每个脚本必须在头部包含：

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
| `ruff-report.sh` | Python 代码风格 | `./scripts/ci/ruff-report.sh style` |
| `pyright-report.sh` | Python 类型检查 | `./scripts/ci/pyright-report.sh` |
| `eslint-report.sh` | JavaScript 代码风格 | `./scripts/ci/eslint-report.sh quick` |
| `error-message-drift-guard.sh` | 错误消息漂移 | `./scripts/ci/error-message-drift-guard.sh` |
| `pagination-param-guard.sh` | 分页参数一致性 | `./scripts/ci/pagination-param-guard.sh` |
| `secrets-guard.sh` | 环境变量密钥 | `./scripts/ci/secrets-guard.sh` |
| `tag-selector-filter-id-guard.sh` | TagSelectorFilter 固定 DOM id 回归 | `./scripts/ci/tag-selector-filter-id-guard.sh` |

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
| 2026-01-09 | 将 scripts 迁移映射/迁移步骤/兼容性过渡迁出到 `docs/changes/refactor/026-scripts-directory-structure-migration.md` |
