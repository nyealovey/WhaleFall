# Account Classification Refactor Progress

> Status: Draft
> Owner: WhaleFall Team
> Created: 2026-01-20
> Updated: 2026-01-20
> Related: `docs/plans/2026-01-20-account-classification-refactor.md`

## 当前状态(摘要)

- 当前阶段: 未开始
- 关键决策已确认:
  - 系统内置 6 类 code(全小写): `super`, `highly`, `sensitive`, `medium`, `low`, `public`
  - 数据库字段: `name` -> `code`, `display_name` 保持为展示名
  - 系统内置分类: 禁止删除/停用/隐藏, 仅允许修改 `display_name/description/priority`
  - 自定义分类: 可配置 `code/display_name/description/risk_level(1-6)/icon_name/priority`
  - 移除分类显示颜色

## Checklist(按 Phase)

### Phase 0: 约束与接口口径确认

- [x] 确认系统内置分类 code(全小写)
- [x] 确认系统内置分类不可停用/隐藏, 不考虑历史迁移
- [ ] 确认 risk_level 的对外 label(1-6)与默认值(建议默认 4)

### Phase 1: 后端类型/常量与 ORM 重构

- [ ] 更新 `RISK_LEVEL_OPTIONS` 为 1-6
- [ ] ORM: `account_classifications.name` 改为 `code`
- [ ] ORM: `risk_level` 改为 int(1-6)
- [ ] ORM: 删除 `color` 及相关派生字段/输出

### Phase 2: Service/Repository/Schema 约束落地

- [ ] 写路径: 系统内置分类仅允许更新 `display_name/description/priority`
- [ ] 写路径: 自定义分类允许更新 `display_name/description/priority/risk_level/icon_name`
- [ ] 读路径: 输出 `code/display_name`, 并在列表/详情包含 `code`
- [ ] 统计/台账: 移除分类颜色相关字段

### Phase 3: API Contract 调整

- [ ] 删除 `/api/v1/accounts/classifications/colors`
- [ ] RESTX models: `risk_level` -> int, 移除 `color/color_key`
- [ ] API payload: create/update 适配 `code/display_name` 口径
- [ ] 更新 unit contract tests

### Phase 4: 前端页面与校验规则

- [ ] 分类卡片展示 `code`
- [ ] 新建分类表单: 增加 `code` 输入(全小写)并校验
- [ ] 编辑系统内置分类: 禁用 risk/icon, 仅提交允许字段
- [ ] 移除颜色选择/颜色预览/颜色校验规则
- [ ] 风险等级 UI 支持 1-6

### Phase 5: DB Migration + 内置 6 类 seed

- [ ] Alembic: `name` -> `code`
- [ ] Alembic: `risk_level` varchar -> smallint(1-6)
- [ ] Alembic: drop `color`
- [ ] Alembic: upsert 6 条系统内置分类(code 固定)

### Phase 6: 全量验证

- [ ] `make format`
- [ ] `make typecheck`
- [ ] `uv run pytest -m unit`

## 变更记录(按日期追加)

### 2026-01-20

- 初始化 progress 文档, 记录已确认的系统内置分类 code 与核心约束.

