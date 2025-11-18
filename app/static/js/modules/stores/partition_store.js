(function (window) {
  "use strict";

  const EVENT_NAMES = {
    loading: "partitions:loading",
    infoUpdated: "partitions:infoUpdated",
    metricsUpdated: "partitions:metricsUpdated",
    createSuccess: "partitions:create:success",
    cleanupSuccess: "partitions:cleanup:success",
    error: "partitions:error",
  };

  /**
   * 校验 service 是否实现分区接口。
   */
  function ensureService(service) {
    if (!service) {
      throw new Error("createPartitionStore: service is required");
    }
    ["fetchInfo", "createPartition", "cleanupPartitions", "fetchCoreMetrics"].forEach(function (method) {
      if (typeof service[method] !== "function") {
        throw new Error("createPartitionStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  /**
   * 获取 mitt 事件总线。
   */
  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createPartitionStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  /**
   * 深拷贝分区列表。
   */
  function clonePartitions(items) {
    return (items || []).map(function (partition) {
      return Object.assign({}, partition);
    });
  }

  /**
   * 拷贝 metrics 结构。
   */
  function cloneMetrics(metrics) {
    if (!metrics) {
      return { periodType: "daily", payload: [] };
    }
    return {
      periodType: metrics.periodType || "daily",
      payload: Array.isArray(metrics.payload) || metrics.payload?.labels ? cloneJSON(metrics.payload) : [],
    };
  }

  /**
   * 简单位 JSON 深拷贝。
   */
  function cloneJSON(value) {
    if (value === null || value === undefined) {
      return value;
    }
    if (Array.isArray(value)) {
      return value.map(cloneJSON);
    }
    if (typeof value === "object") {
      const result = {};
      Object.keys(value).forEach(function (key) {
        result[key] = cloneJSON(value[key]);
      });
      return result;
    }
    return value;
  }

  /**
   * 构造 state 快照。
   */
  function cloneState(state) {
    return {
      stats: Object.assign({}, state.stats),
      partitions: clonePartitions(state.partitions),
      metrics: cloneMetrics(state.metrics),
      loading: Object.assign({}, state.loading),
      lastError: state.lastError,
    };
  }

  /**
   * 提取后端返回的分区信息。
   */
  function extractInfo(response) {
    const payload = response?.data?.data ?? response?.data ?? response ?? {};
    return {
      stats: {
        total_partitions: payload.total_partitions ?? 0,
        total_size: payload.total_size ?? "0 B",
        total_records: payload.total_records ?? 0,
        status: payload.status || "未知",
      },
      partitions: Array.isArray(payload.partitions) ? payload.partitions : [],
    };
  }

  /**
   * 提取核心指标数据。
   */
  function extractMetrics(response) {
    const payload = response?.data ?? response ?? {};
    if (payload.labels && payload.datasets) {
      return payload;
    }
    if (Array.isArray(payload)) {
      return payload;
    }
    if (Array.isArray(payload.metrics)) {
      return payload.metrics;
    }
    return [];
  }

  /**
   * 检查后端是否 success=false。
   */
  function ensureSuccess(response, fallbackMessage) {
    if (response && response.success === false) {
      const error = new Error(response.message || fallbackMessage || "操作失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  function createPartitionStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      stats: {
        total_partitions: 0,
        total_size: "0 B",
        total_records: 0,
        status: "未知",
      },
      partitions: [],
      metrics: {
        periodType: "daily",
        payload: [],
      },
      loading: {
        info: false,
        create: false,
        cleanup: false,
        metrics: false,
      },
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function emitLoading(target, loading) {
      state.loading[target] = loading;
      emit(EVENT_NAMES.loading, {
        target: target,
        loading: Object.assign({}, state.loading),
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit(EVENT_NAMES.error, {
        error: error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    const actions = {
      loadInfo: function (options) {
        const silent = Boolean(options && options.silent);
        if (!silent) {
          emitLoading("info", true);
        }
        return service
          .fetchInfo()
          .then(function (response) {
            const { stats, partitions } = extractInfo(response);
            state.stats = stats;
            state.partitions = clonePartitions(partitions);
            state.lastError = null;
            emit(EVENT_NAMES.infoUpdated, {
              stats: Object.assign({}, state.stats),
              partitions: clonePartitions(state.partitions),
              state: cloneState(state),
            });
            return cloneState(state);
          })
          .catch(function (error) {
            handleError(error, { target: "info" });
            throw error;
          })
          .finally(function () {
            if (!silent) {
              emitLoading("info", false);
            }
          });
      },
      loadCoreMetrics: function (options) {
        const params = options || {};
        const periodType = params.periodType || state.metrics.periodType || "daily";
        state.metrics.periodType = periodType;
        emitLoading("metrics", true);
        return service
          .fetchCoreMetrics({ period_type: periodType, days: params.days || 7 })
          .then(function (response) {
            const payload = extractMetrics(response);
            state.metrics = {
              periodType: periodType,
              payload: cloneJSON(payload),
            };
            state.lastError = null;
            emit(EVENT_NAMES.metricsUpdated, {
              metrics: cloneMetrics(state.metrics),
              state: cloneState(state),
            });
            return payload;
          })
          .catch(function (error) {
            handleError(error, { target: "metrics" });
            throw error;
          })
          .finally(function () {
            emitLoading("metrics", false);
          });
      },
      createPartition: function (payload) {
        const date = payload?.date;
        if (!date) {
          return Promise.reject(new Error("PartitionStore: createPartition 需要 date"));
        }
        emitLoading("create", true);
        return service
          .createPartition({ date: date })
          .then(function (response) {
            const result = ensureSuccess(response, "创建分区失败");
            state.lastError = null;
            emit(EVENT_NAMES.createSuccess, {
              response: result,
              date: date,
              state: cloneState(state),
            });
            return actions.loadInfo({ silent: true }).catch(function () {
              return result;
            });
          })
          .catch(function (error) {
            handleError(error, { target: "create" });
            throw error;
          })
          .finally(function () {
            emitLoading("create", false);
          });
      },
      cleanupPartitions: function (payload) {
        const months = payload?.retention_months;
        if (!Number.isFinite(months) || months < 1) {
          return Promise.reject(new Error("PartitionStore: cleanupPartitions 需要有效的 retention_months"));
        }
        emitLoading("cleanup", true);
        return service
          .cleanupPartitions({ retention_months: months })
          .then(function (response) {
            const result = ensureSuccess(response, "清理分区失败");
            state.lastError = null;
            emit(EVENT_NAMES.cleanupSuccess, {
              response: result,
              retention_months: months,
              state: cloneState(state),
            });
            return actions.loadInfo({ silent: true }).catch(function () {
              return result;
            });
          })
          .catch(function (error) {
            handleError(error, { target: "cleanup" });
            throw error;
          })
          .finally(function () {
            emitLoading("cleanup", false);
          });
      },
    };

    const api = {
      init: function (payload) {
        const shouldAutoLoad = payload?.autoLoad !== false;
        if (shouldAutoLoad) {
          return actions.loadInfo({ silent: Boolean(payload?.silent) });
        }
        return Promise.resolve(cloneState(state));
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
      actions: actions,
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.partitions = [];
      },
    };

    return api;
  }

  window.createPartitionStore = createPartitionStore;
})(window);
