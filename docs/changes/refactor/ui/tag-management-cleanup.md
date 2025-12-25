# 标签管理重构方案：移除颜色/排序并支持父分类

## 背景
- 标签新增/编辑表单长期保留“颜色”“排序”字段，但前台从未展示颜色差异，也不会按排序值渲染；该特性既占用表单空间，又增加命名脚本与后台校验复杂度。
- 标签分类为单层结构，无法表达“业务域 / 子模块”一类的层级。随着标签数量增长，缺乏父类信息导致筛选器和统计页难以按域归组。
- 需要一次性清理冗余字段，并为分类新增父类能力，确保 UI/接口/数据库一致，且可无痛迁移已有数据。

## 目标与范围
1. **彻底移除颜色功能**：删除颜色选择器、色板预览、后端 `color` 字段与常量，标签展示统一由分类/文本决定。
2. **彻底移除排序功能**：删除“排序”输入框与相关数据库字段，标签默认按“创建时间倒序 + 标签名称”排序。
3. **分类支持父类**：`tag_categories` 新增 `parent_id` 自关联字段，API & UI 可读取并编辑父类，默认仅允许两级结构。
4. **更新文档/脚本**：同步更新 API 说明、命名规范、基线脚本、单元测试，确保 `./scripts/refactor_naming.sh --dry-run`、`make quality` 通过。

## 数据模型调整
| 表/实体 | 变更内容 | 迁移策略 |
| --- | --- | --- |
| `tags` | 删除 `color`, `sort_order` 列（具体列名以 Alembic 迁移确认） | 迁移前导出影子表以备回滚；迁移中 `DROP COLUMN`，无需数据回填 |
| `tag_categories` | 新增 `parent_id`（`NULL` 允许，FK 指向 `tag_categories.id`，建立 B-Tree 索引） | 默认值 `NULL`，如需初始化层级，另写数据脚本 |
| 依赖视图/物化视图 | 若 `tags_view` / `tag_stats_view` 包含旧列需同步删除 | 与主迁移同一事务执行 |

> 注意：迁移前需搜 `color`/`sort_order` 关键字，确认无触发器、BI 查询或外部脚本依赖；若存在需提前调整。

## 后端改造
1. **ORM / Schema / Form**
   - 移除 `Tag.color`, `Tag.sort_order` 字段，删除对应校验常量。
   - `TagCategory` 模型新增 `parent_id`，并提供 `relationship('parent')` / `relationship('children', remote_side=[id])`。
   - Schema/Form 删除颜色/排序字段，新增 `parent_id`（可空）校验。
2. **Service & API**
   - `TagService.create/update`：只接受 `name`, `display_name`, `category_id`, `description`, `is_active`。删除颜色/排序相关逻辑。
   - `TagCategoryService`：保存时校验 `parent_id` 合法（不可指向自身，禁止环，默认两级）。暴露 `list_tree` 接口方便前端展示。
   - API 响应中删除颜色/排序字段，补充 `parent_id`、`parent_name`。
3. **脚本与基线数据**
   - 更新基线脚本、测试夹具、Admin 种子数据，去除颜色/排序字段，并新增示例父/子分类。

## 前端改造
1. **标签模态 (`app/templates/tags/modals/tag-modals.html`)**
   - 删除颜色选择器、示例徽章。
   - 删除排序输入框、相关提示文案。
   - 在分类字段下显示父类信息（例如“所属父类：平台 / 数据同步”）。
2. **分类管理页面 (`app/templates/tags/categories.html` 等)**
   - 新增父类下拉框，默认“无父级”。
   - 列表页新增 `父类` 列，若为顶级显示 `—`。
3. **JS 模块**
   - `js/modules/views/tags/modals/tag-modals.js`：移除 color/sort payload，新增 `parentCategorySelect` 赋值。
   - 分类 JS 同步处理 `parent_id` 读取/写入。
4. **UI 统一**
   - 标签列表、筛选器、标签选择器不再引用颜色字段；若之前在样式中根据 `data-color` 设置 class，需清理。

## 父类能力与初始建议
- 推荐预设三个顶级父类，便于后续扩展：
  | 父类代码 | 中文名称 | 用途 |
  | --- | --- | --- |
  | `infra_domain` | 基础设施域 | 管理与服务器、环境、架构、虚拟化、部署方式等相关的标签 |
  | `org_domain` | 组织角色域 | 管理部门、公司类型、项目组等内部组织结构标签 |
  | `external_domain` | 外部域 | 存放来自 AD/LDAP 等外部系统同步的人员标签，便于实例/凭据与人员身份做关联 |
  - `external_domain` 的子分类建议与 AD 分组保持一致（如 `ad_users`, `ad_groups`），同步任务只需写入该父类下的子分类即可。

### 能力约束
- `parent_id` 可空，仅允许两级：若父类还有父类则驳回保存（后端/JS 均提示）。
- 删除父分类前需保证无子分类；如需批量删除需另开需求。
- 前端下拉框按“父类 / 子类”展示，可使用树形数据或 `optgroup`。

## 迁移与上线步骤
1. **准备阶段**
   - 编写 Alembic 迁移：`drop color/sort_order`, `add parent_id` + 索引 + FK。
   - 本地执行 `make migrate && make test` 确认。
2. **实现阶段**
   - 后端与前端同步开发，先在 feature 分支完成并跑通单元测试。
   - 更新 `docs/standards/tag_guidelines.md`、API 文档。
3. **验证阶段**
   - Staging 数据库执行迁移，手工创建父/子分类、标签，验证 CRUD。
   - UI 走查：新增/编辑标签、标签列表、筛选器、实例/凭据标签选择器。
4. **发布 & 回滚**
   - 发布前备份 `tags`、`tag_categories` 数据。
   - 回滚时使用备份表还原并反向执行 Alembic 迁移。

## QA 检查单
- [ ] 迁移后的 `tags` 表中无 `color/sort_order` 列。
- [ ] `tag_categories.parent_id` 可正常写入/修改、自循环被拒绝。
- [ ] 标签模态中启用开关默认勾选，无颜色/排序控件。
- [ ] 分类列表、筛选器等处未引用颜色样式。
- [ ] `POST /tags`、`PATCH /tags/:id` 对旧字段返回 400，防止遗留前端调用。
- [ ] `tags` 相关单元测试/集成测试覆盖新增父类场景。

## 依赖更新
- `scripts/refactor_naming.sh`：去除颜色/排序字段的检查逻辑。
- `docs/changes/refactor/ui/filter-card-single-row.md`：若提及标签颜色需同步删除。
- 监控指标/BI 看板若引用颜色列需协调下线。

> 完成后请在 PR 中附上“重构前/后”模态截图、迁移 SQL 输出、`make quality` 日志，并同步通知使用标签 API 的业务方。 
