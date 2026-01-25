---
title: UI 分层示例(长示例)
aliases:
  - ui-layer-examples
tags:
  - reference
  - reference/examples
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: `standards/ui/layer/**` 引用的长代码示例与正反例集合(非规则 SSOT)
related:
  - "[[reference/examples/README]]"
  - "[[standards/ui/guide/layer/README]]"
  - "[[standards/doc/guide/document-boundary]]"
---

# UI 分层示例(长示例)

> [!important] 说明
> 本文仅用于承载长示例代码, 便于 standards 引用与收敛. 规则 SSOT 以 `docs/Obsidian/standards/**` 为准.

## Page Entry 示例

```javascript
function mountInstancesListPage(global) {
  "use strict";

  const { DOMHelpers, httpU } = global;
  if (!DOMHelpers || !httpU) {
    console.error("InstancesListPage: 依赖缺失");
    return;
  }

  const pageRoot = document.getElementById("instances-page-root");
  if (!pageRoot) {
    console.warn("InstancesListPage: root 未找到");
    return;
  }

  // wiring: services/stores/views
  const service = new global.InstanceManagementService(httpU);
  const store = global.createInstanceStore({ service });

  // grid list pages: use Views.GridPage.mount(...)
  const gridPage = global.Views.GridPage.mount({
    root: pageRoot,
    grid: "#instances-grid",
    filterForm: "#instance-filter-form",
    gridOptions: { /* config only */ },
    filters: { allowedKeys: ["search", "db_type"] },
    plugins: [global.Views.GridPlugins.filterCard()],
  });

  store.init({}).catch((error) => console.error(error));

  return { destroy: () => gridPage?.destroy?.() };
}

window.InstancesListPage = {
  mount: function (global) {
    mountInstancesListPage(global || window);
  },
};
```

## Services 示例

```javascript
(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/tags";
  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const isSafeKey = (key) => typeof key === "string" && !UNSAFE_KEYS.includes(key);

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("TagService: httpClient 未初始化");
    }
    return resolved;
  }

  function buildQuery(params, allowedKeys = []) {
    const allowed = new Set(allowedKeys.filter((k) => isSafeKey(k)));
    const search = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => {
      if (!isSafeKey(key) || (allowed.size && !allowed.has(key))) {
        return;
      }
      if (value === undefined || value === null || value === "") {
        return;
      }
      search.append(key, value);
    });
    const qs = search.toString();
    return qs ? `?${qs}` : "";
  }

  class TagService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    list(params) {
      const query = buildQuery(params, ["search", "category", "status"]);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }
  }

  global.TagService = TagService;
})(window);
```

## Stores 示例

```javascript
(function (window) {
  "use strict";

  function createTagStore(options = {}) {
    const service = options.service;
    if (!service || typeof service.list !== "function") {
      throw new Error("createTagStore: service.list 未实现");
    }
    const emitter = options.emitter || (window.mitt ? window.mitt() : null);
    if (!emitter) {
      throw new Error("createTagStore: 需要 mitt emitter");
    }

    const state = { items: [], loading: false, lastError: null };
    const cloneState = () => ({ ...state, items: state.items.slice() });
    const emit = (name, payload) => emitter.emit(name, payload ?? { state: cloneState() });

    const actions = {
      load: function (params) {
        state.loading = true;
        emit("tags:loading", { loading: true, state: cloneState() });
        return service
          .list(params)
          .then((resp) => {
            const payload = resp?.data ?? resp ?? {};
            state.items = Array.isArray(payload.items) ? payload.items.slice() : [];
            state.lastError = null;
            emit("tags:updated", { items: state.items.slice(), state: cloneState() });
            return state.items;
          })
          .catch((error) => {
            state.lastError = error;
            emit("tags:error", { error, state: cloneState() });
            throw error;
          })
          .finally(() => {
            state.loading = false;
            emit("tags:loading", { loading: false, state: cloneState() });
          });
      },
    };

    return {
      getState: cloneState,
      subscribe: (eventName, handler) => emitter.on(eventName, handler),
      unsubscribe: (eventName, handler) => emitter.off(eventName, handler),
      actions,
      destroy: () => {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.items = [];
      },
    };
  }

  window.createTagStore = createTagStore;
})(window);
```

## Views 示例

```javascript
window.TagsIndexPage = {
  mount: function () {
    window.Views.GridPage.mount({
      root: "#tags-page-root",
      grid: "#tags-grid",
      filterForm: "#tag-filter-form",
      gridOptions: {
        search: false,
        sort: false,
        columns: buildColumns(),
        server: {
          url: "/api/v1/tags",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: mapRows,
          total: (resp) => Number((resp?.data || resp || {}).total) || 0,
        },
      },
      filters: {
        allowedKeys: ["search", "category", "status", "page", "limit", "sort", "order"],
        normalize: normalizeFilters,
      },
      plugins: [
        window.Views.GridPlugins.filterCard({ autoSubmitOnChange: true }),
        window.Views.GridPlugins.urlSync(),
        window.Views.GridPlugins.actionDelegation({ actions: window.TagsIndexActions }),
      ],
    });
  },
};
```

## UI Modules 示例

```javascript
(function (global) {
  "use strict";

  function createButtonLoading(buttonEl) {
    if (!buttonEl) {
      throw new Error("createButtonLoading: buttonEl is required");
    }
    const original = buttonEl.innerHTML;
    return {
      start: () => {
        buttonEl.disabled = true;
        buttonEl.innerHTML = "<span class=\"spinner-border spinner-border-sm me-2\"></span>处理中...";
      },
      stop: () => {
        buttonEl.disabled = false;
        buttonEl.innerHTML = original;
      },
    };
  }

  global.UI = global.UI || {};
  global.UI.createButtonLoading = createButtonLoading;
})(window);
```

