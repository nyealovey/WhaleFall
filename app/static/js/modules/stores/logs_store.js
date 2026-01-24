(function (window) {
  "use strict";

  /**
   * @typedef {Object} LogsService
   * @property {Function} getGridUrl
   * @property {Function} fetchStats
   * @property {Function} fetchLogDetail
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createLogsStore: service is required");
    }
    const required = ["getGridUrl", "fetchStats", "fetchLogDetail"];
    required.forEach((method) => {
      if (typeof service[method] !== "function") {
        throw new Error(`createLogsStore: service.${method} 未实现`);
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createLogsStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function normalizeInt(value, fallback) {
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return parsed;
  }

  function normalizeLogItem(item) {
    const raw = item && typeof item === "object" ? item : {};
    return {
      id: raw.id,
      timestamp: raw.timestamp,
      timestamp_display: raw.timestamp_display || raw.timestamp || "-",
      level: raw.level || "-",
      module: raw.module || "-",
      message: raw.message || "",
      context: raw.context,
      traceback: raw.traceback,
    };
  }

  function cloneState(state) {
    return {
      gridUrl: state.gridUrl,
      windowHours: state.windowHours,
      stats: state.stats ? { ...state.stats } : null,
      loading: { ...state.loading },
      lastError: state.lastError,
    };
  }

  /**
   * Logs Store：承载日志中心的状态与 actions（统计、详情缓存等）。
   *
   * @param {Object} options
   * @param {LogsService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createLogsStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      gridUrl: service.getGridUrl(),
      windowHours: 24,
      stats: null,
      loading: {
        stats: false,
      },
      lastError: null,
    };

    const detailCache = new Map();

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function setLoading(loading, meta) {
      state.loading.stats = Boolean(loading);
      emit("logs:loading", {
        loading: { ...state.loading },
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("logs:error", {
        error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function normalizeStatsParams(filters) {
      const raw = filters && typeof filters === "object" ? filters : {};
      const hours = normalizeInt(raw.hours, 24);
      return {
        search: typeof raw.search === "string" ? raw.search.trim() : "",
        level: typeof raw.level === "string" ? raw.level.trim() : "",
        module: typeof raw.module === "string" ? raw.module.trim() : "",
        hours: hours > 0 ? hours : 24,
      };
    }

    const api = {
      gridUrl: state.gridUrl,
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
        ingestGridItems: function (items) {
          const list = Array.isArray(items) ? items : [];
          detailCache.clear();
          const normalized = list.map((item) => normalizeLogItem(item));
          normalized.forEach((log) => {
            if (log && log.id) {
              detailCache.set(String(log.id), log);
            }
          });
          emit("logs:gridIngested", {
            count: normalized.length,
            state: cloneState(state),
          });
          return normalized;
        },
        loadStats: function (filters) {
          const params = normalizeStatsParams(filters);
          state.windowHours = params.hours;
          setLoading(true, { action: "loadStats" });
          return service
            .fetchStats(params)
            .then((response) => {
              const payload = response?.data || response || {};
              state.stats = payload;
              state.lastError = null;
              emit("logs:statsUpdated", {
                stats: payload,
                windowHours: state.windowHours,
                state: cloneState(state),
              });
              return payload;
            })
            .catch((error) => {
              handleError(error, { action: "loadStats" });
              emit("logs:statsError", {
                error,
                windowHours: state.windowHours,
                state: cloneState(state),
              });
              throw error;
            })
            .finally(() => {
              setLoading(false, { action: "loadStats" });
            });
        },
        loadLogDetail: function (logId) {
          const id = normalizeInt(logId, 0);
          if (!id) {
            return Promise.reject(new Error("LogsStore: loadLogDetail 需要 logId"));
          }
          const cached = detailCache.get(String(id));
          if (cached) {
            return Promise.resolve(cached);
          }
          return service.fetchLogDetail(id).then((response) => {
            const payload = response?.data || response || {};
            const log = payload.log || payload.data || payload || {};
            if (log && log.id) {
              detailCache.set(String(log.id), log);
            }
            emit("logs:detailLoaded", {
              log,
              state: cloneState(state),
            });
            return log;
          });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        detailCache.clear();
        state.stats = null;
        state.lastError = null;
        state.loading.stats = false;
      },
    };

    return api;
  }

  window.createLogsStore = createLogsStore;
})(window);

