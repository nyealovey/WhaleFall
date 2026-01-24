(function (window) {
  "use strict";

  /**
   * @typedef {Object} DashboardService
   * @property {Function} fetchCharts
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createDashboardStore: service is required");
    }
    if (typeof service.fetchCharts !== "function") {
      throw new Error("createDashboardStore: service.fetchCharts 未实现");
    }
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createDashboardStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function cloneState(state) {
    return {
      logTrend: Array.isArray(state.logTrend) ? state.logTrend.slice() : [],
      loading: { ...state.loading },
      lastError: state.lastError,
    };
  }

  /**
   * Dashboard Store：承载仪表盘图表数据加载 actions。
   *
   * @param {Object} options
   * @param {DashboardService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createDashboardStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      logTrend: [],
      loading: {
        logTrend: false,
      },
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function setLoading(loading, meta) {
      state.loading.logTrend = Boolean(loading);
      emit("dashboard:loading", {
        loading: { ...state.loading },
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("dashboard:error", {
        error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    const api = {
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
        loadLogTrend: function () {
          setLoading(true, { action: "loadLogTrend" });
          return service
            .fetchCharts({ type: "logs" })
            .then((data) => {
              const payload = data?.data ?? data ?? {};
              const trend = Array.isArray(payload.log_trend) ? payload.log_trend : [];
              state.logTrend = trend;
              state.lastError = null;
              emit("dashboard:logTrendUpdated", {
                logTrend: trend,
                state: cloneState(state),
              });
              return trend;
            })
            .catch((error) => {
              handleError(error, { action: "loadLogTrend" });
              throw error;
            })
            .finally(() => {
              setLoading(false, { action: "loadLogTrend" });
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.logTrend = [];
        state.lastError = null;
        state.loading.logTrend = false;
      },
    };

    return api;
  }

  window.createDashboardStore = createDashboardStore;
})(window);

