## 凭据列表筛选/搜索 & 模态下拉异常修复记录

### 背景
- 2025-11：凭据列表页面完成 Grid.js 改造后，用户反馈「搜索和筛选完全无效」。
- 同时在新建/编辑凭据时，「数据库类型」下拉只有“请选择数据库类型”一项，看起来没有任何可选值。

### 现象
1. 在 `http://10.10.66.45/credentials/` 输入任意关键词或切换筛选项，列表不变。开发者工具中 `credentials/api/credentials` 请求始终只有 `sort/id/order/page/limit` 参数。
2. 新建/编辑模态里的 “数据库类型” 下拉展开后是空白项（无 MySQL、PostgreSQL 等）。

### 根因分析
| 问题 | 根本原因 |
| --- | --- |
| 筛选/搜索无效 | Grid.js 在触发分页/排序时向 `server.fetch` 传入 `Request` 对象，`GridWrapper.appendFilters()` 原先直接把此对象当字符串追加 query，导致 URL 变成 `"[object Request]"`，最终发起请求时完全丢失 `search/credential_type` 等参数。 |
| 数据库类型为空 | 模态模板使用了 `option.name` / `option.display_name`，而后端传给模板的数据字段为 `value` / `label`，字段名不匹配导致 `<option>` 的 value 和文本都是空字符串。 |

### 修复方案
1. **GridWrapper URL 归一化 + Fetch Hook**
   - `app/static/js/utils/grid-wrapper.js`
     - 新增 `normalizeUrlString()`，无论传入 `string`、`URL`、`Request` 还是自定义对象，都统一转换成普通 URL 字符串。
     - `appendFilters()` / `appendParam()` 先执行归一化，再按键值对 append。
     - `buildServerConfig().fetch()` 在真正触发 `fetch` 前调用 `appendFilters(finalUrl, currentFilters)`，确保即便 Grid.js 在内部重建 `Request`，最终发送的 URL 都携带最新筛选条件。

2. **数据库类型选项字段对齐**
   - `app/templates/credentials/modals/credential-modals.html` 中 `<option>` 改为 `value="{{ option.value }}"` / `{{ option.label }}`，与后端 `db_type_options` 保持一致。

3. **表单关闭触发新增的问题（之前修复）**
   - `credential-modals.js` 中 `resetForm()` 不再调用 `validator.revalidate()`，防止关闭模态时误触发提交。
   - 创建/编辑 API 指向真实存在的 `/credentials/api/create` 与 `/credentials/api/<id>/edit`。

### 验证步骤
1. `npm` 缓存/浏览器缓存清理后访问 `/credentials/`。
2. 输入 `mysql` → Network 中 `credentials/api/credentials?...&search=mysql`，表格显示 1 条记录。
3. 勾选不同筛选组合 → 请求 URL 包含对应参数，列表跟随刷新。
4. 点击 “添加凭据” → “数据库类型” 下拉显示 MySQL/PostgreSQL/SQL Server/Oracle 等选项；切换凭据类型为非数据库时该字段自动隐藏。
5. 点击任意凭据的“编辑”→ 关闭模态 → 不再出现 “添加凭据失败”；点击“保存”则请求 `/credentials/api/<id>/edit`。

### 发布注意事项
- 修改涉及公共组件 `GridWrapper`，其它使用该封装的页面（实例列表、日志、标签等）也获得相同的请求拼接能力，需回归至少一页确保筛选正常。
- 由于前端是纯静态资源，部署后请刷新 CDN/浏览器缓存，避免仍加载旧版 JS。
- 提交前执行仓库要求的 `./scripts/refactor_naming.sh --dry-run` 与 `make test`（如条件允许）。

### 后续建议
- 后续若 Grid.js 接入更多页面，优先依赖该通用封装，避免每个页面单独处理 URL 拼接。
- 模板中消费的选项数据统一使用 `value`/`label` 命名，减少未来类似字段对不上的问题。
