# btn-icon Accessible Name(aria-label) Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `005-btn-icon-accessible-name-plan.md`
> 关联: `005-btn-icon-accessible-name-plan.md`

关联方案: `005-btn-icon-accessible-name-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `005-btn-icon-accessible-name-plan.md`.

## 2. Checklist

### Phase 1(中期): 统一产出能力 + 批量迁移

- [ ] 盘点 `.btn-icon` 存量点位, 明确需覆盖的页面清单
- [ ] 新增模板宏 `btn_icon(...)` 并完成 1-2 个模板页试点迁移
- [ ] 新增 JS helper `renderIconButtonHtml(...)` 并完成 1 个列表模块试点迁移
- [ ] 迁移审计证据点:
  - [ ] `app/static/js/modules/views/instances/list.js`(查看详情/测试连接)
  - [ ] `app/static/js/modules/views/credentials/list.js`(编辑/删除)
  - [ ] `app/templates/history/sessions/detail.html`(复制会话 ID)
- [ ] 全站迁移剩余 `.btn-icon` 与装饰 icon 的 `aria-hidden`
- [ ] 键盘 Tab + 读屏抽检通过(按 plan 第 6 节)

### Phase 2(长期): 规范化 + 自动化门禁 + 回归机制

- [ ] 新增 `scripts/ci/btn-icon-aria-guard.sh`(允许 aria-label 或 aria-labelledby)
- [ ] 将门禁纳入 CI/本地检查链路
- [ ] 新增标准文档 `docs/standards/ui/icon-button-accessible-name-guidelines.md`
- [ ] `docs/standards/ui/README.md` 增加索引
- [ ] `.github/pull_request_template.md` 增加 a11y checklist(至少覆盖 btn-icon)
- [ ] 评估并落地 `axe` 自动化扫描方案(如现有测试栈允许)

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P1-03 为入口推进 btn-icon accessible name 治理.

