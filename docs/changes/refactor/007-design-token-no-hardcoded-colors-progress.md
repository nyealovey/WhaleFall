# Design Token No-Hardcoded-Colors Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `007-design-token-no-hardcoded-colors-plan.md`
> 关联: `007-design-token-no-hardcoded-colors-plan.md`

关联方案: `007-design-token-no-hardcoded-colors-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `007-design-token-no-hardcoded-colors-plan.md`.

## 2. Checklist

### Phase 1(中期): 修复证据点 + 建立最小门禁

- [ ] 修复 `app/static/css/pages/auth/change-password.css` 的 `background: white;` 为 surface token
- [ ] 新增 `scripts/ci/css-color-hardcode-guard.sh`(deny: white/HEX/RGB/RGBA, allow: token definition files)
- [ ] 更新 `.github/pull_request_template.md` 的颜色审计项, 指向实际存在的脚本
- [ ] 手工回归: 修改密码页在默认主题下视觉一致

### Phase 2(长期): 扩展覆盖面 + 标准化 + 退场机制

- [ ] 更新 `docs/standards/ui/color-guidelines.md` 明确禁止颜色关键字, 补齐门禁入口
- [ ] 门禁扩展 deny list(black/hsl/hsla/更多关键字)并控制误报
- [ ] 评估并扩展扫描到 inline style/JS style 赋值(强制 token/ColorTokens)
- [ ] 建立临时 allowlist 的记录与清理 deadline

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P1-06 为入口推进 CSS hardcoded colors 治理.

