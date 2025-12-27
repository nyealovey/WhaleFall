# Navbar Toggler(Desktop Narrow) Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `006-navbar-toggler-accessible-plan.md`
> 关联: `006-navbar-toggler-accessible-plan.md`

关联方案: `006-navbar-toggler-accessible-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `006-navbar-toggler-accessible-plan.md`.

## 2. Checklist

### Phase 1(中期): 可达性修复 + 桌面分屏回归

- [ ] 在 `app/templates/base.html` 增加 `navbar-toggler` 并关联 `#navbarNav`
- [ ] 补齐 `aria-controls/aria-expanded/aria-label`, 确保键盘可触发
- [ ] 如 toggler icon 不可见, 增加最小 CSS 兜底
- [ ] 手工回归: 900px 桌面分屏下可展开并可访问全部菜单项

### Phase 2(长期): 规范化 + 门禁 + 策略沉淀

- [ ] 新增 `docs/standards/ui/navbar-responsive-guidelines.md`
- [ ] 新增 `scripts/ci/navbar-toggler-guard.sh`
- [ ] `docs/standards/ui/README.md` 增加索引
- [ ] `.github/pull_request_template.md` 增加导航回归项
- [ ] 评估 Option B/C(断点调整/优先级菜单/overflow)并落地到独立变更

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P1-04 为入口推进 Navbar 桌面分屏可达性治理.

