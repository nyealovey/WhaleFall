# 实例详情页面信息密度重构方案

## 背景
- 相关文件：`app/templates/instances/detail.html`、`app/static/js/modules/views/instances/detail.js`、`app/static/css/pages/instances/detail.css`。
- 页面顶部“实例详情”卡片与下方“基本信息”重复呈现实例名称、数据库类型、主机/端口、ID 等字段，造成占用空间、折返滚动与阅读成本。
- 运营与售前反馈截图（2025-12-02）表明用户只需在一个信息块中确认所有实例属性；当前布局在 1440px 桌面下仍有大面积留白，信息密度不足。

## 现状问题
1. **信息重复**：`instance-detail-header` 与 `基本信息` 区域字段 1:1 复制，标签/版本之外缺乏差异。
2. **关注点分散**：关键元数据（名称、主机、端口、ID、描述、最后连接/同步时间）被拆成三个容器，用户确认状态需多次视线跳转。
3. **卡片比重失衡**：顶部卡片高度接近 260px，但仅承载三行文本；下方 `col-8` 宽度内又重复相同内容，浪费屏幕资源。

## 重构目标
1. **单卡片承载全部实例属性**：将“实例详情”区域的内容合并到“基本信息”卡片，形成一份完整元数据表。
2. **保留标签与数据库版本**：原“基本信息”中的“数据库版本”“标签”以原组件样式保留，并与新字段采用统一网格。
3. **提高信息密度与可扫描性**：卡片内字段按业务分组（身份、连接、生命周期、状态、标签），避免重复标签、标题。
4. **不破坏既有脚本数据结构**：`InstanceDetailPage` 继续从 `window.INSTANCE_DETAIL` 读取，只调整模板结构与局部渲染钩子。

## 目标信息架构
| 分组 | 字段 | 说明 | 显示形式 |
| --- | --- | --- | --- |
| 身份 | 实例名称、数据库类型、实例 ID、描述 | 组合在卡片开头，名称+DB 类型行保留徽标，ID 以 `ledger-chip` 表示 | 左上区域，占据一整行 |
| 连接属性 | 主机地址、端口号、最后连接时间、连接状态（status pill） | 以 `col-md-6` 网格呈现 | `row` 1 |
| 同步与生命周期 | 上次同步时间、创建时间、更新时间 | `row` 2 |
| 标签 & 版本 | 标签栈、数据库主版本 + 详细版本/折叠信息 | 原逻辑迁入卡片底部两列 | `row` 3 |
| 补充 | 描述/备注、更多操作入口（optional link 到“连接测试”卡片） | 描述紧随身份信息 | 文本块 |

合并后“基本信息”卡片成为单一信息源，原顶部 `instance-detail-header` 被移除（或缩减为仅展示导航锚点），右侧“快速操作”卡片保持不变。

## 交互与视觉策略
- **标题保留**：卡片仍命名为“基本信息”，避免误解；顶部标签“实例详情”删除。
- **网格布局**：沿用现有 `row/col-6` 结构，新增 `col-12` 行用于名称/描述，整体高度<220px（无描述时）。
- **状态标识**：最后连接、上次同步使用 `status-pill`，连接状态 Pill 继续由 JS 更新 `#connectionStatus`。
- **标签/版本**：保持 chip 样式与折叠逻辑，文案不变，确保用户仍可展开完整版本信息。
- **辅助提示**：如实例缺少某字段，统一展示 `span.text-muted` 占位，杜绝空白格。

## 技术方案
### 模板调整
1. 删除 `instance-detail-header` 整体 `card`，将其 DOM 结构（名称、db_type、host、port、ID、描述、最后连接、上次同步）迁入 `基本信息 card-body`。
2. 重新组织 `card-body`：
   - 新增 `div.basic-info__identity` 承载标题区与描述。
   - 下面依次渲染两行 `row`，分别放置连接属性、生命周期字段；最底行保留“数据库版本”“标签”。
3. 将 `last_connected`、`updated_at` 显示复用 status-pill 结构，移除原 `detail-meta-block`。
4. 保留 `col-8/col-4` 布局，避免调动右侧列。

### JavaScript / 数据流
- `app/static/js/modules/views/instances/detail.js`：只需更新 `mountIdentityCard()`（若存在）或相关查询选择器，确保连接状态 pill DOM ID 不变，以免 `testConnection()` 写入失败。
- 若脚本依赖 `instance-detail-header__primary`、`__meta` 类名，需要提供兼容占位或同步更新选择器。

### 样式
- 删除 `instance-detail-header` 专用样式；在 `detail.css` 新增 `basic-info-card__identity`、`basic-info-card__chips` 等轻量 class，保证间距。
- 卡片内部不新增硬编码颜色，全部沿用 `variables.css` token。

## 实施步骤
1. **模板改造**
   - 编辑 `app/templates/instances/detail.html`，重构 `基本信息` 卡片结构并移除顶部卡片。
   - 调整字段顺序，确保标签、数据库版本保留。
2. **样式更新**
   - 清理 `app/static/css/pages/instances/detail.css` 中对 `instance-detail-header` 的定义；加入新布局所需的间距样式。
3. **脚本适配**
   - 检查 `detail.js` 中对被删除 DOM 的引用，更新查询选择器或增加新的 data attribute（如 `data-section="identity"`）。
4. **自检脚本**
   - 执行 `./scripts/refactor_naming.sh --dry-run`，确认无命名违规。
   - 运行 `make test` 或最少 `pytest -k "instances and detail"`，验证模板上下文渲染。
5. **人工验证**
   - `make dev start` + `make dev start-flask` 后访问 `/instances/<id>`，在 1440px 宽度下截图作为“前后对比”。

## 风险与缓解
- **脚本残留引用**：若 JS 继续查询旧 class，可能导致绑定失败；解决方案是在提交前搜索 `instance-detail-header` 相关引用，逐一替换。
- **信息拥挤**：所有字段集中后可能导致列过长，需确保 `col-md-6 col-12` 响应式设置并限制单行字符数，必要时利用 `text-break`。
- **可读性下降**：去掉顶部卡片后需通过 `fw-bold` 标签标题和灰色分隔线明确分组。

## 验证清单
- [ ] 页面只有一个承载基础信息的卡片，包含名称、ID、主机、端口、描述、最后连接、上次同步、创建/更新时间。
- [ ] “数据库版本”“标签”仍在卡片底部，以 chip + details 呈现。
- [ ] `status-pill` 组件在最后连接、连接状态、上次同步字段中渲染正常。
- [ ] `testConnection()` 触发后 `#connectionStatus` pill 状态可正常刷新。
- [ ] Lighthouse/手动对比确认首屏高度减少 ≥120px，信息一次可见。

## 时间安排
- D0（准备）：评审本方案、确认交互稿。
- D1（开发）：完成模板/JS/样式改造与本地验证。
- D2（联调）：与后端确认 `INSTANCE_DETAIL` 数据完整，补充回归测试、截图入库。
- D3（验收）：提交 PR、运行 `make quality`、补充文档并通知产品验收。

## 后续行动
- 若用户仍需“最后连接时间”在页眉展示，可考虑在 `breadcrumbs` 旁新增状态图标而非完整卡片。
- 将该布局模式沉淀为 `components/cards/basic_info.html`，供凭据详情、账户详情复用。

