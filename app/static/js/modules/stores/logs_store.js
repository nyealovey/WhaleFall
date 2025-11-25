(function (window) {
  "use strict";

  const DEFAULT_PER_PAGE = 20;
  const DEFAULT_FILTERS = { hours: 24 };

  /**
   * 校验 service 是否实现日志模块接口。
   *
   * 检查服务对象是否存在，并验证是否实现了所有必需的方法。
   *
   * @param {Object} service - 服务对象
   * @param {Function} service.fetchModules - 获取模块列表的方法
   * @param {Function} service.fetchStats - 获取日志统计的方法
   * @param {Function} service.searchLogs - 搜索日志的方法
   * @param {Function} service.fetchLogDetail - 获取日志详情的方法
   * @return {Object} 校验后的服务对象
   * @throws {Error} 当 service 为空或缺少必需方法时抛出
   */
  function ensureService(service) {
    if (!service) {
      throw new Error("createLogsStore: service is required");
    }
    ["fetchModules", "fetchStats", "searchLogs", "fetchLogDetail"].forEach(function (method) {
      if (typeof service[method] !== "function") {
        throw new Error("createLogsStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  /**
   * 获取 mitt 事件总线。
   *
   * 如果提供了 emitter 则直接返回，否则从 window.mitt 创建新实例。
   *
   * @param {Object} [emitter] - 可选的 mitt 实例
   * @return {Object} mitt 事件总线实例
   * @throws {Error} 当 emitter 为空且 window.mitt 不存在时抛出
   */
  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createLogsStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  /**
   * 清洗过滤条件并填充默认值。
   *
   * 移除空值，并为缺失的必需字段填充默认值。
   *
   * @param {Object} filters - 原始过滤条件对象
   * @return {Object} 规范化后的过滤条件对象
   */
  function normalizeFilters(filters) {
    const base = filters && typeof filters === "object" ? filters : {};
    const normalized = {};
    Object.keys(base).forEach(function (key) {
      const value = base[key];
      if (value !== undefined && value !== null && value !== "") {
        normalized[key] = value;
      }
    });
    if (normalized.hours === undefined || normalized.hours === null || normalized.hours === "") {
      normalized.hours = DEFAULT_FILTERS.hours;
    }
    return normalized;
  }

  /**
   * 拷贝 state 用于事件 payload。
   *
   * 创建状态对象的浅拷贝，避免外部修改影响内部状态。
   *
   * @param {Object} state - 状态对象
   * @return {Object} 状态对象的拷贝
   */
  function cloneState(state) {
    return {
      modules: state.modules.slice(),
      stats: Object.assign({}, state.stats),
      logs: state.logs.slice(),
      filters: Object.assign({}, state.filters),
      pagination: Object.assign({}, state.pagination),
      loading: Object.assign({}, state.loading),
      lastError: state.lastError,
      selectedLog: state.selectedLog ? Object.assign({}, state.selectedLog) : null,
    };
  }

  /**
   * 标准化分页数据。
   *
   * 从不同格式的响应中提取分页信息，并统一为标准格式。
   *
   * @param {Object} data - 分页数据对象
   * @param {Object} fallback - 回退默认值对象
   * @return {Object} 标准化后的分页对象
   */
  function normalizePagination(data, fallback) {
    const source = data || {};
    const base = fallback || {};
    const page = Number(source.page ?? source.current_page ?? base.page ?? 1);
    const pages = Number(source.pages ?? source.total_pages ?? base.pages ?? 1);
    const perPage = Number(source.per_page ?? source.perPage ?? base.perPage ?? DEFAULT_PER_PAGE);
    const totalItems = Number(
      source.total ?? source.total_items ?? source.totalItems ?? base.totalItems ?? 0,
    );
    const hasNext =
      source.has_next ??
      source.has_more ??
      source.hasNext ??
      (pages ? page < pages : base.hasNext ?? false);
    const hasPrev =
      source.has_prev ??
      source.has_previous ??
      source.hasPrev ??
      (page > 1 ? true : base.hasPrev ?? false);
    const prevPage = Number(
      source.prevPage ??
        source.prev_num ??
        source.previous_page ??
        base.prevPage ??
        (hasPrev ? page - 1 : 1),
    );
    const nextPage = Number(
      source.nextPage ??
        source.next_num ??
        source.next_page ??
        base.nextPage ??
        (hasNext ? page + 1 : page),
    );

    return {
      page: page > 0 ? page : 1,
      pages: pages > 0 ? pages : 1,
      perPage: perPage > 0 ? perPage : DEFAULT_PER_PAGE,
      totalItems: totalItems >= 0 ? totalItems : 0,
      hasNext: Boolean(hasNext),
      hasPrev: Boolean(hasPrev),
      prevPage: prevPage > 0 ? prevPage : 1,
      nextPage: nextPage > 0 ? nextPage : 1,
    };
  }

  /**
   * 提取日志数组。
   *
   * 从响应对象中提取日志列表，兼容多种响应格式。
   *
   * @param {Object} response - API 响应对象
   * @return {Array} 日志数组
   */
  function extractLogs(response) {
    if (!response) {
      return [];
    }
    const payload = response.data ?? response;
    const list = payload.logs ?? payload.items ?? payload;
    if (!Array.isArray(list)) {
      return [];
    }
    return list;
  }

  /**
   * 从响应推断分页信息。
   *
   * @param {Object} response - API 响应对象
   * @param {Object} fallback - 回退默认值对象
   * @return {Object} 分页信息对象
   */
  function resolvePagination(response, fallback) {
    const payload = response?.data ?? response ?? {};
    const pagination = payload.pagination ?? response?.pagination ?? null;
    return normalizePagination(pagination, fallback);
  }

  /**
   * 提取模块列表。
   *
   * @param {Object} response - API 响应对象
   * @return {Array} 模块数组
   */
  function extractModules(response) {
    const payload = response?.data ?? response ?? {};
    const modules = payload.modules ?? payload.items ?? payload;
    if (!Array.isArray(modules)) {
      return [];
    }
    return modules.slice();
  }

  /**
   * 提取统计对象。
   *
   * @param {Object} response - API 响应对象
   * @return {Object} 统计信息对象
   */
  function extractStats(response) {
    const payload = response?.data ?? response ?? {};
    if (payload.stats) {
      return Object.assign({}, payload.stats);
    }
    if (payload.data && payload.data.stats) {
      return Object.assign({}, payload.data.stats);
    }
    return Object.assign(
      {
        total_logs: 0,
        error_logs: 0,
        warning_logs: 0,
        modules_count: 0,
      },
      payload,
    );
  }

  /**
   * 创建日志状态管理 Store。
   *
   * 提供日志查询、过滤、分页等功能的状态管理。
   *
   * @param {Object} options - 配置选项
   * @param {Object} options.service - 日志服务对象
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @param {Object} [options.initialFilters] - 初始过滤条件
   * @param {number} [options.perPage] - 每页数量
   * @return {Object} Store API 对象
   *
   * @example
   * const store = createLogsStore({
   *   service: logsService,
   *   initialFilters: { hours: 24 }
   * });
   * store.init().then(() => {
   *   console.log(store.getState());
   * });
   */
  function createLogsStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);
    const state = {
      modules: [],
      stats: {
        total_logs: 0,
        error_logs: 0,
        warning_logs: 0,
        modules_count: 0,
      },
      logs: [],
      filters: normalizeFilters(opts.initialFilters || DEFAULT_FILTERS),
      pagination: {
        page: 1,
        pages: 1,
        perPage: opts.perPage || DEFAULT_PER_PAGE,
        totalItems: 0,
        hasNext: false,
        hasPrev: false,
        prevPage: 1,
        nextPage: 1,
      },
      loading: {
        modules: false,
        stats: false,
        logs: false,
        detail: false,
      },
      lastError: null,
      selectedLog: null,
    };

    /**
     * 发布日志相关事件。
     *
     * @param {string} eventName 事件名称。
     * @param {Object} [payload] 附带数据，默认为状态快照。
     */
    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? cloneState(state));
    }

    /**
     * 统一处理日志 store 的错误。
     *
     * @param {Error|Object|string} error 捕获的异常。
     */
    function handleError(error) {
      state.lastError = error;
      emit("logs:error", { error: error, state: cloneState(state) });
    }

    /**
     * 解析日志列表响应并更新内部状态。
     *
     * @param {Object} response 后端返回的数据。
     */
    function applyListResponse(response) {
      state.logs = extractLogs(response);
      state.pagination = resolvePagination(response, state.pagination);
    }

    const api = {
      init: function (initialFilters) {
        if (initialFilters && typeof initialFilters === "object") {
          state.filters = normalizeFilters(initialFilters);
        }
        return Promise.all([
          api.actions.loadModules({ silent: true }),
          api.actions.loadStats({ silent: true }),
          api.actions.searchLogs({ page: 1, silent: true }),
        ]);
      },
      getState: function () {
        return cloneState(state);
      },
      subscribe: function (eventName, handler) {
        emitter.on(eventName, handler);
      },
      unsubscribe: function (eventName, handler) {
        emitter.off(eventName, handler);
      },
      actions: {
        loadModules: function (options) {
          const silent = Boolean(options && options.silent);
          state.loading.modules = !silent;
          if (!silent) {
            emit("logs:modulesLoading", cloneState(state));
          }
          return service
            .fetchModules()
            .then(function (response) {
              if (!response || response.success === false) {
                const error = new Error(response?.message || "加载模块失败");
                error.raw = response;
                throw error;
              }
              state.modules = extractModules(response);
              emit("logs:modulesUpdated", {
                modules: state.modules.slice(),
                state: cloneState(state),
              });
              return state.modules.slice();
            })
            .catch(function (error) {
              handleError(error);
              throw error;
            })
            .finally(function () {
              state.loading.modules = false;
            });
        },
        loadStats: function (options) {
          const silent = Boolean(options && options.silent);
          state.loading.stats = !silent;
          if (!silent) {
            emit("logs:statsLoading", cloneState(state));
          }
          const params = Object.assign({}, state.filters);
          return service
            .fetchStats(params)
            .then(function (response) {
              if (!response || response.success === false) {
                const error = new Error(response?.message || "加载日志统计失败");
                error.raw = response;
                throw error;
              }
              state.stats = extractStats(response);
              emit("logs:statsUpdated", {
                stats: Object.assign({}, state.stats),
                state: cloneState(state),
              });
              return Object.assign({}, state.stats);
            })
            .catch(function (error) {
              handleError(error);
              throw error;
            })
            .finally(function () {
              state.loading.stats = false;
            });
        },
        searchLogs: function (options) {
          const opts = options || {};
          const silent = Boolean(opts.silent);
          const incomingFilters = opts.filters;
          const requestedPage = Number(opts.page);
          let page = Number.isFinite(requestedPage) && requestedPage > 0 ? requestedPage : state.pagination.page;

          if (incomingFilters && typeof incomingFilters === "object") {
            state.filters = normalizeFilters(incomingFilters);
            page = 1;
          }

          state.pagination.page = page;

          if (!silent) {
            state.loading.logs = true;
            emit("logs:loading", cloneState(state));
          }

          const params = Object.assign({}, state.filters, {
            page: page,
            per_page: state.pagination.perPage,
          });

          return service
            .searchLogs(params)
            .then(function (response) {
              if (!response || response.success === false) {
                const error = new Error(response?.message || "查询日志失败");
                error.raw = response;
                throw error;
              }
              applyListResponse(response);
              state.lastError = null;
              emit("logs:updated", {
                logs: state.logs.slice(),
                pagination: Object.assign({}, state.pagination),
                filters: Object.assign({}, state.filters),
                state: cloneState(state),
              });
              return cloneState(state);
            })
            .catch(function (error) {
              handleError(error);
              throw error;
            })
            .finally(function () {
              state.loading.logs = false;
            });
        },
        applyFilters: function (filters, options) {
          state.filters = normalizeFilters(filters);
          state.pagination.page = 1;
          return Promise.all([
            api.actions.loadStats({ silent: options && options.silent }),
            api.actions.searchLogs({ page: 1, silent: options && options.silent }),
          ]);
        },
        resetFilters: function (options) {
          state.filters = normalizeFilters(DEFAULT_FILTERS);
          state.pagination.page = 1;
          return Promise.all([
            api.actions.loadStats({ silent: options && options.silent }),
            api.actions.searchLogs({ page: 1, silent: options && options.silent }),
          ]);
        },
        loadLogDetail: function (logId) {
          if (!logId && logId !== 0) {
            return Promise.reject(new Error("LogsStore: 需要 logId"));
          }
          state.loading.detail = true;
          return service
            .fetchLogDetail(logId)
            .then(function (response) {
              if (!response || response.success === false) {
                const error = new Error(response?.message || "加载日志详情失败");
                error.raw = response;
                throw error;
              }
              const payload = response?.data ?? response ?? {};
              const log = payload.log ?? payload.data ?? payload;
              state.selectedLog = log || {};
              emit("logs:detailLoaded", {
                log: Object.assign({}, state.selectedLog),
                state: cloneState(state),
              });
              return Object.assign({}, state.selectedLog);
            })
            .catch(function (error) {
              handleError(error);
              throw error;
            })
            .finally(function () {
              state.loading.detail = false;
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.logs = [];
        state.modules = [];
      },
    };

    return api;
  }

  window.createLogsStore = createLogsStore;
})(window);
