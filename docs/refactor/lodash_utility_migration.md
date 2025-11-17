# Lodash 前端通用工具重构方案

## 背景

当前前端代码在数组去重、对象合并、深拷贝、节流/防抖、字符串处理等场景采用大量手写辅助函数或内联逻辑，主要问题：

- **实现分散**：`components/`、`pages/`、`utils/` 中存在重复的排序、过滤、clone、merge 等逻辑，维护困难。
- **可靠性不足**：手写实现缺少边界处理（深层对象、循环引用、Unicode 字符串等），易出现潜在 bug。
- **性能/尺寸隐患**：多处引入第三方零散工具或自定义实现，无法统一 Tree Shaking 与依赖治理。

目标是引入 [Lodash](https://lodash.com/) 作为前端统一的实用函数库，并通过内部封装集中使用，以提升可靠性与可维护性。

## 依赖下载

项目采用 vendored 方式管理第三方静态资源，请按以下步骤下载 Lodash：

```bash
mkdir -p app/static/vendor/lodash

# 下载生产版本（4.17.21 可替换为需要的版本）
curl -L https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.21/lodash.min.js \
  -o app/static/vendor/lodash/lodash.min.js

# 如需未压缩版本便于调试
curl -L https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.21/lodash.js \
  -o app/static/vendor/lodash/lodash.js
```

下载完成后，在 `app/templates/base.html` 的通用脚本区域（`axios` 之后、业务脚本之前）加载 `lodash.min.js`，确保所有页面都可访问 `window._`。

## 重构策略

1. **封装入口**  
   - 在 `app/static/js/common/` 下新增 `lodash-utils.js`（命名遵循 kebab-case），集中导出常用工具，如 `cloneDeep`, `merge`, `debounce`, `throttle`, `uniqBy`, `orderBy`, `isEqual` 等。  
   - 若需限制 bundle 体积，可只暴露项目常用方法，通过 `const { debounce, throttle } = _;` 方式转发。

2. **替换手写实现**  
   - 使用 `rg` 搜索关键字（例如 `debounce`, `throttle`, `deepClone`, `JSON.parse(JSON.stringify`, `new Set(...)` 去重复等）列出所有目标。
   - 按模块优先级逐步替换：  
     1. 全局组件与公共工具（`components/`, `common/`）  
     2. 影响面大的页面脚本（实例列表、容量统计、历史同步等）  
     3. 其余散点逻辑

3. **统一出口**  
   - 封装层直接转发 Lodash 提供的方法（如 `cloneDeep`, `merge`, `debounce` 等），对外保持统一 API。
   - 所有业务代码禁止直接访问 `window._`，统一通过 `window.LodashUtils`。

4. **命名与规范**  
   - 引入新文件/函数名需遵循 `docs/refactoring/命名规范重构指南.md`，提交前运行 `./scripts/refactor_naming.sh --dry-run`。
   - 不在业务模块中直接 `import _ from 'lodash'`，统一通过封装层引用，避免多处加载同一依赖。

## 推荐封装示例

```js
// app/static/js/common/lodash-utils.js
(function (window) {
  "use strict";
  const lodash = window._;
  if (!lodash) {
    throw new Error("Lodash 未加载");
  }

  const wrap = (method) => method.bind(lodash);

  window.LodashUtils = {
    cloneDeep: wrap(lodash.cloneDeep),
    merge: wrap(lodash.merge),
    debounce: wrap(lodash.debounce),
    throttle: wrap(lodash.throttle),
    uniqBy: wrap(lodash.uniqBy),
    orderBy: wrap(lodash.orderBy),
    isEqual: wrap(lodash.isEqual),
    get: wrap(lodash.get),
    set: wrap(lodash.set),
  };
})(window);
```

## 重构步骤

1. **引入依赖**  
   - 按“依赖下载”段落拉取 Lodash 文件并在模板中加载。
   - 新建 `lodash-utils.js`，初始化封装并挂载到全局。

2. **替换现有逻辑**  
   - 分批处理：先替换 debounce/throttle、深拷贝、对象合并等高频函数，再处理去重、排序、聚合等场景。
   - 每次替换前后需手动验证对应功能（如表单验证、筛选器、防抖输入等）。

3. **测试与检查**  
   - 运行 `./scripts/refactor_naming.sh --dry-run`、`make test`（如适用）。
   - 手工走查关键页面。

4. **文档与提交**  
   - 在 PR 描述中列出替换范围、验证步骤、潜在风险。
   - 若封装 API 被其他开发者复用，在 `docs/development/STYLE_GUIDE.md` 增补“统一通过 LodashUtils 调用”的说明。

## 风险与缓解

- **体积增加**：默认 `lodash.min.js` ~70KB gzip，可接受；若需进一步瘦身，可评估使用 `lodash-es` + 构建工具，当前阶段先以 vendor 方式上线。
- **全局命名冲突**：Lodash 默认暴露 `_`，若担心冲突，可在封装层内部引用并避免全局滥用。
- **渐进式迁移**：可按模块划分批次逐步替换旧逻辑，确保验证路径清晰。

## 后续计划

1. 落地 Lodash 依赖与封装工具。
2. 分阶段替换前端脚本中的重复实现，并在 PR 中明确覆盖范围。
3. 根据反馈决定是否进一步按模块拆分（例如仅打包 `lodash.throttle.js` 等），减少最终产物体积。
