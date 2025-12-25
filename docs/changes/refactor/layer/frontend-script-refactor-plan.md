# 前端脚本分层重构总计划（Service → Store → View）

> 状态：Draft  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：`app/static/js/` 前端分层与页面脚本瘦身

## 1. 目标

- 将页面脚本逐步收敛为“入口 glue + 组件 + Store”，避免千行脚本长期不可维护。
- 形成稳定的分层边界：
  - Service：只做 API 调用与序列化
  - Store：承载业务状态与 actions
  - View：只做 DOM 渲染与交互绑定

## 2. 单一真源（SSOT）

本计划不重复列清单，清单以以下文档为准：

- S0（服务层）清单：`service-layer-inventory.md`
- S1（状态层）清单：`state-layer-inventory.md`
- S2（视图层）清单：`view-layer-inventory.md`
- UI 组件化推进：`ui-componentization-plan.md`

## 3. 进度记录规范

- 每次完成一个领域/页面迁移：
  1. 在对应清单中更新 ✅/🔄 状态
  2. 在本文件追加一条“进度记录”（含日期、范围、PR、验证）

### 进度记录（追加写）

- 2025-12-25：初始化文档结构与迁移路径；补齐计划入口与索引（无代码行为变更）。

## 4. 质量门禁

- 页面迁移必须通过：`make quality`（必要时补单测/回归说明）。
- 命名与路径变更必须通过：`./scripts/refactor_naming.sh --dry-run`。
