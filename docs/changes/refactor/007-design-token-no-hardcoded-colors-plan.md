# Design Token No-Hardcoded-Colors Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: `app/static/css/**`, `scripts/ci/**`, `.github/**`, `docs/standards/ui/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P1-06), `docs/standards/ui/color-guidelines.md`, `docs/standards/ui/design-token-governance-guidelines.md`, `scripts/ci/css-token-guard.sh`, `.github/pull_request_template.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** No page/component CSS hardcodes colors(e.g. `white`, HEX, RGB). All color usage must come from design tokens(`var(--*)`) or approved external tokens(e.g. `--bs-*`). Token definition files remain the only place that can contain raw color literals.

**Architecture:** Split "token definition" and "token usage". Enforce with a static guard that scans non-token CSS files for hardcoded colors, plus standards + PR workflow to prevent regressions.

**Tech Stack:** CSS variables(`variables.css`), theme overrides(`theme-*.css`), ripgrep-based CI guard scripts.

---

## 1. 动机与范围

### 1.1 动机

- 审计报告(P1-06)指出: `app/static/css/pages/auth/change-password.css` 出现 `background: white;`, 破坏设计 Token 约束, 带来主题一致性与未来扩展(如暗色模式)风险.
- 现有标准已经声明"禁止硬编码 HEX/RGB/RGBA"(见 `docs/standards/ui/color-guidelines.md`), 但缺少对颜色关键字(例如 `white`)的门禁, 且 PR 模板引用的 `scripts/audit_colors.py` 并不存在, 导致治理缺口长期存在.

### 1.2 范围

In-scope:

- `app/static/css/**` 中除 token 定义文件外的所有 CSS: 禁止硬编码颜色关键字/HEX/RGB/RGBA(可扩展到 HSL/HSLA).
- 补齐门禁脚本并纳入协作入口(标准 + PR template).

Out-of-scope(本次不做):

- 重做现有 token 命名体系或引入完整主题系统.
- 一次性清理全站所有历史色彩问题(优先覆盖审计证据点与新增改动).

---

## 2. 不变约束(行为/视觉/性能门槛)

- 行为不变: 仅替换颜色来源为 token, 不改变布局/交互逻辑.
- 视觉不变: 在当前主题下, 替换后的颜色效果与原值一致或等价(例如 `white` -> `var(--surface-elevated)`).
- 性能门槛: 不引入额外运行时依赖, 不增加页面首屏资源体积.

---

## 3. 分层边界(依赖方向/允许与禁止)

### 3.1 Token 定义层(允许 raw color literals)

允许出现 raw color 的文件(建议固定 allowlist):

- `app/static/css/variables.css`
- `app/static/css/theme-*.css`

这些文件可以使用 HEX/RGB 等字面量定义 token, 其余 CSS 文件只能消费 token.

### 3.2 Token 使用层(禁止 raw color literals)

除 3.1 allowlist 以外的 CSS 文件:

- MUST: 使用 `var(--*)` 或允许的外部 token(`--bs-*`).
- MUST NOT: 出现颜色关键字(例如 `white`/`black`)或 HEX/RGB/RGBA 字面量.
- MAY: 使用 `transparent`, `currentColor`, `inherit` 等非色值字面量(需要在门禁规则中显式允许).

---

## 4. 方案选项(2-3 个)与推荐

### Option A(推荐): ripgrep 静态门禁 + allowlist

做法:

- 新增 `scripts/ci/css-color-hardcode-guard.sh`, 扫描 `app/static/css/**` 中非 allowlist 文件.
- 规则:
  - 禁止 `:\s*white\b` 等颜色关键字(至少覆盖 `white`, 可逐步扩展).
  - 禁止 `:\s*#[0-9a-fA-F]{3,8}\b`(仅在 declaration 中匹配, 避免 selector `#id` 误报).
  - 禁止 `:\s*(rgb|rgba)\(`.
- 允许:
  - `var(--*)`, `var(--bs-*)`, `transparent`, `currentColor` 等.

优点:

- 与现有门禁体系一致(参考 `scripts/ci/css-token-guard.sh`), 落地成本低.
- 可快速覆盖 P1-06 并防止回归.

缺点:

