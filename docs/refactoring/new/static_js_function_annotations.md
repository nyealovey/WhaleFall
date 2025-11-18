# app/static/js 函数注释重构计划

## 目标
- 为 `app/static/js/` 下的所有函数、类和导出工厂补充简洁的行级或块级注释，说明用途、关键参数、副作用。
- 注释遵循统一格式，避免破坏现有逻辑与 lint 规则，同时保持中文描述、易读性。

## 范围与优先级
1. **核心公共模块**（优先级高）
   - `modules/services/`
   - `modules/stores/`
   - `modules/views/components/`
   - `core/`、`common/`
2. **页面视图层**
   - `modules/views/**`
   - `bootstrap/**`（入口装配）
3. **遗留脚本**
   - `vendor` 以外的自定义 JS（若存在）

## 注释风格
- 采用单行 `//` 或块状 `/** ... */`；针对复杂函数用块状描述。
- 模板示例：
  ```js
  /**
   * 说明一句话
   * @param {...}
   * @returns {...}
   */
  function xxx() {
    // ...
  }
  ```
- 对事件处理、闭包、导出 API 在声明处注释，不在每一行重复。

## 执行步骤
1. **脚本清单**：使用 `find app/static/js -name '*.js'` 导出路径列表，记录在 `docs/refactor/static_js_files.md`。
2. **模块分批**：按目录划分批次，每次 PR 涵盖 1~2 个子目录，确保可读性。
3. **审阅与验证**：
   - 每次注释修改后运行 `npm`/`pytest`（若相关）以防格式问题。
   - 重点检查 ESLint/格式化结果，保持 120 字符限制。
4. **工具**：可用 `rg` 搜索无注释函数，或编写脚本检测 `function` 声明前是否包含 `//`。

## 约束
- 仅添加注释，不改动函数逻辑；如需重构另开任务。
- 保持注释语言为中文；可嵌入必要的英文专有词。
- 避免在 `vendor/`、第三方库中注释或修改。

## 验收标准
- `app/static/js` 下每个自定义函数、类、导出均有明确用途注释。
- 文档更新记录在 `CHANGELOG.md`（可选）。
- 通过 `./scripts/refactor_naming.sh --dry-run`，确保命名规范未被破坏。

## 建议进度
1. **阶段 1**：`modules/services` + `modules/stores`
2. **阶段 2**：`modules/views/components` + `modules/views/accounts/*`
3. **阶段 3**：`modules/views/instances/*` + 其他页面
4. **阶段 4**：`core/`、`common/` 与零散脚本

每阶段完成后更新该文档，记录覆盖范围与 TODO。

## 注释应覆盖的信息
- 作用：函数/类提供什么能力、在哪个上下文被使用。
- 输入：关键参数类型/取值范围/必填可选，事件对象或外部依赖（如全局 store、DOM 选择器）。
- 输出：返回值形态、Promise 逻辑、是否有副作用（修改 DOM、全局状态、触发事件）。
- 边界：节流/防抖、错误处理路径、缓存命中等特殊分支。

## 模块示例片段
### 服务层（modules/services）
```js
// 通过 Grid.js 服务端分页获取实例列表；保留筛选器的查询字符串
export const fetchInstances = (params = {}) => {
  // params: { page, limit, sort, order, filters }
  return request.get('/api/instances', { params });
};
```

### 视图层事件处理（modules/views/**）
```js
// 处理标签筛选变更，重置页码并刷新表格
const handleTagFilterChange = (tagId) => {
  currentPage.value = 1;
  grid.forceRender({ tag_id: tagId });
};
```

### 状态存储（modules/stores）
```js
// 保存最近一次同步结果，供实例详情页复用
export const setLastSyncResult = (instanceId, result) => {
  state.syncResults[instanceId] = result;
};
```

## 分批进度记录（草案）
- [x] services：`modules/services/*.js`（抽检 connection_service.js、instance_management_service.js 均已覆盖用途/参数/异常）
- [x] stores：`modules/stores/*.js`（instance_store.js、tag_list_store.js 等已标注状态流转与事件）
- [x] 核心 UI：`modules/ui/**`（modal.js、filter-card.js 已补充初始化依赖、事件绑定说明）
- [x] 通用组件：`modules/views/components/**`（如 connection-manager.js 已为导出方法补充用途与回调参数）
- [x] 视图入口：`bootstrap/**`（已为各入口脚本补充“挂载对象 + 依赖条件”描述）
- [x] 其他页面视图：`modules/views/**`（抽检 tags/index.js、auth/login.js、capacity-stats/* 均有注释，建议后续走查剩余页面）
- [x] 核心工具：`core/`、`common/`（dom.helpers.js、http-u.js、csrf-utils.js 等已添加用途与边界处理说明）
