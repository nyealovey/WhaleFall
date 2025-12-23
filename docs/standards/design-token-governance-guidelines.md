# 设计 Token 治理规范（CSS Variables）

## 目标
- 让全站颜色/圆角/阴影/间距等视觉基线可预测、可复用、可统一调整。
- 避免出现 `var(--xxx)` 未定义导致的样式回退（如圆角变直角、字体/阴影漂移）。

## 适用范围
- 全站 CSS：`app/static/css/**`
- 核心 token 文件：`app/static/css/variables.css`
- 主题覆盖（如有）：`app/static/css/theme-*.css`

## 规则
1) **全局 Token 必须集中定义**
- 全站复用的 token（`--surface-*`、`--text-*`、`--border-radius-*`、`--shadow-*`、`--spacing-*` 等）必须在 `app/static/css/variables.css` 定义。
- 页面 CSS / 组件 CSS 不得“临时发明”全局 token 名称；如确需局部变量，必须在同一作用域内定义（例如 `.component { --local-x: ... }`）。

2) **禁止引用未定义 Token**
- 任意 CSS 中出现 `var(--xxx)` 时，必须能在 `app/static/css/**` 内找到 `--xxx:` 的定义（外部库 token 例外，见下文）。
- 合并前必须通过门禁脚本 `scripts/code_review/css_token_guard.sh`。

3) **兼容别名必须显式标注**
- 若历史代码已使用旧 token 名（例如 `--surface-default`），可以在 `variables.css` 中以“别名”方式指向新 token：
  - 示例：`--surface-default: var(--surface-base);`
- 必须在定义旁用中文注释标明“兼容别名”，并在后续重构中逐步删除旧引用。

4) **外部库 Token（允许）**
- Bootstrap 等外部库的 token（例如 `--bs-*`）允许在本仓库 CSS 中直接引用。
- 若引入新的外部 token 前缀，需要同步更新门禁脚本的允许列表。

## 门禁
- 脚本：`scripts/code_review/css_token_guard.sh`
- 作用：扫描 `app/static/css/**`，发现 `var(--xxx)` 引用但没有任何 `--xxx:` 定义时阻断合并（默认忽略 `--bs-*`）。

## 落地建议
- 新增 token：先在 `variables.css` 补齐，再在页面/组件中引用；避免“先用后补”导致回退。
- 删除 token：先全仓搜索引用，确保 0 命中后再删除定义；必要时先做兼容别名过渡。
