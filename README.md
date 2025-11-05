# 鲸落 (TaifishV4)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.2.1-blue.svg)](CHANGELOG.md#121---2025-11-05)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

> 鲸落是一套面向 DBA 团队的数据库资源管理平台，围绕实例、账户、容量与任务调度等场景提供统一的管理与审计能力。

---

## 🚀 1.2.1 焦点

- **重构核心服务**：账户同步、权限差异与历史日志逻辑整体梳理，`type_specific` 字段结构统一，摘要信息更清晰。
- **系统信息一致化**：所有页脚、API 与脚本中的版本号同步更新，About 页面新增核心服务重构说明。
- **文档同步更新**：新增 `permissions_type_specific` 重构说明，刷新部署手册、架构文档版本标识。

完整更新详情见 [CHANGELOG.md](CHANGELOG.md#121---2025-11-05)。

---

## ✨ 核心能力

- **多实例管理**：集中管理 PostgreSQL、MySQL、SQL Server、Oracle 等数据库实例。
- **账号与权限治理**：账户同步、智能分类、权限差异分析与审计日志。
- **容量洞察**：实例 / 数据库容量同步、周期聚合、趋势分析与 TOP 榜单。
- **调度与自动化**：基于 APScheduler 的任务中心，支持手动、定时与批量执行。
- **统一日志中心**：结构化日志、同步会话追踪、异常告警。
- **安全与合规**：凭据加密存储、CSRF 防护、全链路审计。

更多模块拆解参见 [docs/architecture/PROJECT_STRUCTURE.md](docs/architecture/PROJECT_STRUCTURE.md)。

---

## ⚙️ 快速开始

```bash
# 1. 克隆代码
git clone https://github.com/nyealovey/TaifishingV4.git
cd TaifishingV4

# 2. 安装依赖（推荐使用 uv）
make install

# 3. 准备环境变量
cp env.development .env
# 按需修改 .env，配置数据库、Redis、密钥等

# 4. 启动开发环境（PostgreSQL + Redis）
make dev start

# 5. 启动 Flask 应用
make dev start-flask
```

> 生产部署请参考 [docs/deployment/PRODUCTION_DEPLOYMENT.md](docs/deployment/PRODUCTION_DEPLOYMENT.md)。

---

## 🗂️ 目录索引

- [docs/README.md](docs/README.md) - 项目 About 页面与版本综述
- [docs/api/README.md](docs/api/README.md) - API 文档
- [docs/architecture/spec.md](docs/architecture/spec.md) - 体系结构与设计背景
- [docs/development/DEVELOPMENT_SETUP.md](docs/development/DEVELOPMENT_SETUP.md) - 开发环境搭建
- [docs/deployment/PRODUCTION_DEPLOYMENT.md](docs/deployment/PRODUCTION_DEPLOYMENT.md) - 生产部署指南

---

## 🙌 贡献 & 支持

欢迎提交 Issue / PR，共创更好的数据库管理平台。

- 问题反馈：[GitHub Issues](https://github.com/nyealovey/TaifishingV4/issues)
- 讨论交流：[GitHub Discussions](https://github.com/nyealovey/TaifishingV4/discussions)

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 发布。欢迎在遵守许可证的前提下使用并衍生。
