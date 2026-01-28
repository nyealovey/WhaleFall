---
title: 版本更新 checklist
aliases:
  - version-update-checklist
tags:
  - reference
  - reference/development
status: active
created: 2026-01-09
updated: 2026-01-28
owner: WhaleFall Team
scope: 发布版本号更新时的执行清单(查阅型)与最小回归建议
related:
  - "[[standards/core/guide/version-update]]"
  - "[[standards/core/guide/git-workflow]]"
  - "[[standards/core/guide/testing]]"
---

# 版本更新 checklist

> [!important] 说明
> 本文是 checklist(面向执行与查阅), 不是 standards SSOT.
> 规则与门禁口径以 [[standards/core/guide/version-update]] 为准.

## 适用范围

- 发布版本号更新: `MAJOR.MINOR.PATCH`
- 需要确保运行时/构建/对外展示/部署资产之间不发生版本漂移

## 必须更新的文件清单(最小集)

> [!note] 说明
> 如文件不存在则跳过该项, 并在 PR 描述中说明原因.

| 更新项 | 文件/位置 | 说明 |
|---|---|---|
| 运行时版本 | `app/settings.py`(`APP_VERSION`) | 运行时版本号唯一来源 |
| 项目配置 | `pyproject.toml`(`[project].version`) | 构建工具与依赖管理使用 |
| 运行环境示例 | `env.example`(`APP_VERSION`) | `.env` 示例基线 |
| 依赖锁 | `uv.lock`(`[[package]] name = "whalefalling"` 的 `version`) | 锁文件中的本项目版本 |
| 部署脚本 | `scripts/deploy/deploy-prod-all.sh` | 脚本输出/注释中的版本号 |
| API 元数据 | `app/api/v1/__init__.py`(`WhaleFallApi.version`) · `app/api/v1/namespaces/health.py` | OpenAPI/健康检查返回值 |
| 页脚展示 | `app/templates/base.html` | 全站页面版本展示；年份使用 `current_year` 动态注入，无需手动改年份 |
| Nginx 错误页 | `nginx/error_pages/404.html`, `nginx/error_pages/50x.html` | 访客可见页面版本信息 |
| README | `README.md` | 外部访客识别最新版本 |
| CHANGELOG | `CHANGELOG.md` | 倒序记录: 日期/主题/变化 |
| About 时间轴 | `app/templates/about.html` | 仅新增当前版本条目, 不改历史条目 |

## 页面回归检查(建议)

- 登录/登出流程可用, 页脚版本号与 `APP_VERSION` 一致.
- 列表页(使用 GridWrapper 的页面): 分页/排序/筛选正常, 刷新不漂移, 控制台无生产 `console.log`.
- 危险操作: 确认弹窗可用, 默认焦点在"取消", 可跳转到会话中心查看进度(如适用).

> [!note] 关于页脚版本号一直不更新
> `APP_VERSION` 会从运行时环境变量/`.env` 中读取(如存在)，若部署机的 `.env` 未随版本更新同步修改，页脚/Swagger 可能仍显示旧版本。
> 建议发布时同步更新部署机 `.env` 中的 `APP_VERSION`，或删除该变量以回落到代码内置默认值。

## 自检命令(按改动取子集)

- `rg -n "<old_version>"`: 确认改动只落在"最小集 + 本次发布相关文件".
- `make format`
- `ruff check <paths>`
- `make typecheck`
- `pytest -m unit`

## 变更历史

- 2026-01-09: 从 `standards/version-update-guide` 拆出 checklist, 避免 standards 混入 runbook/checklist.
