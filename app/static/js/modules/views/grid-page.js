(function (global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("Views.GridPage: DOMHelpers 未初始化");
    return;
  }

  const GridWrapper = global.GridWrapper;
  if (!GridWrapper) {
    console.error("Views.GridPage: GridWrapper 未加载");
    return;
  }

  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const isSafeKey = (key) => typeof key === "string" && !UNSAFE_KEYS.includes(key);

  function resolveElement(input, { rootEl = null } = {}) {
    if (!input) {
      return null;
    }
    if (input instanceof Element) {
      return input;
    }
    if (typeof input === "string") {
      const selector = input;
      if (rootEl) {
        const scoped = rootEl.querySelector(selector);
        if (scoped) {
          return scoped;
        }
      }
      return document.querySelector(selector);
    }
    return null;
  }

  function resolveAllowedKeys(config) {
    const allowed = config?.filters?.allowedKeys;
    if (!Array.isArray(allowed)) {
      return null;
    }
    return allowed.filter((key) => typeof key === "string" && isSafeKey(key));
  }

  function pickAllowedFilters(filters, allowedKeys) {
    const source = filters && typeof filters === "object" ? filters : {};
    if (!allowedKeys || !allowedKeys.length) {
      const picked = Object.create(null);
      Object.entries(source).forEach(([key, value]) => {
        if (!isSafeKey(key)) {
          return;
        }
        // eslint-disable-next-line security/detect-object-injection
        picked[key] = value;
      });
      return picked;
    }

    const picked = Object.create(null);
    allowedKeys.forEach((key) => {
      if (!isSafeKey(key)) {
        return;
      }
      // eslint-disable-next-line security/detect-object-injection
      const value = source[key];
      if (value === undefined) {
        return;
      }
      // eslint-disable-next-line security/detect-object-injection
      picked[key] = value;
    });
    return picked;
  }

  function createGridPageController(config) {
    const rootEl = resolveElement(config?.root);
    if (!rootEl) {
      console.error("Views.GridPage: root 未找到", config?.root);
      return null;
    }

    const gridEl = resolveElement(config?.grid, { rootEl });
    if (!gridEl) {
      console.error("Views.GridPage: grid 未找到", config?.grid);
      return null;
    }

    const filterFormEl = resolveElement(config?.filterForm, { rootEl });
    const allowedKeys = resolveAllowedKeys(config);
    if (!allowedKeys) {
      console.warn("Views.GridPage: filters.allowedKeys 未配置，退回仅过滤危险键");
    }

    const state = {
      destroyed: false,
      filters: Object.create(null),
    };

    const plugins = [];
    const pluginDestroyers = [];

    const ctx = {
      config: config || {},
      rootEl,
      gridEl,
      filterFormEl,
      helpers,
      UI: global.UI || null,
      toast: global.toast || null,
      gridWrapper: null,
      filterCard: null,
      state,
      queryOne: (selector) => {
        if (!selector || typeof selector !== "string") {
          return null;
        }
        return rootEl.querySelector(selector);
      },
      queryAll: (selector) => {
        if (!selector || typeof selector !== "string") {
          return [];
        }
        return Array.from(rootEl.querySelectorAll(selector));
      },
      getFilters: () => Object.assign({}, state.filters),
      buildSearchParams: (filters) => {
        const safe = pickAllowedFilters(filters || {}, allowedKeys);
        if (global.TableQueryParams?.buildSearchParams) {
          return global.TableQueryParams.buildSearchParams(safe);
        }
        const params = new URLSearchParams();
        Object.entries(safe).forEach(([key, value]) => {
          if (!isSafeKey(key)) {
            return;
          }
          if (value === undefined || value === null || value === "") {
            return;
          }
          if (Array.isArray(value)) {
            value.forEach((item) => {
              if (item === undefined || item === null || item === "") {
                return;
              }
              params.append(key, item);
            });
            return;
          }
          params.append(key, value);
        });
        return params;
      },
      applyFiltersFromValues: (values, options = {}) => {
        const resolver = config?.filters?.resolve;
        const resolved = typeof resolver === "function" ? resolver(values || {}, ctx) : Object.assign({}, values || {});
        if (resolved === null) {
          return ctx.getFilters();
        }
        return ctx.applyFilters(resolved, Object.assign({}, options, { source: options.source || "values" }));
      },
      applyFiltersFromForm: (options = {}) => {
        const form = filterFormEl;
        const serialize = ctx.filterCard?.serialize || global.UI?.serializeForm;
        const values = typeof serialize === "function" ? serialize(form) : {};
        return ctx.applyFiltersFromValues(values, Object.assign({}, options, { source: options.source || "form" }));
      },
      applyFilters: (filters, options = {}) => {
        const resolved = pickAllowedFilters(filters || {}, allowedKeys);
        const tableQueryParams = global.TableQueryParams;
        const paginationNormalized =
          tableQueryParams?.normalizePaginationFilters && typeof tableQueryParams.normalizePaginationFilters === "function"
            ? tableQueryParams.normalizePaginationFilters(resolved)
            : resolved;
        const normalizer = config?.filters?.normalize;
        const normalized =
          typeof normalizer === "function" ? normalizer(paginationNormalized, ctx) : paginationNormalized;
        state.filters = Object.assign({}, normalized || {});

        if (ctx.gridWrapper) {
          ctx.gridWrapper.setFilters(state.filters, { silent: Boolean(options.silent) });
        }

        if (!options.silent) {
          plugins.forEach((plugin) => {
            if (typeof plugin?.onFiltersChanged === "function") {
              plugin.onFiltersChanged(ctx, {
                filters: Object.assign({}, state.filters),
                source: options.source || null,
              });
            }
          });
        }

        return state.filters;
      },
    };

    const rawPlugins = Array.isArray(config?.plugins) ? config.plugins : [];
    rawPlugins.forEach((plugin) => {
      if (!plugin) {
        return;
      }
      const resolved = typeof plugin === "function" ? plugin(ctx) : plugin;
      if (!resolved) {
        return;
      }
      plugins.push(resolved);
    });

    ctx.gridWrapper = new GridWrapper(gridEl, config?.gridOptions || {});

    plugins.forEach((plugin) => {
      if (typeof plugin?.init !== "function") {
        return;
      }
      const result = plugin.init(ctx);
      if (result && typeof result.destroy === "function") {
        pluginDestroyers.push(() => result.destroy());
      }
    });

    ctx.applyFiltersFromForm({ silent: true, source: "init" });
    ctx.gridWrapper.init();

    const gridHandlers = [];
    if (ctx.gridWrapper.grid?.on) {
      const onReady = () => {
        plugins.forEach((plugin) => {
          if (typeof plugin?.onGridReady === "function") {
            plugin.onGridReady(ctx);
          }
        });
      };
      const onUpdated = () => {
        plugins.forEach((plugin) => {
          if (typeof plugin?.onGridUpdated === "function") {
            plugin.onGridUpdated(ctx);
          }
        });
      };
      ctx.gridWrapper.grid.on("ready", onReady);
      ctx.gridWrapper.grid.on("updated", onUpdated);
      gridHandlers.push({ event: "ready", handler: onReady });
      gridHandlers.push({ event: "updated", handler: onUpdated });
    }

    return {
      rootEl,
      gridEl,
      filterFormEl,
      gridWrapper: ctx.gridWrapper,
      get filterCard() {
        return ctx.filterCard;
      },
      applyFiltersFromValues: ctx.applyFiltersFromValues,
      applyFiltersFromForm: ctx.applyFiltersFromForm,
      applyFilters: ctx.applyFilters,
      getFilters: ctx.getFilters,
      destroy: () => {
        if (state.destroyed) {
          return;
        }
        state.destroyed = true;
        pluginDestroyers.forEach((destroy) => destroy());
        pluginDestroyers.length = 0;
        plugins.forEach((plugin) => {
          if (typeof plugin?.destroy === "function") {
            plugin.destroy(ctx);
          }
        });
        if (ctx.gridWrapper?.grid?.off) {
          gridHandlers.forEach(({ event, handler }) => {
            ctx.gridWrapper.grid.off(event, handler);
          });
        }
        gridHandlers.length = 0;
      },
    };
  }

  function mount(config) {
    return createGridPageController(config);
  }

  global.Views = global.Views || {};
  global.Views.GridPage = global.Views.GridPage || {};
  global.Views.GridPage.mount = mount;
})(window);
