# 修复文档：脚本路径迁移（按 `scripts-standards.md` 统一脚本入口）

## 1. 症状与影响

仓库已引入 `docs/standards/scripts-standards.md` 作为脚本目录规范，但实际 `scripts/` 仍停留在旧结构（如 `scripts/code_review/`、`scripts/deployment/` 等）。这会导致：

- 按规范/新文档执行脚本时出现 “No such file or directory”。
- 不同文档/入口给出的脚本命令不一致，维护成本高、容易误用。
- 一些脚本间的相互引用（baseline/提示文案）在迁移后会失效。

## 2. 复现步骤

1. 查看脚本目录是否存在规范定义的入口目录（如 `scripts/ci/`、`scripts/setup/`）。
2. 尝试执行规范中的命令（示例）：
   - `./scripts/ci/ruff-report.sh style`
   - `./scripts/setup/validate-env.sh`
3. 若未迁移，会出现脚本不存在/路径错误等问题。

## 3. 根因分析

- 标准先行：`docs/standards/scripts-standards.md` 定义了新的脚本目录结构与迁移映射。
- 落地滞后：脚本文件未按映射迁移，且仓库中大量文档/代码仍引用旧路径。
- 命名漂移：CI 门禁脚本在旧结构下以 `snake_case` 命名（如 `ruff_report.sh`），而规范示例/入口使用 `kebab-case`（如 `ruff-report.sh`），导致“路径 + 文件名”双重不一致。

## 4. 修复方案

按 `docs/standards/scripts-standards.md` 的迁移映射统一落地：

1. **迁移目录结构**
   - `scripts/code_review/` → `scripts/ci/`
   - `scripts/deployment/` → `scripts/deploy/`
   - `scripts/docker/` → `scripts/ops/docker/`（Docker 运维；`start-prod-*.sh` 迁移到 `scripts/deploy/` 并更名为 `deploy-prod-*.sh`）
   - `scripts/nginx/` → `scripts/ops/nginx/`
   - `scripts/oracle/` → `scripts/setup/`
   - `scripts/password/` → `scripts/admin/password/`
   - `scripts/security/` → `scripts/admin/security/`
   - `scripts/code/` → `scripts/dev/code/`

2. **统一关键入口脚本命名（CI）**
   - `ruff_report.sh` → `ruff-report.sh`
   - `pyright_report.sh` → `pyright-report.sh`
   - `eslint_report.sh` → `eslint-report.sh`
   - `*_guard.sh` → `*-guard.sh`（并更新文档引用）
   - baseline：`error_message_drift.txt` → `error-message-drift.txt`

3. **更新仓库内所有引用点**
   - 文档：`docs/**`（standards/operations/changes/reference/architecture 等）
   - 仓库入口：`AGENTS.md`、`README.md`
   - 工具/构建：`Makefile.prod`、`Dockerfile.prod`
   - 辅助工具：`skills/**`

4. **补齐脚本目录入口文档**
   - 新增 `scripts/README.md` 作为目录总览与常用入口集合。

## 5. 回归验证

建议在仓库根目录执行（按需）：

- 路径存在性（结构复核）：`find scripts -maxdepth 2 -type d -print`
- 常用门禁入口：
  - `./scripts/ci/secrets-guard.sh`
  - `./scripts/ci/refactor-naming.sh --dry-run`
- 环境验证入口：`./scripts/setup/validate-env.sh`
- 其它按场景执行：`./scripts/ci/ruff-report.sh style`、`./scripts/ci/pyright-report.sh`、`./scripts/ci/eslint-report.sh quick`

> 注：部分脚本会生成 `docs/reports/*` 或依赖本地环境（Node/Python/虚拟环境），回归时以“能正确定位到脚本并执行到预期阶段”为准。

## 6. 风险与回滚

### 6.1 风险

- 旧路径命令（如 `./scripts/code_review/...`、`./scripts/validate_env.sh`）将不再可用；本地脚本调用、历史文档、个人习惯命令需要同步更新。

### 6.2 回滚

- 如需回滚，优先通过 `git revert`/回退到迁移前版本恢复旧目录结构。
- 若需要短期兼容旧命令，可按 `docs/standards/scripts-standards.md` 的“兼容性过渡”示例，在旧路径补充转发脚本（后续再删除旧目录）。
