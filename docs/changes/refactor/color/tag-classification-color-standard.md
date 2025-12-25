# 标签与账户分类色彩重构方案

## 背景
- 标签（`app/models/tag.py` + `instances.tags`）与账户分类（`app/models/account_classification.py`）允许用户自定义颜色，但实际使用中出现大量 HEX/RGB 颜色，导致页面视觉噪声，与《界面色彩与视觉疲劳控制指南》（`docs/standards/ui/color-guidelines.md`）“禁止硬编码颜色、语义色 ≤4”冲突。
- 账户台账页面已经升级为中性色芯片，但底层数据仍存储用户自定义颜色；后续当需要在图表、报表或第三方导出中展示标签时，仍可能恢复为五花八门的色块。

## 目标
1. 统一标签/分类颜色来源，全部映射到 `app/static/css/variables.css` 或 ColorTokens 的有限集合。
2. 保留用户“类型”配置自由（例如生产/测试/地域），但颜色只允许从预设调色板中选取，避免硬编码。
3. 提供数据迁移方案，将现有自定义颜色安全回收。

## 设计策略
### 1. 定义核心色盘
- 在 `variables.css` 中追加 `--tag-color-*`、`--classification-color-*` 系列，基于品牌主色 + 3 个语义色 + 2 个中性色，总计 6 种。
- 同时提供“浅底 + 描边”组合：CSS 中通过 `color-mix` 自动生成背景，避免重复写 HEX。

### 2. 数据层约束
- 新增 `tag_color_token`、`classification_color_token` 字段，或复用现有 `color` 字段但限制取值为 token key（如 `primary`, `success`, `muted`）。
- 后端校验：
  - API (`/tags/api/create`/`edit`、`/accounts/api/classifications/*`) 验证 `color` 是否在白名单。
  - 若前端传入 HEX，则直接拒绝并提示“请从色盘中选择”。

### 3. 前端交互
- 标签/分类表单中的颜色选择器改为固定下拉/色板，展示 Token 名称与用途说明（如“success：表示正常、通过”）。
- Grid 渲染层不再读取 `color` 字段的实际值，而是根据 token 名构建 class ：`chip-outline--brand`、`chip-outline--info` 等，由 CSS 控制最终颜色。

## 实施步骤
1. **定义色盘**
   - 更新 `app/static/css/variables.css` 并补充 `docs/standards/ui/color-guidelines.md` 的“引用示例”章节。
2. **数据迁移**
   - 创建 Alembic 迁移脚本：为标签/分类表增加 `color_token` 字段，并在迁移中根据现有颜色映射到最接近的 token（可使用简单的 RGB 距离算法或人工映射表）。
   - 迁移完成后将旧 `color` 字段保留 1~2 个版本以做兼容，但前端不再使用。
3. **后端校验**
   - 在 `app/routes/tags/api.py`、`app/routes/accounts/classifications.py` 等接口内增加校验逻辑，使用统一工具函数 `validate_color_token(token, domain)`。
4. **前端改造**
   - 标签/分类 modal 表单加载统一色盘（可引入 `ColorTokenPicker` 组件）。
   - Grid 渲染函数（例如 `renderTags`、`renderClassifications`）根据 `color_token` 输出类名，不再拼接 `style="background-color: ..."`。
5. **清理资产**
   - 搜索 CSS/JS/HTML 中 `#`、`rgb(` 等硬编码颜色，确保标签/分类相关部分全部移除。
6. **验证**
   - 手工验证：创建/编辑不同颜色标签，确认页面 chip 与色盘保持一致。
   - 自动化：补充 API 层单元测试，断言非法颜色返回 400。

## 风险与缓解
- **历史数据映射不准确**：可在迁移脚本中将现有颜色按“最邻近”原则映射，同时生成报告列出无法自动识别的记录，供运营手工确认。
- **用户定制性下降**：在文档中解释“色彩统一”的可用性收益，并允许通过配置扩展色盘（例如在 `ColorTokens` JSON 中新增条目，并同步到变量文件）。
- **多端样式同步**：若移动端或外部报表也引用标签颜色，需要同步更新对应代码并共享同一 token 名称。

## 里程碑建议
| 阶段 | 内容 | 负责人 | 耗时 |
| --- | --- | --- | --- |
| T+0 | 审核色盘方案，确定 token 列表 | UI/前端 | 0.5 天 |
| T+0.5 | 编写迁移脚本并生成映射报告 | 后端 | 1 天 |
| T+1.5 | 实现前后端校验与色盘选择器 | 前端/后端 | 1.5 天 |
| T+3 | QA 验证 + 回归（标签/分类 CRUD） | QA | 1 天 |
| T+4 | 发布并监控反馈，更新文档 | PM/UI | 0.5 天 |

## 文档与沟通
- 将本方案链接至 `docs/changes/refactor/color/accounts-ledger-color-refactor.md` 的“后续工作”章节，明确标签/分类配色统一是下一阶段目标。
- 在发表公告/变更日志时提醒用户：如需更多颜色，请通过工单申请，由设计统一扩展 token。
