(function (global) {
  "use strict";

  const gridjs = global.gridjs;
  if (!gridjs || !gridjs.Grid) {
    console.error("GridWrapper: gridjs 未加载");
    return;
  }

  const { Grid } = gridjs;

  const debugEnabled = () => Boolean(global.DEBUG_GRID_WRAPPER);
  const MAX_PAGE_SIZE = 200;
  const DEFAULT_PAGE_SIZE = 20;
  /**
   * GridWrapper 调试日志输出，默认关闭。
   *
   * @param {string} message 文本描述。
   * @param {*} [payload] 可选上下文对象。
   * @returns {void}
   */
  function debugLog(message, payload) {
    if (!debugEnabled()) {
      return;
    }
    const prefix = "[GridWrapper]";
    if (payload !== undefined) {
      console.debug(`${prefix} ${message}`, payload);
    } else {
      console.debug(`${prefix} ${message}`);
    }
  }

  /**
   * gridjs 包装器，统一处理服务端分页/排序。
   *
   * @param {HTMLElement} container 承载 gridjs 表格的容器。
   * @param {Object} [options={}] gridjs 初始化参数。
   * @returns {void}
   * @constructor
   */
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
            let next = this.applyFiltersToUrl(prev, this.currentFilters);
            next = this.removeQueryKeys(next, ["sort", "order"]);
            next = this.appendParam(next, `sort=${encodeURIComponent(col.id || col.name)}`);
            next = this.appendParam(next, `order=${dir}`);
            return next;
          },
        },
      },
      pagination: {
        enabled: true,
        limit: DEFAULT_PAGE_SIZE,
        summary: true,
        server: {
          url: (prev, page, limit) => {
            let next = this.applyFiltersToUrl(prev, this.currentFilters);
            next = this.removeQueryKeys(next, ["page", "limit", "page_size"]);
            next = this.appendParam(next, `page=${page + 1}`);
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
        table: "table table-hover align-middle mb-0 compact-table",
        thead: "table-light",
        td: "compact-cell",
        th: "compact-header",
      },
      style: {
        table: {
          'font-size': '13px'
        },
        td: {
          'padding': '6px 12px',
          'line-height': '1.4'
        },
        th: {
          'padding': '8px 12px',
          'font-size': '13px'
        }
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
    const baseResolver =
      typeof baseServer.__baseUrlResolver === "function"
        ? baseServer.__baseUrlResolver
        : typeof originalUrl === "function"
          ? originalUrl
          : () => originalUrl;
    const self = this;

    const serverConfig = {
      ...baseServer,
      url: (...args) => {
        const prev = baseResolver(...args);
        const result = self.appendFilters(prev, self.currentFilters);
        debugLog("URL 构建", { prev, filters: self.currentFilters, result });
        return result;
      },
    };
    serverConfig.__baseUrlResolver = baseResolver;
    return serverConfig;
  };

  GridWrapper.prototype.removeQueryKeys = function removeQueryKeys(url, keys = []) {
    const normalized = this.normalizeUrlString(url);
    if (!normalized || !Array.isArray(keys) || !keys.length) {
      return normalized;
    }
    const [baseWithQuery, hash = ""] = normalized.split("#");
    const [base, query = ""] = baseWithQuery.split("?");
    if (!query) {
      return normalized;
    }
    const params = new URLSearchParams(query);
    keys.forEach((key) => {
      if (!key) {
        return;
      }
      params.delete(key);
    });
    const queryString = params.toString();
    const rebuilt = queryString ? `${base}?${queryString}` : base;
    return hash ? `${rebuilt}#${hash}` : rebuilt;
  };

  GridWrapper.prototype.applyFiltersToUrl = function applyFiltersToUrl(url, filters = {}) {
    const normalizedFilters = filters && typeof filters === "object" ? filters : {};
    const filterKeys = Object.keys(normalizedFilters);
    const cleaned = this.removeQueryKeys(url, filterKeys);
    return this.appendFilters(cleaned, normalizedFilters);
  };

  GridWrapper.prototype.appendFilters = function appendFilters(url, filters = {}) {
    let result = this.normalizeUrlString(url);
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
    const normalizedFilters = { ...(filters || {}) };
    const pageSize = this.resolvePageSize(normalizedFilters);
    if (pageSize !== null) {
      this.applyPageSize(pageSize);
    }
    // 分页字段由 gridjs pagination 控制，避免重复拼接导致行为不可预测。
    delete normalizedFilters.page;
    delete normalizedFilters.limit;
    delete normalizedFilters.page_size;

    this.currentFilters = normalizedFilters;
    debugLog("setFilters 调用", { filters: this.currentFilters, options, pageSize });
    if (!options.silent) {
      this.refresh();
    }
    return this;
  };

  GridWrapper.prototype.updateFilters = function updateFilters(filters = {}) {
    return this.setFilters(filters);
  };

  GridWrapper.prototype.refresh = function refresh() {
    if (!this.grid) {
      console.warn("[GridWrapper] Grid 实例未初始化");
      return this;
    }

    if (!this.grid.config) {
      console.warn("[GridWrapper] Grid config 不可用");
      return this;
    }

    debugLog("refresh 调用", { filters: this.currentFilters });

    const pipeline = this.grid.config?.pipeline;
    // 优先触发 pipeline updated 事件，让 Grid.js 在不重建插件的情况下重新拉取数据。
    // 避免重复渲染触发控制台告警：
    // [Grid.js] [ERROR]: Duplicate plugin ID: pagination
    if (pipeline && typeof pipeline.clearCache === "function" && typeof pipeline.emit === "function") {
      pipeline.clearCache();
      pipeline.emit("updated");
      return this;
    }

    // 兜底：旧版本 Grid.js 缺少 pipeline.emit 时，回退到 forceRender/render。
    if (typeof this.grid.forceRender === "function") {
      this.grid.forceRender();
    } else if (typeof this.grid.render === "function") {
      this.grid.render(this.container);
    } else {
      console.warn("[GridWrapper] Grid 无法刷新（缺少 pipeline/forceRender/render）");
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
    let target = this.normalizeUrlString(url);
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

  GridWrapper.prototype.normalizeUrlString = function normalizeUrlString(url) {
    if (!url) {
      return "";
    }
    if (typeof url === "string") {
      return url;
    }
    if (typeof url === "object") {
      if (typeof url.url === "string") {
        return url.url;
      }
      if (typeof url.href === "string") {
        return url.href;
      }
      if (typeof url.toString === "function") {
        const value = url.toString();
        if (value && value !== "[object Object]" && value !== "[object Request]") {
          return value;
        }
      }
    }
    try {
      return String(url);
    } catch (error) {
      console.error("GridWrapper: 无法解析 URL", error);
      return "";
    }
  };

  GridWrapper.prototype.deepMerge = function deepMerge(target, source) {
    const output = { ...target };
    const isSafeKey = (key) => !['__proto__', 'prototype', 'constructor'].includes(key);
    if (this.isObject(target) && this.isObject(source)) {
      Object.keys(source).forEach((key) => {
        if (!isSafeKey(key) || !Object.prototype.hasOwnProperty.call(source, key)) {
          return;
        }
        // 经过安全键过滤后再读取值，防御原型污染。
        // eslint-disable-next-line security/detect-object-injection
        const sourceValue = source[key];
        if (this.isObject(sourceValue)) {
          if (!(key in target)) {
            output[key] = sourceValue; // eslint-disable-line security/detect-object-injection
          } else {
            // 深度合并仅在安全键下递归，避免原型污染。
            // eslint-disable-next-line security/detect-object-injection
            output[key] = this.deepMerge(target[key], sourceValue);
          }
        } else {
          // 经过 isSafeKey 过滤，仅合并自有字段，避免原型污染。
          output[key] = sourceValue; // eslint-disable-line security/detect-object-injection
        }
      });
    }
    return output;
  };

  GridWrapper.prototype.isObject = function isObject(item) {
    return item && typeof item === "object" && !Array.isArray(item);
  };

  GridWrapper.prototype.resolvePageSize = function resolvePageSize(filters = {}) {
    const candidateValue = filters.limit;
    const parseCandidate = (candidateValue) => {
      if (candidateValue === undefined || candidateValue === null || candidateValue === "") {
        return null;
      }
      const raw = Array.isArray(candidateValue) ? candidateValue[0] : candidateValue;
      const parsed = Number.parseInt(String(raw), 10);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        return null;
      }
      return Math.min(Math.max(parsed, 1), MAX_PAGE_SIZE);
    };

    return parseCandidate(candidateValue);
  };

  GridWrapper.prototype.applyPageSize = function applyPageSize(pageSize) {
    if (!pageSize || !Number.isFinite(pageSize)) {
      return;
    }
    const resolved = Math.min(Math.max(Number(pageSize), 1), MAX_PAGE_SIZE);
    if (this.options.pagination === false) {
      return;
    }
    if (!this.options.pagination || !this.isObject(this.options.pagination)) {
      this.options.pagination = { enabled: true, limit: resolved, summary: true };
      return;
    }
    this.options.pagination.limit = resolved;
  };

  global.GridWrapper = GridWrapper;
})(window);
