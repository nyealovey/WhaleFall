# Git 工作流与分支规范

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2025-12-26
> 更新: 2025-12-26
> 范围: 本仓库所有代码与文档变更
> 关联: AGENTS.md, docs/standards/new-feature-delivery-standard.md, docs/standards/version-update-guide.md

## 1. 目的

- 明确 `main` 与 `dev` 的职责边界, 降低线上风险与返工成本.
- 统一分支命名与 PR 基准分支, 让协作流程可预测, 可审计, 可长期维护.

## 2. 适用范围

- 本规范适用于仓库内所有变更: 后端, 前端, 文档, 脚本, 运维配置.

## 3. 分支角色定义

### 3.1 长期分支

- `main`: 生产就绪分支. MUST 仅通过 PR 合入.
- `dev`: 长期开发集成分支. 日常开发变更默认合入该分支.

### 3.2 短期分支

- `feat/<scope>-<topic>`: 新功能分支.
- `fix/<scope>-<topic>`: 缺陷修复分支.
- `refactor/<scope>-<topic>`: 重构分支.
- `docs/<topic>`: 文档分支.
- `chore/<topic>`: 工程化与杂项分支.
- `wip/<topic>`: 临时快照分支, 允许不完整, MUST 标注用途并尽快清理.

> 说明: `<scope>` 建议使用模块名, 例如 `api`, `ui`, `db`, `auth`.

## 4. 工作流规则

### 4.1 日常开发

- MUST 从 `dev` 拉出短期分支进行开发.
- MUST 通过 PR 合入 `dev`, 不允许直接 push 到 `dev`.
- SHOULD 采用 squash merge, 保持 `dev` 历史简洁.
- MUST 在 PR 描述中写清: 变更范围, 验证命令, 是否影响配置/迁移/对外接口, 是否需要回滚说明.

### 4.2 发布与回灌

- 发布版本 SHOULD 从 `dev` 进入 `main`.
- 当 `main` 合入发布 PR 后, MUST 将 `main` 的发布提交回灌到 `dev` (避免版本号与修复漂移).

### 4.3 紧急修复

- 生产紧急修复 MUST 从 `main` 拉出 `fix/<scope>-<topic>` 分支, PR 目标为 `main`.
- `main` 合入后, MUST 将同等修复同步到 `dev` (推荐 cherry-pick 或回灌合并).

## 5. PR 门禁与自检

PR 合入 `dev` 或 `main` 前, MUST 完成以下自检:

- `make format`
- `make typecheck`
- `pytest -m unit`
- `./scripts/ci/secrets-guard.sh` (如改动 `env.example` 或疑似配置相关文件)

如 PR 涉及迁移, 配置, 对外接口, MUST 在 PR 中补充:

- 迁移策略与回滚策略.
- 兼容性说明(如存在字段迁移, 版本化, 别名兼容等).

## 6. 正反例

### 6.1 正例

- 新功能: 从 `dev` 拉出 `feat/api-bulk-create`, PR 合入 `dev`.
- 修复线上: 从 `main` 拉出 `fix/auth-jwt-exp`, PR 合入 `main`, 再同步到 `dev`.

### 6.2 反例

- 直接 push 到 `main` 或 `dev`.
- 将日常功能 PR 直接指向 `main`(除发布/紧急修复外).

## 7. 变更历史

- 2025-12-26: 新增 `main/dev` 分支工作流规范, 作为长期协作基线.

