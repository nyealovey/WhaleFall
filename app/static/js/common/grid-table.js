(function (global) {
  "use strict";

  const gridjs = global.gridjs;
  if (!gridjs?.Grid) {
    console.error("GridTable: gridjs.Grid 未加载");
    return;
  }

  function resolveElement(target) {
    if (!target) {
      return null;
    }
    if (target instanceof Element) {
      return target;
    }
    if (typeof target === "string") {
      return document.querySelector(target);
    }
    if (target && typeof target.first === "function") {
      return target.first();
    }
    return null;
  }

  function mergeObjects(base, override) {
    const result = { ...(base || {}) };
    const forbiddenKeys = new Set(["__proto__", "prototype", "constructor"]);
    Object.entries(override || {}).forEach(([key, value]) => {
      if (forbiddenKeys.has(key)) {
        return;
      }
      const baseValue = Reflect.get(result, key);
      const canMerge =
        baseValue &&
        typeof baseValue === "object" &&
        !Array.isArray(baseValue) &&
        value &&
        typeof value === "object" &&
        !Array.isArray(value);

      // Merge one level deep for plain objects (className/language/style/pagination 等足够).
      Reflect.set(result, key, canMerge ? { ...baseValue, ...value } : value);
    });
    return result;
  }

  function buildOptions(userOptions) {
    const defaults = {
      sort: true,
      search: true,
      pagination: {
        enabled: true,
        limit: 20,
        summary: true,
      },
      language: {
        pagination: {
          previous: "上一页",
          next: "下一页",
          showing: "显示",
          to: "至",
          of: "共",
          results: "条记录",
        },
        loading: "加载中...",
        noRecordsFound: "未找到记录",
        error: "加载数据失败",
      },
      className: {
        table: "table table-hover align-middle mb-0 compact-table",
        thead: "table-light",
        td: "compact-cell",
        th: "compact-header",
      },
      style: {
        table: { "font-size": "13px" },
        td: { padding: "6px 12px", "line-height": "1.4" },
        th: { padding: "8px 12px", "font-size": "13px" },
      },
    };

    const merged = mergeObjects(defaults, userOptions || {});
    merged.pagination = mergeObjects(defaults.pagination, userOptions?.pagination || {});
    merged.language = mergeObjects(defaults.language, userOptions?.language || {});
    merged.className = mergeObjects(defaults.className, userOptions?.className || {});
    merged.style = mergeObjects(defaults.style, userOptions?.style || {});

    return merged;
  }

  function create(options = {}) {
    const config = buildOptions(options);
    let container = null;
    let grid = null;

    function destroy() {
      if (grid && typeof grid.destroy === "function") {
        grid.destroy();
      }
      grid = null;
      if (container) {
        container.innerHTML = "";
      }
    }

    function render(target) {
      container = resolveElement(target);
      if (!container) {
        throw new Error("GridTable: container 未找到");
      }
      destroy();

      grid = new gridjs.Grid(config);
      grid.render(container);
      return api;
    }

    const api = {
      get grid() {
        return grid;
      },
      render,
      destroy,
    };

    return api;
  }

  global.GridTable = Object.freeze({
    create,
  });
})(window);
