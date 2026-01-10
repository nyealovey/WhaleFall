# 026 scripts directory structure migration

> 状态: Archived
> 负责人: WhaleFall Team
> 创建: 2026-01-09
> 更新: 2026-01-09
> 范围: `scripts/` 目录结构标准化的迁移记录(迁移映射/步骤/兼容性过渡)
> 关联:
> - `docs/Obsidian/standards/scripts-standards.md`
> - `docs/Obsidian/standards/doc/changes-standards.md`
> - `docs/Obsidian/standards/doc/document-boundary-standards.md`

---

## 动机与范围

- 动机: `scripts/` 存量脚本分散在多个 legacy 目录, 不利于检索与门禁收敛.
- 范围: 将脚本按"用途/时机"归档到 `ci/setup/deploy/ops/admin/dev/test`, 并同步更新相关入口文档与调用路径.

## 迁移映射

| 现有位置 | 目标位置 | 说明 |
|---|---|---|
| `scripts/code_review/` | `scripts/ci/` | 门禁脚本 |
| `scripts/deployment/` | `scripts/deploy/` | 部署脚本 |
| `scripts/docker/start-prod-base.sh` | `scripts/deploy/deploy-prod-base.sh` | 部署脚本(分步启动基础服务) |
| `scripts/docker/start-prod-flask.sh` | `scripts/deploy/deploy-prod-flask.sh` | 部署脚本(分步启动应用) |
| `scripts/docker/` | `scripts/ops/docker/` | Docker 运维 |
| `scripts/nginx/` | `scripts/ops/nginx/` | Nginx 运维 |
| `scripts/oracle/` | `scripts/setup/` | 依赖安装 |
| `scripts/password/` | `scripts/admin/password/` | 密码管理 |
| `scripts/security/` | `scripts/admin/security/` | 安全操作 |
| `scripts/code/` | `scripts/dev/code/` | 代码分析 |
| `scripts/docs/` | `scripts/dev/openapi/` | 文档生成(OpenAPI 导出) |
| `scripts/validate_env.sh` | `scripts/setup/validate-env.sh` | 环境验证 |
| `scripts/refactor_naming.sh` | `scripts/ci/refactor-naming.sh` | 命名检查 |

## 迁移步骤

1. 创建新目录结构.
2. 移动脚本文件(保留 git 历史).
3. 更新脚本内的相对路径引用.
4. 更新 `AGENTS.md` / `scripts/README.md` 等入口文档中的命令路径.
5. 更新 CI 配置中的脚本路径(如有).
6. 删除旧目录.

## 兼容性过渡

迁移期间, 如确需短期兼容旧路径, 允许在旧路径保留转发脚本, 但必须:

- 明确注明"仅兼容转发"与目标路径.
- 禁止在转发脚本中引入额外逻辑, 避免 drift.

示例:

```bash
#!/usr/bin/env bash
# 已迁移到 scripts/ci/, 此文件仅作兼容转发
exec "$(dirname "$0")/../ci/ruff-report.sh" "$@"
```

## 验证与门禁

- `./scripts/ci/ruff-report.sh style`
- `./scripts/ci/pyright-report.sh`
- `./scripts/ci/eslint-report.sh quick`(如涉及 `app/static/js`)
- `./scripts/setup/validate-env.sh`(如涉及 env.example)

## 风险与回滚

- 风险: 路径变更导致 CI 或文档入口命令失效.
- 回滚: 通过 `git revert` 回滚本次迁移提交, 或临时增加"兼容性转发脚本"(有明确下线计划).

