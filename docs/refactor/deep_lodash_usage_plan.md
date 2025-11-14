# Lodash 深度使用改造计划

## 背景

项目已经引入 Lodash（通过 `LodashUtils` 封装）来处理 clone/merge/debounce 等常见需求，但在大量代码里仍存在手写的数组/对象/字符串操作。典型问题：

- 同一类逻辑重复实现（排序、去重、分组等），可读性差、易出错；
- 手写深拷贝/合并容易遗漏嵌套字段或破坏引用；
- 事件节流/防抖常用 `setTimeout` 手写实现，维护开销大；
- 多层可选值访问 (`obj?.foo?.bar`) 分布在各处，缺乏统一的默认值策略。

这些地方都可以用 Lodash 的成熟 API 替换，统一风格、提升可维护性。

## 改造范围

| 场景 | 典型文件 | 推荐 API |
| --- | --- | --- |
| 排序/分页 | `credentials/list.js`, `tags/index.js` 等 | `_.orderBy`, `_.sortBy`, `_.chunk` |
| 去重/集合运算 | 标签筛选、实例列表 | `_.uniq`, `_.uniqBy`, `_.difference`, `_.intersection` |
| 分组/统计 | 容量统计、日志分析 | `_.groupBy`, `_.countBy`, `_.mapValues` |
| 深拷贝/合并 | 各种配置对象 | `_.cloneDeep`, `_.merge` |
| 对象取值 | API 数据访问 | `_.get`, `_.has`, `_.set` |
| 节流/防抖 | 实时搜索、输入监听 | `_.throttle`, `_.debounce`（已部分使用） |

## 分阶段实施

### 阶段 1：排查与梳理
1. 搜索手写模式：
   ```bash
   rg "sort\(" app/static/js
   rg "new Set" app/static/js
   rg "JSON\.parse\(JSON\.stringify" app/static/js
   rg "\?.+\?" app/static/js
   ```
2. 将结果分类：排序、集合、深拷贝、链式取值等。

### 阶段 2：优先替换高风险/高重复场景
1. **排程表/列表排序**：统一改用 `LodashUtils.orderBy`，支持多字段排序。
2. **过滤去重**：标签/实例/账户的筛选数据使用 `LodashUtils.uniqBy`。
3. **深拷贝/合并**：所有 `Object.assign({}, obj)` 或 `{ ...obj }` 用 `LodashUtils.cloneDeep`/`merge` 替换。
4. **嵌套取值**：API 数据解析统一使用 `LodashUtils.get(data, 'path', default)`。

### 阶段 3：推广与规范
1. 在代码 review 模板中添加检查项：“如使用手写排序/去重/clone，请优先考虑 LodashUtils”。
2. 在 `docs/development/STYLE_GUIDE.md` 补充 Lodash 使用建议，列出常用场景与 API。
3. 对新模块要求优先使用 `LodashUtils`，减少 utils 或重复手写函数。

## 验收标准

- 手写的排序、去重、深拷贝代码基本消失，统一使用 `LodashUtils`。
- 事件节流/防抖统一调用 `LodashUtils.debounce/throttle`。
- API 数据访问统一使用 `LodashUtils.get` 提供默认值。
- 代码 review 时如出现手写逻辑，应能指出对应的 Lodash 替代方案。

## 风险与缓解

- **引入 Lodash 过多 API 导致包体积增加**：我们使用的是 vendor 版本，API 都在一个文件里，不存在 tree-shaking 问题；重点是统一调用方式而非额外引入。
- **团队成员对 Lodash API 不熟悉**：在文档里列出常用示例，必要时安排简短分享。
- **旧代码迁移冲击较大**：按模块逐步替换，优先在新/改的代码里使用，避免一次性大规模改动。

## 下一步
1. 完成本计划文档评审，确认范围。
2. 分配具体模块（如标签、实例、历史日志等）给对应开发者替换手写逻辑。
3. 改造完成后，在代码 review 中保持对 Lodash 使用的监督，确保不再回退到手写方式。
