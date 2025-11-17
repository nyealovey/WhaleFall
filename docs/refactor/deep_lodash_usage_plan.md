# Lodash 深度使用改造计划

## 背景

项目已经引入 Lodash（通过 `LodashUtils` 封装）来处理 clone/merge/debounce 等常见需求，但在大量代码里仍存在手写的数组/对象/字符串操作。典型问题：

- 同一类逻辑重复实现（排序、去重、分组等），可读性差、易出错；
- 手写深拷贝/合并容易遗漏嵌套字段或破坏引用；
- 事件节流/防抖常用 `setTimeout` 手写实现，维护开销大；
- 多层可选值访问 (`obj?.foo?.bar`) 分布在各处，缺乏统一的默认值策略。

这些地方都可以用 Lodash 的成熟 API 替换，统一风格、提升可维护性。

### LodashUtils 组件使用准则

1. 所有 Lodash 调用一律通过 `LodashUtils` 暴露的包装层完成，禁止直接 `import _ from 'lodash'`，确保未来可替换实现（例如 `lodash-es` 或自研 util）。
2. `LodashUtils` 中的 API 命名与 Lodash 对齐，必要时可额外暴露带业务默认值的二次封装，例如 `safeGet(data, path, fallback='')` 用于表单组件。
3. 新增的 util 函数若能由 Lodash 组合完成（`flow`, `pipe`, `mapValues` 等），优先实现为 `LodashUtils` 的组合方法，而非在业务模块内散落自定义实现。
4. 在 TypeScript/现代前端模块中，利用泛型/类型收窄为 `LodashUtils` 补充类型提示，避免 `any` 扩散。

## 改造范围

| 场景 | 典型文件 | 推荐 API |
| --- | --- | --- |
| 排序/分页 | `credentials/list.js`, `tags/index.js` 等 | `_.orderBy`, `_.sortBy`, `_.chunk` |
| 去重/集合运算 | 标签筛选、实例列表 | `_.uniq`, `_.uniqBy`, `_.difference`, `_.intersection` |
| 分组/统计 | 容量统计、日志分析 | `_.groupBy`, `_.countBy`, `_.mapValues` |
| 深拷贝/合并 | 各种配置对象 | `_.cloneDeep`, `_.merge`, `_.defaultsDeep` |
| 对象取值 | API 数据访问 | `_.get`, `_.has`, `_.set`, `_.pick`, `_.omit` |
| 节流/防抖 | 实时搜索、输入监听 | `_.throttle`, `_.debounce`（已部分使用） |
| 数据整形 | 表格列构造、图表数据 | `_.map`, `_.flatMap`, `_.keyBy`, `_.flow` |
| 等值/变更检测 | 表单 diff、缓存命中 | `_.isEqual`, `_.isEmpty`, `_.isNil` |

## 分阶段实施

### 阶段 1：排查与梳理
1. 搜索手写模式：
   ```bash
   rg "sort\(" app/static/js
   rg "new Set" app/static/js
   rg "JSON\.parse\(JSON\.stringify" app/static/js
   rg "\?.+\?" app/static/js
   ```
   如需覆盖 TS/React 代码，额外在 `app/frontend/`、`packages/` 等目录执行相同命令，并将结果输出为 CSV 供统计。
2. 将结果分类：排序、集合、深拷贝、链式取值等，并记录“触发组件/模块、复杂度、可替换 API、预计收益”四列，形成可分享的基线清单。
3. 建立 `docs/refactor/lodash_adoption_tracker.md`，每次改造后更新命中条目，作为后续周会复盘依据。

### 阶段 2：优先替换高风险/高重复场景
1. **排程表/列表排序**：统一改用 `LodashUtils.orderBy`，支持多字段排序，并对排序字段配置进行单测验证（含升序/降序）。
2. **过滤去重**：标签/实例/账户的筛选数据使用 `LodashUtils.uniqBy`，同时清理冗余的 `Array.prototype.filter` + `findIndex` 组合。
3. **深拷贝/合并**：所有 `Object.assign({}, obj)` 或 `{ ...obj }` 用 `LodashUtils.cloneDeep`/`merge` 替换，并在敏感对象（配置、表单草稿）上辅以 `_.isEqual` 防止无意义 diff。
4. **嵌套取值**：API 数据解析统一使用 `LodashUtils.get(data, 'path', default)`，在默认值策略中约定空数组/空对象/空字符串的首选项，避免 `undefined` 泄漏至 UI。
5. **输入事件**：将手写 `setTimeout` 防抖迁移至 `LodashUtils.debounce(fn, wait, { leading: false })`，并补充测试覆盖“组件卸载时取消事件”。
6. **数据整形**：集中封装 `LodashUtils.flow([normalize, enrich, sort])` 作为复杂数据处理管线，降低中间变量泄漏。

