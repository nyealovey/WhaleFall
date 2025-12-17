(function (global) {
  "use strict";

  const gridjs = global.gridjs;
  if (!gridjs || !gridjs.Grid) {
    console.error("GridWrapper: gridjs 未加载");
    return;
  }

  const { Grid } = gridjs;

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
    const urlResolver = typeof originalUrl === "function" ? originalUrl : () => originalUrl;
    const self = this;

    const serverConfig = {
      ...baseServer,
      url: (...args) => {
        const prev = urlResolver(...args);
        const result = self.appendFilters(prev, self.currentFilters);
        console.log('[GridWrapper] URL 构建:', { prev, filters: self.currentFilters, result });
        return result;
      },
    };
    serverConfig.__baseUrlResolver = urlResolver;
    return serverConfig;
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
    console.log('[GridWrapper] setFilters 调用:', { filters, options, silent: options.silent });
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
    console.log('[GridWrapper] refresh 调用, currentFilters:', this.currentFilters);
    
    if (!this.grid) {
      console.warn('[GridWrapper] Grid 实例未初始化');
      return this;
    }
    
    if (!this.grid.config) {
      console.warn('[GridWrapper] Grid config 不可用');
      return this;
    }
    
    // 重新构建服务端配置（包含最新的筛选参数）
    const newServerConfig = this.buildServerConfig(this.options.server || {});
    console.log('[GridWrapper] 更新服务端配置, 新筛选参数:', this.currentFilters);
    
    // 直接更新 Grid 的 server.url 函数（避免 updateConfig 导致插件重复）
    if (this.grid.config.server) {
      this.grid.config.server.url = newServerConfig.url;
      this.grid.config.server.__baseUrlResolver = newServerConfig.__baseUrlResolver;
      console.log('[GridWrapper] 已更新 server.url 函数');
    }
    
    // 清除缓存
    if (this.grid.config.store) {
      console.log('[GridWrapper] 清除 store 缓存');
      if (typeof this.grid.config.store.clearCache === "function") {
        this.grid.config.store.clearCache();
      }
    }
    
    // 尝试直接操作 pipeline 重新加载数据
    if (this.grid.config.pipeline) {
      console.log('[GridWrapper] 触发 pipeline 重新处理');
      const pipeline = this.grid.config.pipeline;
      
      // 清除 pipeline 缓存
      if (pipeline.clearCache && typeof pipeline.clearCache === "function") {
        pipeline.clearCache();
      }
      
      // 重新处理数据
      if (pipeline.process && typeof pipeline.process === "function") {
        console.log('[GridWrapper] 调用 pipeline.process()');
        pipeline.process().then(() => {
          console.log('[GridWrapper] pipeline 处理完成，触发渲染');
          if (typeof this.grid.forceRender === "function") {
            this.grid.forceRender();
          }
        }).catch((error) => {
          console.error('[GridWrapper] pipeline 处理失败:', error);
        });
        return this;
      }
    }
    
    // 如果没有 pipeline，尝试 forceRender
    console.log('[GridWrapper] 触发 forceRender');
    if (typeof this.grid.forceRender === "function") {
      this.grid.forceRender();
    } else {
      console.warn('[GridWrapper] forceRender 方法不可用');
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

  global.GridWrapper = GridWrapper;
})(window);
