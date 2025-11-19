(function (global) {
  "use strict";

  const gridjs = global.gridjs;
  if (!gridjs || !gridjs.Grid) {
    console.error("GridWrapper: gridjs 未加载");
    return;
  }

  const { Grid } = gridjs;

  function GridWrapper(container, options = {}) {
    if (!container) {
      throw new Error("GridWrapper: container 未定义");
    }
    this.container = container;
    this.currentFilters = {};
    this.options = this.mergeOptions(options);
    this.grid = null;
  }

  GridWrapper.prototype.mergeOptions = function mergeOptions(userOptions = {}) {
    const defaults = {
      search: false,
      sort: {
        multiColumn: false,
        server: {
          url: (prev, columns) => {
            if (!columns.length) {
              return prev;
            }
            const col = columns[0];
            const dir = col.direction === 1 ? "asc" : "desc";
            let next = this.appendParam(prev, `sort=${encodeURIComponent(col.id || col.name)}`);
            next = this.appendParam(next, `order=${dir}`);
            return next;
          },
        },
      },
      pagination: {
        enabled: true,
        limit: 20,
        summary: true,
        server: {
          url: (prev, page, limit) => {
            let next = this.appendParam(prev, `page=${page + 1}`);
            next = this.appendParam(next, `limit=${limit}`);
            return next;
          },
        },
      },
      fetchOptions: {
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
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
        table: "table table-hover align-middle mb-0",
        thead: "table-light",
      },
    };
    return this.deepMerge(defaults, userOptions);
  };

  GridWrapper.prototype.init = function init() {
    const baseServer = this.options.server || {};
    if (!baseServer.url) {
      throw new Error("GridWrapper: server.url 未配置");
    }
    const resolvedServer = this.buildServerConfig(baseServer);
    this.options.server = resolvedServer;
    const gridOptions = {
      ...this.options,
    };
    this.grid = new Grid(gridOptions);
    this.grid.render(this.container);
    return this;
  };

  GridWrapper.prototype.buildServerConfig = function buildServerConfig(baseServer) {
    const originalUrl = baseServer.url;
    const urlResolver = typeof originalUrl === "function" ? originalUrl : () => originalUrl;

    const serverConfig = {
      ...baseServer,
      url: (...args) => {
        const prev = urlResolver(...args);
        return this.appendFilters(prev, this.currentFilters);
      },
      fetch: (url, fetchOptions) => {
        const baseOptions = fetchOptions || {};
        const mergedOptions = {
          ...baseOptions,
          ...(this.options.fetchOptions || {}),
        };
        return fetch(url, mergedOptions);
      },
    };
    serverConfig.__baseUrlResolver = urlResolver;
    return serverConfig;
  };

  GridWrapper.prototype.appendFilters = function appendFilters(url, filters = {}) {
    let result = url;
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      if (Array.isArray(value)) {
        if (!value.length) {
          return;
        }
        value.forEach((item) => {
          result = this.appendParam(result, `${encodeURIComponent(key)}=${encodeURIComponent(item)}`);
        });
        return;
      }
      result = this.appendParam(result, `${encodeURIComponent(key)}=${encodeURIComponent(value)}`);
    });
    return result;
  };

  GridWrapper.prototype.setFilters = function setFilters(filters = {}, options = {}) {
    this.currentFilters = { ...(filters || {}) };
    if (!options.silent) {
      this.refresh();
    }
    return this;
  };

  GridWrapper.prototype.updateFilters = function updateFilters(filters = {}) {
    return this.setFilters(filters);
  };

  GridWrapper.prototype.refresh = function refresh() {
    if (this.grid && typeof this.grid.forceRender === "function") {
      this.grid.forceRender();
    }
    return this;
  };

  GridWrapper.prototype.mergeGridQueryParams = function mergeGridQueryParams(baseUrl, sourceUrl) {
    const query = this.extractQueryString(sourceUrl);
    const normalizedBase = baseUrl || this.normalizeBaseUrl("", sourceUrl);
    if (!query) {
      return normalizedBase || sourceUrl || "";
    }
    if (!normalizedBase) {
      return `?${query}`;
    }
    const separator = normalizedBase.includes("?") ? "&" : "?";
    return `${normalizedBase}${separator}${query}`;
  };

  GridWrapper.prototype.normalizeBaseUrl = function normalizeBaseUrl(baseUrl, fallbackUrl) {
    if (baseUrl) {
      return baseUrl;
    }
    if (!fallbackUrl) {
      return "";
    }
    const trimmed = fallbackUrl.trim();
    if (!trimmed) {
      return "";
    }
    const questionIndex = trimmed.indexOf("?");
    const hashIndex = trimmed.indexOf("#");
    const endIndex =
      questionIndex >= 0 ? questionIndex : hashIndex >= 0 ? hashIndex : trimmed.length;
    return trimmed.slice(0, endIndex);
  };

  GridWrapper.prototype.extractQueryString = function extractQueryString(sourceUrl) {
    if (!sourceUrl) {
      return "";
    }
    const trimmed = sourceUrl.trim();
    if (!trimmed) {
      return "";
    }
    if (trimmed.startsWith("?")) {
      return trimmed.slice(1).split("#")[0];
    }
    const questionIndex = trimmed.indexOf("?");
    if (questionIndex >= 0) {
      return trimmed.slice(questionIndex + 1).split("#")[0];
    }
    if (!trimmed.startsWith("http") && trimmed.includes("=")) {
      return trimmed.split("#")[0];
    }
    return "";
  };

  GridWrapper.prototype.appendParam = function appendParam(url, param) {
    let target = url;
    if (!target || target === "?") {
      target = this.resolveBaseUrl();
    }
    if (!target) {
      target = "";
    }
    const separator = target.includes("?") ? "&" : "?";
    return `${target}${separator}${param}`;
  };

  GridWrapper.prototype.resolveBaseUrl = function resolveBaseUrl() {
    const server = this.options?.server;
    const resolver = server?.__baseUrlResolver;
    if (typeof resolver === "function") {
      try {
        return resolver();
      } catch (error) {
        console.error("GridWrapper: 解析基础请求地址失败", error);
      }
    }
    if (typeof server?.url === "string") {
      return server.url;
    }
    return "";
  };

  GridWrapper.prototype.deepMerge = function deepMerge(target, source) {
    const output = { ...target };
    if (this.isObject(target) && this.isObject(source)) {
      Object.keys(source).forEach((key) => {
        if (this.isObject(source[key])) {
          if (!(key in target)) {
            output[key] = source[key];
          } else {
            output[key] = this.deepMerge(target[key], source[key]);
          }
        } else {
          output[key] = source[key];
        }
      });
    }
    return output;
  };

  GridWrapper.prototype.isObject = function isObject(item) {
    return item && typeof item === "object" && !Array.isArray(item);
  };

  global.GridWrapper = GridWrapper;
})(window);
