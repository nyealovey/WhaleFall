# 022 frontend ui polish progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2026-01-04
> 更新: 2026-01-04
> 范围: `app/templates/**`, `app/static/css/**`
> 关联: `docs/changes/refactor/022-frontend-ui-polish-plan.md`

---

关联方案: `docs/changes/refactor/022-frontend-ui-polish-plan.md`

## 当前状态(摘要)

- Phase 3 决策已确定: A(全站启用 Inter).

## Checklist

### Phase 0: 基线与验收口径

- [x] 运行 UI 门禁并记录结果
- [x] 固定代表页面回归清单

### Phase 1: page header 描述渲染补齐

- [ ] 渲染 `description` 并回归主要页面

### Phase 2: 响应式基线修复(viewport + navbar toggler)

- [ ] 添加 viewport meta
- [ ] 添加 navbar toggler 并通过小屏回归

### Phase 3: 字体系统收敛

- [x] 决策: A(启用 Inter) 或 B(保留 system stack)
- [x] 收敛 font-family 单一真源
- [ ] 核心页面回归(Dashboard, Instances, Logs)

### Phase 4: chip 组件样式收敛

- [ ] 新增 `css/components/chips.css`
- [ ] 在 `base.html` 引入 chips
- [ ] 移除页面 CSS 内重复 chips 定义

### Phase 5: 动效收敛与 reduced motion 支持

- [ ] 收敛 `transition: all`
- [ ] 增加 `prefers-reduced-motion: reduce` 路径

### Phase 6: danger confirm modal 视觉语义强化

- [ ] 增加 `.danger-confirm-modal` scoped CSS
- [ ] 通过危险按钮语义门禁

## 变更记录

- 2026-01-04: 初始化 `plan` 与 `progress` 文档.
- 2026-01-04: Phase 3 决策确定为 A(全站启用 Inter).
- 2026-01-04: Phase 3 字体收敛: `--font-family-base` 以 Inter 优先, `body` 与 `--bs-body-font-family` 对齐.
- 2026-01-04: Phase 0 门禁通过: `css-token-guard`, `component-style-drift-guard`, `inline-px-style-guard`. 代表页面: Dashboard, Instances, Logs.
