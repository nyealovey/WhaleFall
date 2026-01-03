# Timezone Display and Configuration Refactor Progress

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 同 `011-timezone-display-and-config-plan.md`
> 关联: `011-timezone-display-and-config-plan.md`

关联方案: `011-timezone-display-and-config-plan.md`

---

## 1. 当前状态(摘要)

- 尚未开始落地.
- 目标与方案见 `011-timezone-display-and-config-plan.md`.

## 2. Checklist

### Phase 1: Single source of truth + time zone badge

- [ ] 后端增加 display timezone 配置项(默认 `Asia/Shanghai`)
- [ ] 在 `base.html` 注入 display timezone 给前端
- [ ] `timeUtils` 支持读取配置并输出 timezone label
- [ ] 会话中心/日志中心/详情面板增加 timezone badge

### Phase 2: 用户设置支持切换 display timezone

- [ ] 用户设置页增加显示时区选项(至少支持 `Asia/Shanghai`/`UTC`/`browser local`)
- [ ] display timezone 切换后全站生效且一致
- [ ] UI 总是显示当前 timezone label(避免歧义)

### Phase 3: UI 标准 + 回归策略

- [ ] 新增 `docs/standards/ui/time-display-guidelines.md`
- [ ] `docs/standards/ui/README.md` 增加索引
- [ ] 评估并落地门禁或 code review checklist, 防止新增页面时间无时区标识

## 3. 变更记录

- 2025-12-27: 初始化 plan/progress 文档, 以 P2-04 为入口推进时间展示时区显式化治理.
