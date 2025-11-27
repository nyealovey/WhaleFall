(function (global) {
  "use strict";

  const EVENT_NAMES = {
    trendLoading: "databases:trend:loading",
    trendLoaded: "databases:trend:loaded",
    error: "databases:error",
  };

  function ensureService(service) {
    if (!service || typeof service.fetchCapacityTrend !== "function") {
      throw new Error("createDatabaseStore: service.fetchCapacityTrend 未实现");
    }
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!global.mitt) {
      throw new Error("createDatabaseStore: 需要 mitt 实例");
    }
    return global.mitt();
  }

  /**
   * 创建数据库台账 store。
   *
   * @param {Object} options store 配置
   * @param {Object} options.service HTTP 服务实例
   * @param {Object} [options.emitter] mitt 事件实例
   * @returns {Object} store 实例
   */
  function createDatabaseStore({ service, emitter }) {
    const resolvedService = ensureService(service);
    const eventBus = ensureEmitter(emitter);
    const state = {
      trend: {
        loading: false,
        database: null,
        points: [],
        lastError: null,
      },
    };

    function emit(eventName, payload) {
      eventBus.emit(eventName, payload);
    }

    function fetchCapacityTrend(databaseId, params) {
      state.trend.loading = true;
      emit(EVENT_NAMES.trendLoading, { databaseId });
      return resolvedService
        .fetchCapacityTrend(databaseId, params)
        .then((response) => {
          const data = response?.data || response || {};
          state.trend = {
            loading: false,
            database: data.database || null,
            points: data.points || [],
            lastError: null,
          };
          emit(EVENT_NAMES.trendLoaded, state.trend);
          return data;
        })
        .catch((error) => {
          state.trend.loading = false;
          state.trend.lastError = error;
          emit(EVENT_NAMES.error, error);
          throw error;
        });
    }

    function subscribe(eventName, handler) {
      eventBus.on(eventName, handler);
    }

    function unsubscribe(eventName, handler) {
      eventBus.off(eventName, handler);
    }

    function getState() {
      return JSON.parse(JSON.stringify(state));
    }

    return {
      EVENTS: EVENT_NAMES,
      fetchCapacityTrend,
      subscribe,
      unsubscribe,
      getState,
    };
  }

  global.createDatabaseStore = createDatabaseStore;
})(window);
