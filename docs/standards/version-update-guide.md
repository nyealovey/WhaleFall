# 版本更新与版本漂移控制

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-11-27  
> 更新：2025-12-25  
> 范围：发布版本号（`MAJOR.MINOR.PATCH`）更新、版本展示与版本漂移治理

## 目的

- 保证项目版本号在“运行时/构建配置/对外展示/部署资产”之间一致，避免版本漂移。
- 让版本更新变成可审查、可回滚、可快速验证的标准化动作。

## 适用范围

- 运行时版本：`app/settings.py` 的 `APP_VERSION`
- 构建/依赖：`pyproject.toml`、`uv.lock`
- 对外展示：模板页脚、Nginx 错误页、README 徽章、CHANGELOG
- 发布脚本与环境示例：`scripts/deploy/`、`env.example`

## 规则（MUST/SHOULD/MAY）

### 1) 版本号来源（单一真源）

- MUST：每次版本更新必须先修改 `app/settings.py` 中的 `APP_VERSION`，其作为运行时版本号来源。
- MUST：`pyproject.toml` 的 `[project].version` 与 `APP_VERSION` 保持一致。
- SHOULD：对外展示与脚本内出现的版本号字符串与 `APP_VERSION` 同步（见 2)）。

### 2) 必须更新的文件清单（最小集）

以下为“版本强一致”的最小覆盖集；如文件不存在则跳过该项，并在 PR 描述中说明原因。

| 更新项 | 文件/位置 | 说明 |
| --- | --- | --- |
| 运行时版本 | `app/settings.py`（`APP_VERSION`） | 运行时版本号唯一来源 |
| 项目配置 | `pyproject.toml`（`[project].version`） | 构建工具与依赖管理使用 |
| 运行环境示例 | `env.example`（`APP_VERSION`） | `.env` 示例基线 |
| 依赖锁 | `uv.lock`（`[[package]] name = "whalefalling"` 的 `version`） | 锁文件中的本项目版本 |
| 部署脚本 | `scripts/deploy/deploy-prod-all.sh` | 脚本输出/注释中的版本号 |
| API 元数据 | `app/routes/main.py`（`app_version`） | 健康检查/首页返回值 |
| 页脚展示 | `app/templates/base.html`（页脚） | 全站页面版本展示 |
| Nginx 错误页 | `nginx/error_pages/404.html`、`nginx/error_pages/50x.html` | 访客可见页面版本信息 |
| README | `README.md`（徽章/版本说明） | 外部访客识别最新版本 |
| CHANGELOG | `CHANGELOG.md`（新增条目） | 倒序记录：日期、主题、变化 |
| About 时间轴 | `app/templates/about.html` | 仅新增当前版本条目，不改历史条目 |

### 3) 版本更新时的“最小扰动”原则

- SHOULD：避免为了版本号而修改与本次发布无关的大文档（例如架构白皮书/评审报告）。如确有内容更新，需要在 PR 描述中说明“为什么必须同步改动”。
- MUST：不得把第三方依赖版本号（例如 `flask==...`）误替换为项目版本号。

## 正反例

### 正例：只改最小集并补齐验证

- 版本号替换仅落在“必需文件清单”与本次功能相关文件中。
- PR 描述包含：
  - 版本号从 `x.y.z` → `x.y.(z+1)` 的说明
  - 自检命令与结果（如 `ruff check`、`make typecheck`、`pytest -m unit`）

### 反例：全仓无差别替换

- 直接 `rg` 全仓替换导致大量 `docs/reports/*`、历史方案文档发生纯字符串变更，增加审核噪音。

## 门禁/检查方式

- 版本一致性自检（建议）：
  - `rg -n "<旧版本号>"`：确认改动只落在“必需文件清单 + 功能相关文件”
  - `./scripts/setup/validate-env.sh`：确认示例环境变量完整性（按需）
- 代码质量自检（按实际改动取子集）：
  - `make format`
  - `ruff check <paths>`
  - `make typecheck`
  - `pytest -m unit`

## 页面回归检查（建议）

版本发布前后建议做最小 UI 回归（按改动范围选择页面）：

- 登录/登出流程可用，页脚版本号与 `APP_VERSION` 一致。
- 列表页（使用 GridWrapper 的页面）：分页/排序/筛选正常、刷新不漂移、控制台无生产 `console.log`。
- 危险操作：确认弹窗可用、默认焦点在“取消”、能跳转到会话中心查看进度（如适用）。

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 重写为“版本漂移控制标准”，移除过期脚本引用与历史案例段落，补齐门禁与回归检查。
