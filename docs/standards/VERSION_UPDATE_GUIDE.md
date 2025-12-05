# 版本更新操作指南

> 适用范围：当需要发布全局版本（如 `v1.2.x`）时，使用本指南同步核心版本号、校验脚本与可见页面。该流程力求**聚焦必要文件**，避免在重构文档、分析白皮书等大体量文件上反复改动。

## 1. 操作前准备

1. 确认即将发布的版本号（语义化：`MAJOR.MINOR.PATCH`）。
2. 确认此次发版的主题（例如“注释补齐”“安全补丁”等），以便 CHANGELOG 与 About 页面简述。
3. 切换到干净分支，确保本地 `rg`/`python3` 可运行。

## 2. 必须更新的文件清单

此列表为**版本号强一致**的最小集，更新顺序随意，但务必全部覆盖。

| 更新项 | 文件/位置 | 说明 |
| --- | --- | --- |
| 项目配置 | `pyproject.toml` (`[project].version`) | 统一版本源头，供构建工具与 `uv` 使用。 |
| 运行环境 | `env.production` (`APP_VERSION`) | 提供健康检查及 `.env` 示例基线。 |
| 依赖锁 | `uv.lock` 中 `name = "whalefallingv4"` 节点 | 搜索 `[[package]] name = "whalefallingv4"`，更新 `version` 字段。 |
| SQL 初始化 | `sql/init_postgresql.sql` 中 `system_version` 记录 | 保证全新部署默认写入最新版本。 |
| 部署脚本 | `scripts/deployment/deploy-prod-all.sh` | 更新脚本头部注释、欢迎横幅和日志输出中的版本号。 |
| API 元数据 | `app/routes/main.py` (`app_version`) | `/` 健康检查返回值。 |
| 页脚展示 | `app/templates/base.html` 页脚文本 | 网站所有页面的版本展示。 |
| Nginx 错误页 | `nginx/error_pages/404.html` 与 `50x.html` | 访客可见的离线提示页面。 |
| README 徽章与页脚 | `README.md` 顶部徽章 & 底部“最后更新/版本” | 方便外部访客识别最新版本。 |
| CHANGELOG | `CHANGELOG.md` 顶部新增条目 | 采用倒序记录：日期、主题、修复项。 |
| About 页面 | `app/templates/about.html` 简介段落与时间轴 | 仅保留最新版本摘要，不需要调整历史条目。 |

> **说明**：如无特殊需求，不要改动重构文档（例如 `docs/architecture/spec.md`、`docs/architecture/PROJECT_STRUCTURE.md`）或分析报告（例如 `docs/reports/clean-code-analysis.md`）。这些文档仅在内容真正变更时更新，避免纯版本跳动带来的审核负担。

## 3. 可选更新项

- 部署/运维文档示例：若文档明确引用 `APP_VERSION` 示例值，可在同一次 PR 中顺手替换，但不是硬性要求。
- 模板或脚本中以“最近版本”做展示的非核心页面，可视需要更新。

## 4. 操作步骤建议

1. **批量搜索**：更新前运行 `rg -n "1\.2\.x"` 定位当前版本号出现位置，逐一甄别属于“必需列表”还是“可忽略项/依赖版本”。
2. **逐项替换**：按照上表替换版本号，并在 CHANGELOG/About 中写入简短中文描述。
3. **自检脚本**：
   - `python3 scripts/check_missing_docs_smart.py`（确保注释规范仍通过）。
   - 如有数据库变更或部署脚本修改，可额外运行针对性的单元/集成测试。
4. **验证差异**：`git status` 应只包含指南列出的文件（以及与本次功能直接相关的内容）。若出现 `docs/architecture/*`、`docs/reports/*` 等大文档，请确认是否确有内容更新，避免仅为版本号而修改。
5. **提交信息**：建议使用 `chore: bump version to x.y.z` 或 `chore: release vX.Y.Z`，并在 PR 描述中列出验证步骤（脚本、手测等）。

## 5. FAQ

- **Q: 版本更新时是否需要重新生成分析报告?**  
  A: 否。除非分析内容有实质变更，否则不要为了版本号刷新而重跑报告。

- **Q: 依赖文件中出现 `1.2.2`，需要改吗?**  
  A: 若是第三方包（如 `flask-wtf==1.2.2`），保持不变；只处理与本项目自身版本直接相关的字符串。

- **Q: 需要同步更新 Git Tag/Release 吗?**  
  A: 视团队流程而定，通常在 PR 合并后由发布者打 Tag 并生成 Release 说明。

## 6. 页面回归检查（CRUD 模态）

近期凭据、实例、标签、账户分类及分类规则等模块统一了 CRUD 模态展现，请在发版前额外确认以下页面均已加载 `css/components/crud-modal.css` 并保持“芯片标题 + 状态 Pill”结构：

| 模块 | 模板/位置 | 校验要点 |
| --- | --- | --- |
| 凭据管理 | `app/templates/credentials/list.html`（列表） | 顶部 `extra_css` 包含 CRUD 样式；`credential-modals.html` 显示“凭据配置 / 新建”头部。 |
| 实例管理 | `app/templates/instances/list.html`、`instances/detail.html` | 列表与详情页都需引入 CRUD 样式，模态内 header 与按钮文案同步。 |
| 标签管理 | `app/templates/tags/index.html` | 模态头部为“标签配置”，状态 Pill 会随模式切换。 |
| 账户分类/规则 | `app/templates/accounts/account-classification/modals/*.html` | 分类/规则模态均应有 `crud-modal__header` 与状态提示。 |

若新增页面也使用 CRUD 模态组件，务必同时引入样式文件并按照上述结构构建 header，以避免出现“只有标题栏、缺少状态提示”的旧样式。

---

按照以上流程执行，可在最短时间内完成一次标准化的版本同步，同时避免维护噪音。