### 阶段 3：推广与规范
1. 在代码 review 模板中添加检查项：“如使用手写排序/去重/clone，请优先考虑 LodashUtils”，并在 MR 描述中要求列出“使用了哪些 Lodash API”。
2. 在 `docs/development/STYLE_GUIDE.md` 补充 Lodash 使用建议，列出常用场景与 API，并强调“禁止直接引入 lodash 全量对象”。
3. 对新模块要求优先使用 `LodashUtils`，减少 utils 或重复手写函数，同时在 lint（`eslint-plugin-lodash`/自定义 rule）中禁止 `JSON.parse(JSON.stringify())` 深拷贝。
4. 组织 30 分钟 sharing，演示 3 个真实模块的替换收益，并提供代码片段模板。

## 验收标准

- 手写的排序、去重、深拷贝代码基本消失，统一使用 `LodashUtils`。
- 事件节流/防抖统一调用 `LodashUtils.debounce/throttle`。
- API 数据访问统一使用 `LodashUtils.get` 提供默认值。
- 代码 review 时如出现手写逻辑，应能指出对应的 Lodash 替代方案。

## 风险与缓解

- **引入 Lodash 过多 API 导致包体积增加**：我们使用的是 vendor 版本，API 都在一个文件里，不存在 tree-shaking 问题；重点是统一调用方式而非额外引入。
- **团队成员对 Lodash API 不熟悉**：在文档里列出常用示例，必要时安排简短分享。
- **旧代码迁移冲击较大**：按模块逐步替换，优先在新/改的代码里使用，避免一次性大规模改动。

## 自动化与守护手段

- **扫描脚本**：新增 `scripts/audit_lodash_usage.py`，读取阶段 1 产出的清单，持续检测 diff 中是否出现黑名单模式（`new Set([...])`, `obj?.a?.b` 等），并在 CI 的 `make quality` 里执行。
- **命令行助手**：在 `scripts/cli/tooling.sh` 中加入 `./scripts/lodash_refactor.sh pattern`，自动定位并生成建议替换的 diff（基于 `jscodeshift`）。
- **提示性 ESLint 规则**：对 `Array.prototype.sort`、`reduce` 等常见 API 添加 `prefer-lodash-orderby` 自定义 rule，触发时给出推荐写法。
- **命令结果固化**：扫描脚本输出保存到 `docs/refactor/lodash_reports/<date>.md`，便于跟踪回溯。

## 度量指标与推进节奏

- **覆盖率**：每周统计 `LodashUtils` API 在代码库中的引用次数，目标是季度内新增调用 >= 60% 源于 Lodash。
- **遗留偿还率**：针对阶段 1 清单设置 S/M/L 标签，要求每个迭代至少关闭 2 个 M 级条目。
- **缺陷率**：对比 Lodash 改造前后的相关 bug/回归数量，若下降明显可进一步强化推广。
- **培训参与度**：至少 80% 前端/全栈同学参加分享或回看录屏，避免知识孤岛。

## 代码示例

```javascript
// 旧：多次判空 + 手写排序
const sortedList = (items || [])
  .filter(item => item && item.value)
  .sort((a, b) => (a.value > b.value ? -1 : 1));
const ownerName = items && items[0] && items[0].owner ? items[0].owner.name : '未知';

// 新：统一使用 LodashUtils
const sortedList = LodashUtils.orderBy(
  LodashUtils.compact(items),
  ['value'],
  ['desc']
);
const ownerName = LodashUtils.get(sortedList, '[0].owner.name', '未知');
```

```javascript
// 旧：深拷贝 + 手写去重 + 事件防抖
const cache = JSON.parse(JSON.stringify(payload));
const uniqueTags = tags.filter((tag, idx, self) => self.findIndex(t => t.id === tag.id) === idx);
let timer;
const onInput = value => {
  clearTimeout(timer);
  timer = setTimeout(() => fetchData(value), 300);
};

// 新：LodashUtils 组合
const cache = LodashUtils.cloneDeep(payload);
const uniqueTags = LodashUtils.uniqBy(tags, 'id');
const onInput = LodashUtils.debounce(fetchData, 300, { leading: false, trailing: true });
```

## 下一步
1. 完成本计划文档评审，确认范围。
2. 分配具体模块（如标签、实例、历史日志等）给对应开发者替换手写逻辑。
3. 改造完成后，在代码 review 中保持对 Lodash 使用的监督，确保不再回退到手写方式。