- Regex 方案存在误报/漏报风险, 需要逐步迭代 allow/deny 规则.

### Option B: 引入 stylelint(长期质量更高)

做法:

- 引入 stylelint + 自定义规则, 对 color 值进行语义级检查.

优点:

- 检查更准确, 可配置更细粒度的属性与上下文.

缺点:

- 引入新依赖与配置成本较高, 与当前仓库 "轻量 shell guard" 风格不一致.

推荐结论:

- Phase 1 采用 Option A 先补齐治理缺口.
- Phase 2 如遇到大量误报/漏报, 再评估 Option B.

---

## 5. 分阶段计划(中期 + 长期)

### Phase 1(中期): 修复证据点 + 建立最小门禁(建议 0.5-2 天)

验收口径:

- `app/static/css/pages/auth/change-password.css` 不再出现 `background: white;`, 改为使用 surface token.
- 新增门禁脚本在本地/CI 可运行, 且能阻断新增 hardcoded colors.
- PR 模板与实际脚本对齐, 避免"写了但跑不了".

实施步骤:

1. 修复 P1-06 证据点:
   - `background: white;` -> `background: var(--surface-elevated);`(或团队确认的等价 token).
2. 新增门禁:
   - `scripts/ci/css-color-hardcode-guard.sh`
   - 默认 deny: `white` + HEX + RGB/RGBA(先覆盖最常见).
   - 默认 allow: `variables.css`/`theme-*.css` 内允许 raw color.
3. 更新协作入口:
   - 修正 `.github/pull_request_template.md` 中不存在的 `scripts/audit_colors.py` 引用, 改为指向新门禁脚本(或新增等价脚本路径).

### Phase 2(长期): 扩展覆盖面 + 标准化 + 退场机制(建议 1-2 周)

验收口径:

- `docs/standards/ui/color-guidelines.md` 明确 "颜色关键字也属于硬编码" 并给出门禁脚本入口.
- 门禁规则对实际代码的误报率可控, 且 allowlist 有明确退场机制.
- 逐步覆盖 JS/template 的颜色硬编码风险点(如存在).

实施步骤:

1. 标准补齐:
   - 更新 `docs/standards/ui/color-guidelines.md` 的禁止项, 将 color keyword(例如 `white`)纳入 hardcode 范畴.
   - 在标准中明确 allowlist 文件与例外值(`transparent`/`currentColor`).
2. 门禁增强:
   - 扩展 deny list: `black`/`red` 等常见关键字, 以及 `hsl/hsla`(按实际使用情况).
   - 扩展扫描范围(可选): `app/templates/**` 的 inline style, `app/static/js/**` 中的 style 赋值, 强制使用 `ColorTokens`/token.
3. 退场机制:
   - 若门禁需要临时 allowlist 某些文件/行, 必须记录到 `007-design-token-no-hardcoded-colors-progress.md` 并给出清理 deadline.

---

## 6. 风险与回滚

风险:

- Regex 误报: 例如合法的 `#id` selector, 需要确保门禁只在 declaration(`:` 后)匹配.
- Token 选择不一致: `white` 替换为哪个 token 需要统一口径(建议 surface token 的层级语义优先).

回滚:

- Phase 1 的替换属于样式层变更, 可按 PR 回退.
- 门禁若影响存量合并, 可先以 warn 模式运行并输出命中清单, 再逐步收紧为 fail.

---

## 7. 验证与门禁

手工验证:

- 打开修改密码页, 对比替换前后卡片背景是否仍符合主题一致性.

静态检查(建议命令):

- `rg -n \"background:\\s*white\\b\" app/static/css`
- `./scripts/ci/css-color-hardcode-guard.sh`
- `./scripts/ci/css-token-guard.sh`

---

## 8. 清理计划

- Phase 1 完成后: 先确保新增改动全部通过门禁, 再逐步清理历史遗留命中点.
- Phase 2 完成后: 将临时 allowlist 收敛为最小集合(仅 token 定义文件).

---

## 9. Open Questions(需要确认)

1. `white` 的语义替换应统一为 `--surface-elevated` 还是 `--surface-default`?
2. 是否需要在门禁中同时覆盖 `hsl/hsla` 与更多颜色关键字, 还是按实际命中逐步扩展?
