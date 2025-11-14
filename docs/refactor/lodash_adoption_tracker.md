# Lodash Adoption Tracker

> 记录每次将手写排序/去重/深拷贝/取值等逻辑迁移到 `LodashUtils` 的改造，便于周会复盘与覆盖率度量。

## 维护规则

- 每次提交涉及 Lodash 改造时，新增一行记录，并在 `Summary` 字段中简要说明触发场景与收益。
- `Patterns Replaced` 建议使用逗号列出（例如 `Array.sort`, `setTimeout debounce`, `JSON.parse(JSON.stringify)`）。
- 若同一模块多次迭代，可追加多行并注明阶段，方便统计完成度。

| Date       | Module/Path                                        | Patterns Replaced                                   | Lodash APIs Used                                               | Status  | Summary |
| ---------- | -------------------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------- | ------- | ------- |
| 2024-05-07 | `app/static/js/pages/credentials/list.js`          | `Array.sort`, `setTimeout` 防抖，字符串判空         | `orderBy`, `safeGet`, `debounce`, `compact`, `toLower`         | ✅ 已上线 | 列表排序/搜索统一通过 LodashUtils，搜索输入支持 flush/cancel，避免内存泄漏 |
| 2024-05-07 | `app/static/js/pages/tags/batch_assign.js`         | 分组排序、多次 `find`/`map` 查找                    | `groupBy`, `orderBy`, `keyBy`, `safeGet`, `uniq`, `toLower`    | ✅ 已上线 | 标签/实例分组、选择摘要等逻辑全部使用 LodashUtils，减少重复遍历 |
| 2024-05-07 | `app/static/js/pages/instances/detail.js`          | `Array.sort`（按容量排序）                          | `orderBy`                                                      | ✅ 已上线 | 数据库容量表按大小降序渲染，统一排序实现 |
| 2024-05-07 | `app/static/js/pages/admin/aggregations_chart.js`  | `Object.keys().sort`, `Set + forEach` 去重          | `sortBy`, `flatMap`, `uniq`, `compact`                         | ✅ 已上线 | 图表日期与数据集来源统一用 Lodash 排序/去重，避免手动集合代码 |
| 2024-05-07 | `app/static/js/common/capacity_stats/transformers.js` | `Array.from().sort`, 手写 TopN 排序                 | `sortBy`, `orderBy`                                            | ✅ 已上线 | 各类容量图表的时间轴与 TopN 选择全部使用 Lodash，保持一致性 |
| 2024-05-07 | `app/static/js/common/capacity_stats/manager.js`   | `Array.sort` + `localeCompare`                      | `orderBy`                                                      | ✅ 已上线 | 数据库下拉选项按名称统一排序，避免多处 `localeCompare` |
| 2024-05-07 | `app/static/js/pages/instances/statistics.js`      | 手写分组、双重循环构建标签/数据集                   | `groupBy`, `flatMap`, `orderBy`                                | ✅ 已上线 | 版本统计图表按 DB 类型 + 版本稳定排序，颜色/数据整理统一通过 LodashUtils |
| 2024-05-07 | `app/static/js/pages/dashboard/overview.js`        | 多次 `Array.map` + 判空                              | `get`, `map`, `safeGet`                                        | ✅ 已上线 | 仪表板日志趋势图统一通过 LodashUtils 取数，避免空值导致的错位 |
| 2024-05-07 | `app/static/js/pages/history/logs.js`              | 模块列表排序/去重、筛选参数构建                       | `compact`, `uniq`, `orderBy`                                   | ✅ 已上线 | 模块筛选名单及查询参数统一用 LodashUtils，减少重复 DOM 读取和排序 |
| 2024-05-07 | `app/static/js/pages/accounts/list.js`             | Tag 选择初始值与筛选参数手工拼接                       | `compact`, `orderBy`                                           | ✅ 已上线 | 账户 Tag 过滤初始化与参数构建改用 LodashUtils，避免空值/重复项 |
| 2024-05-07 | `app/static/js/pages/tags/index.js`                | 筛选参数拼接、导出参数复用                               | `compact`                                                      | ✅ 已上线 | 标签筛选与导出共享 Lodash 化的参数清洗逻辑，消除重复 DOM 读取 |
| 2024-05-07 | `app/static/js/pages/instances/list.js`            | Tag 初始值解析、筛选参数构建                             | `compact`                                                      | ✅ 已上线 | 实例筛选表单与导出统一用 LodashUtils 清洗/拼装参数，避免空值 |
| 2024-05-07 | `app/static/js/pages/history/sync_sessions.js`     | 会话筛选参数构建、查询字符串拼接                         | `compact`                                                      | ✅ 已上线 | 同步会话筛选/分页统一用 LodashUtils 构建 URL 参数，去除手写逻辑 |
| 2024-05-07 | `app/static/js/pages/credentials/list.js`          | 筛选参数构建、搜索词判空                                 | `compact`                                                      | ✅ 已上线 | 凭据筛选与查询 URL 经 LodashUtils 清洗，统一校验搜索关键字长度 |
| 2024-05-07 | `app/static/js/pages/history/logs.js`              | stats/搜索 URL 参数拼装                                   | `compact`                                                      | ✅ 已上线 | 日志统计与搜索请求统一走 Lodash 化参数构建，去掉重复拼接 |
| 2024-05-07 | `app/static/js/pages/history/logs.js`              | 搜索词高亮 RegExp 构建                                  | `escapeRegExp`                                                 | ✅ 已上线 | 搜索高亮使用 Lodash 的 `escapeRegExp`，避免特殊字符破坏正则 |
| 2024-05-07 | `app/static/js/pages/credentials/list.js`          | 导出参数拼接                                              | `compact`                                                      | ✅ 已上线 | 凭据导出复用筛选参数构建逻辑，避免直接使用 location.search |
| 2024-05-07 | `app/static/js/pages/admin/aggregations_chart.js`  | Chart 请求参数构建                                        | `compact`                                                      | ✅ 已上线 | 聚合图表使用统一的 Lodash 化 query builder，减少重复 URLSearchParams |
| 2024-05-07 | `app/static/js/pages/history/sync_sessions.js`     | 自动刷新防抖、筛选请求拼装                               | `compact`, `debounce`                                          | ✅ 已上线 | 同步会话自动刷新改用 Lodash 防抖，并复用 query builder 防止重复请求 |
