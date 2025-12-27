# WhaleFall 脚本目录（scripts/）

本目录遵循：`docs/standards/scripts-standards.md`。

## 目录结构

```text
scripts/
├── README.md
├── ci/                     # CI/CD 门禁脚本（提交前/流水线）
├── setup/                  # 环境安装/初始化/验证
├── deploy/                 # 部署/热更新脚本
├── ops/                    # 运维脚本（日常运维）
│   ├── docker/
│   └── nginx/
├── admin/                  # 管理脚本（密码/安全）
│   ├── password/
│   └── security/
├── dev/                    # 开发辅助脚本
│   └── code/
└── test/                   # 测试脚本
```

## 常用命令（入口）

### CI / 门禁

- Ruff（报告）：`./scripts/ci/ruff-report.sh style`
- Pyright（报告）：`./scripts/ci/pyright-report.sh`
- ESLint（报告，改动 JS 时）：`./scripts/ci/eslint-report.sh quick`
- 命名巡检：`./scripts/ci/refactor-naming.sh --dry-run`
- `env.example` 密钥门禁：`./scripts/ci/secrets-guard.sh`

### Setup / 环境验证

- 环境变量完整性检查：`./scripts/setup/validate-env.sh`

### Deploy / Ops / Admin / Dev / Test

- 部署脚本：
  - 全量部署：`./scripts/deploy/deploy-prod-all.sh`
  - 分步部署：`./scripts/deploy/deploy-prod-base.sh`、`./scripts/deploy/deploy-prod-flask.sh`
  - 热更新：`./scripts/deploy/update-prod-flask.sh`
- Docker 运维：见 `scripts/ops/docker/`
- Nginx 运维：见 `scripts/ops/nginx/`
- 密码管理：见 `scripts/admin/password/`
- 安全操作：见 `scripts/admin/security/`
- 代码分析：见 `scripts/dev/code/`
- 本地同步代码到运行中的 Docker 容器（用于快速验证）：`./scripts/dev/sync-local-code-to-docker.sh`
- 测试运行：`./scripts/test/run-unit-tests.sh`
