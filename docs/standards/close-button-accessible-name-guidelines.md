# 关闭按钮（btn-close）可访问名称规范

## 目标
1. 全站所有关闭按钮都有可访问名称（Accessible Name），读屏能稳定朗读“关闭”。
2. 禁止中英文混用（例如 `aria-label="Close"`），避免读屏语言错乱与体验割裂。
3. 关闭按钮渲染统一，避免模板/脚本手写导致漏标与回归。

## 适用范围
- Bootstrap `btn-close`（Alert/Modal/Toast 的关闭按钮）。
- 任何“仅图标/无文本”的关闭交互（优先使用 `btn-close`）。

## 规范要求
### 1) 可访问名称必须为中文
- 统一使用：`aria-label="关闭"`。
- 禁止使用：`aria-label="Close"` 或其他英文。

### 2) 组件一致性
- Alert：所有可关闭提示必须包含 `btn-close` 且带 `aria-label`。
- Modal：关闭按钮必须来自统一模板（避免手写）。
- Toast：关闭按钮由统一 JS helper 生成，且带 `aria-label`。

## 实现落点（统一渲染）
- 模板宏：`app/templates/components/ui/macros.html` 的 `btn_close(...)`。
- 通用模态：`app/templates/components/ui/modal.html` 使用 `btn_close(...)` 输出关闭按钮。
- 全站门禁：`scripts/code_review/btn_close_aria_guard.sh`（禁止缺失 aria-label 或英文 Close）。

## 自检与验收
- 读屏：聚焦任意关闭按钮，必须朗读“关闭”。
- 静态扫描：运行 `./scripts/code_review/btn_close_aria_guard.sh` 必须通过。

