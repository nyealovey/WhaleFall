(function (window) {
  "use strict";

  /**
   * @typedef {Object} AccountsStatisticsService
   * @property {Function} fetchStatistics
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createAccountsStatisticsStore: service is required");
    }
    if (typeof service.fetchStatistics !== "function") {
      throw new Error("createAccountsStatisticsStore: service.fetchStatistics 未实现");
    }
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createAccountsStatisticsStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function cloneState(state) {
    return {
      stats: state.stats ? { ...state.stats } : null,
      loading: Boolean(state.loading),
      lastError: state.lastError,
    };
  }

  /**
   * AccountsStatistics Store：承载账户统计刷新 actions。
   *
   * @param {Object} options
   * @param {AccountsStatisticsService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createAccountsStatisticsStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      stats: null,
      loading: false,
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function setLoading(loading, meta) {
      state.loading = Boolean(loading);
      emit("accountsStatistics:loading", {
        loading: state.loading,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("accountsStatistics:error", {
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
        refresh: function () {
          setLoading(true, { action: "refresh" });
          return service
            .fetchStatistics()
            .then((payload) => {
              const stats = payload?.data?.stats ?? payload?.stats ?? null;
              state.stats = stats && typeof stats === "object" ? { ...stats } : {};
              state.lastError = null;
              emit("accountsStatistics:updated", {
                stats: state.stats,
                state: cloneState(state),
              });
              return state.stats;
            })
            .catch((error) => {
              handleError(error, { action: "refresh" });
              throw error;
            })
            .finally(() => setLoading(false, { action: "refresh" }));
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.stats = null;
        state.lastError = null;
        state.loading = false;
      },
    };

    return api;
  }

  window.createAccountsStatisticsStore = createAccountsStatisticsStore;
})(window);

