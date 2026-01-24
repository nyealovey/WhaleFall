(function (window) {
  "use strict";

  /**
   * @typedef {Object} AccountChangeLogsService
   * @property {Function} getGridUrl
   * @property {Function} fetchStats
   * @property {Function} fetchDetail
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createAccountChangeLogsStore: service is required");
    }
    const required = ["getGridUrl", "fetchStats", "fetchDetail"];
    required.forEach((method) => {
      if (typeof service[method] !== "function") {
        throw new Error(`createAccountChangeLogsStore: service.${method} 未实现`);
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createAccountChangeLogsStore: 需要 mitt 实例");
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

  function normalizeItem(item) {
    const raw = item && typeof item === "object" ? item : {};
    return {
      id: raw?.id,
      account_id: raw?.account_id ?? null,
      instance_id: raw?.instance_id ?? null,
      instance_name: raw?.instance_name || "",
      db_type: raw?.db_type || "",
      username: raw?.username || "",
      change_type: raw?.change_type || "",
      status: raw?.status || "",
      message: raw?.message || "",
      change_time: raw?.change_time || "",
      session_id: raw?.session_id ?? null,
      privilege_diff_count: raw?.privilege_diff_count ?? 0,
      other_diff_count: raw?.other_diff_count ?? 0,
    };
  }

  function ensureSuccessResponse(resp, fallbackMessage) {
    if (resp && resp.success === false) {
      const error = new Error(resp.message || resp.error || fallbackMessage || "操作失败");
      error.raw = resp;
      throw error;
    }
    return resp;
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
   * AccountChangeLogs Store：承载账户变更历史的状态与 actions（统计、详情、缓存等）。
   *
   * @param {Object} options
   * @param {AccountChangeLogsService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createAccountChangeLogsStore(options) {
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

    const cache = new Map();

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function setLoading(loading, meta) {
      state.loading.stats = Boolean(loading);
      emit("accountChangeLogs:loading", {
        loading: { ...state.loading },
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("accountChangeLogs:error", {
        error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    const api = {
      gridUrl: state.gridUrl,
      getCachedMeta: function (logId) {
        const id = (logId || "").toString();
        return cache.get(id) || null;
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
        ingestGridItems: function (items) {
          const list = Array.isArray(items) ? items : [];
          cache.clear();
          const normalized = list.map((item) => normalizeItem(item));
          normalized.forEach((log) => {
            if (log && log.id !== undefined && log.id !== null && log.id !== "") {
              cache.set(String(log.id), log);
            }
          });
          emit("accountChangeLogs:gridIngested", {
            count: normalized.length,
            state: cloneState(state),
          });
          return normalized;
        },
        loadStats: function (filters) {
          const hours = normalizeInt(filters?.hours, 24);
          state.windowHours = hours > 0 ? hours : 24;
          setLoading(true, { action: "loadStats" });
          return service
            .fetchStats({ hours: filters?.hours })
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "加载账户变更统计失败");
              const payload = resolved?.data || resolved || {};
              state.stats = payload;
              state.lastError = null;
              emit("accountChangeLogs:statsUpdated", {
                stats: payload,
                windowHours: state.windowHours,
                state: cloneState(state),
              });
              return payload;
            })
            .catch((error) => {
              handleError(error, { action: "loadStats" });
              emit("accountChangeLogs:statsError", {
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
        loadDetail: function (logId) {
          const id = (logId || "").toString();
          if (!id) {
            return Promise.reject(new Error("AccountChangeLogsStore: loadDetail 需要 logId"));
          }
          return service.fetchDetail(id).then((resp) => {
            const resolved = ensureSuccessResponse(resp, "获取详情失败");
            const payload = resolved?.data || resolved || {};
            const log = payload?.log || null;
            emit("accountChangeLogs:detailLoaded", {
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
        cache.clear();
        state.stats = null;
        state.lastError = null;
        state.loading.stats = false;
      },
    };

    return api;
  }

  window.createAccountChangeLogsStore = createAccountChangeLogsStore;
})(window);

