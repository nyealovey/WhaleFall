(function (window) {
  "use strict";

  /**
   * @typedef {Object} TaskRunsService
   * @property {Function} getGridUrl
   * @property {Function} detail
   * @property {Function} cancel
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createTaskRunsStore: service is required");
    }
    const required = ["getGridUrl", "detail", "cancel"];
    required.forEach((method) => {
      // 固定白名单方法名, 避免动态键注入.
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error(`createTaskRunsStore: service.${method} 未实现`);
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createTaskRunsStore: 需要 mitt 实例");
    }
    return window.mitt();
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
      total: state.total,
      loading: { ...state.loading },
      lastError: state.lastError,
    };
  }

  /**
   * TaskRuns Store：承载运行中心的状态与 actions（总数、详情、取消等）。
   *
   * @param {Object} options
   * @param {TaskRunsService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createTaskRunsStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      gridUrl: service.getGridUrl(),
      total: 0,
      loading: {
        detail: false,
        cancel: false,
      },
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("taskRuns:error", {
        error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function setLoading(key, loading, meta) {
      const next = Boolean(loading);
      if (key === "detail") {
        state.loading.detail = next;
      } else if (key === "cancel") {
        state.loading.cancel = next;
      } else {
        return;
      }
      emit("taskRuns:loading", {
        loading: { ...state.loading },
        meta: meta || {},
        state: cloneState(state),
      });
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
        ingestGridPayload: function (payload) {
          const raw = payload && typeof payload === "object" ? payload : {};
          state.total = Number(raw.total) || 0;
          emit("taskRuns:totalUpdated", {
            total: state.total,
            state: cloneState(state),
          });
          return Array.isArray(raw.items) ? raw.items : [];
        },
        loadDetail: function (runId) {
          if (runId === undefined || runId === null || runId === "") {
            return Promise.reject(new Error("TaskRunsStore: loadDetail 需要 runId"));
          }
          setLoading("detail", true, { action: "loadDetail" });
          return service
            .detail(runId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "获取任务详情失败");
              const payload = resolved?.data || resolved || {};
              const session = {
                run: payload.run || {},
                items: Array.isArray(payload.items) ? payload.items : [],
              };
              state.lastError = null;
              emit("taskRuns:detailLoaded", {
                session,
                state: cloneState(state),
              });
              return session;
            })
            .catch((error) => {
              handleError(error, { action: "loadDetail" });
              throw error;
            })
            .finally(() => {
              setLoading("detail", false, { action: "loadDetail" });
            });
        },
        cancelRun: function (runId) {
          if (runId === undefined || runId === null || runId === "") {
            return Promise.reject(new Error("TaskRunsStore: cancelRun 需要 runId"));
          }
          setLoading("cancel", true, { action: "cancelRun" });
          return service
            .cancel(runId, {})
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "取消任务失败");
              const payload = resolved?.data || resolved || {};
              state.lastError = null;
              emit("taskRuns:cancelled", {
                runId,
                payload,
                state: cloneState(state),
              });
              return payload;
            })
            .catch((error) => {
              handleError(error, { action: "cancelRun" });
              throw error;
            })
            .finally(() => {
              setLoading("cancel", false, { action: "cancelRun" });
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.total = 0;
        state.lastError = null;
        state.loading.detail = false;
        state.loading.cancel = false;
      },
    };

    return api;
  }

  window.createTaskRunsStore = createTaskRunsStore;
})(window);
