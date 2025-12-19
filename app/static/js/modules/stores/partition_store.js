(function (window) {
  "use strict";

  /**
   * @typedef {Object} PartitionStats
   * @property {number} total_partitions - 分区总数
   * @property {string} total_size - 总大小，格式化字符串如 '1.5 GB'
   * @property {number} total_records - 总记录数
   * @property {string} status - 状态描述
   */

  /**
   * @typedef {Object} PartitionInfo
   * @property {string} name - 分区名称
   * @property {string} table - 表名
   * @property {string} table_type - 表类型
   * @property {string} display_name - 显示名称
   * @property {string} size - 格式化的大小
   * @property {number} size_bytes - 字节大小
   * @property {number} record_count - 记录数
   * @property {string} date - 日期字符串
   * @property {string} status - 状态：'current'、'past'、'future'
   */

  /**
   * @typedef {Object} MetricsPayload
   * @property {Array<string>} labels - 标签数组
   * @property {Array<Object>} datasets - 数据集数组
   */

  /**
   * @typedef {Object} PartitionMetrics
   * @property {string} periodType - 统计周期类型：'daily'、'weekly'、'monthly'
   * @property {MetricsPayload|Array} payload - 指标数据
   */

  /**
   * @typedef {Object} PartitionState
   * @property {PartitionStats} stats - 统计信息
   * @property {Array<PartitionInfo>} partitions - 分区列表
   * @property {PartitionMetrics} metrics - 指标数据
   * @property {Object} loading - 加载状态
   * @property {Error|null} lastError - 最后的错误
   */

  /**
   * @typedef {Object} PartitionService
   * @property {Function} fetchInfo - 获取分区信息
   * @property {Function} createPartition - 创建分区
   * @property {Function} cleanupPartitions - 清理分区
   * @property {Function} fetchCoreMetrics - 获取核心指标
   */

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
   *
   * 检查服务对象是否存在，并验证是否实现了所有必需的方法。
   * 如果校验失败，将抛出错误并阻止 store 初始化。
   *
   * @param {PartitionService} service - 服务对象
   * @return {PartitionService} 校验后的服务对象
   * @throws {Error} 当 service 为空或缺少必需方法时抛出
   */
  function ensureService(service) {
    if (!service) {
      throw new Error("createPartitionStore: service is required");
    }
    const REQUIRED_METHODS = ["fetchInfo", "createPartition", "cleanupPartitions", "fetchCoreMetrics"];
    REQUIRED_METHODS.forEach(function (method) {
      // 固定白名单方法名，避免动态键注入。
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error("createPartitionStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  /**
   * 获取 mitt 事件总线。
   *
   * 如果提供了 emitter 则直接返回，否则尝试从 window.mitt 创建新实例。
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
      throw new Error("createPartitionStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  /**
   * 深拷贝分区列表。
   *
   * @param {Array<PartitionInfo>} items - 分区对象数组
   * @return {Array<PartitionInfo>} 深拷贝后的分区数组
   */
  function clonePartitions(items) {
    return (items || []).map(function (partition) {
      return Object.assign({}, partition);
    });
  }

  /**
   * 拷贝 metrics 结构。
   *
   * @param {PartitionMetrics} metrics - 指标数据对象
   * @return {PartitionMetrics} 深拷贝后的指标数据
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
   * 简单的 JSON 深拷贝。
   *
   * @param {*} value - 要拷贝的值
   * @return {*} 深拷贝后的值
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
        if (["__proto__", "prototype", "constructor"].includes(key)) {
          return;
        }
        // eslint-disable-next-line security/detect-object-injection
        result[key] = cloneJSON(value[key]);
      });
      return result;
    }
    return value;
  }

  /**
   * 构造 state 快照。
   *
   * @param {PartitionState} state - 状态对象
   * @return {PartitionState} 深拷贝后的状态快照
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
   *
   * @param {Object} response - 后端响应对象
   * @return {Object} 包含 stats 和 partitions 的对象
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
   *
   * @param {Object} response - 后端响应对象
   * @return {MetricsPayload|Array} 指标数据
   */
  function extractMetrics(response) {
    const payload = response?.data?.data ?? response?.data ?? response ?? {};
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
   * 检查后端响应是否成功。
   *
   * @param {Object} response - 后端响应对象
   * @param {string} fallbackMessage - 默认错误消息
   * @return {Object} 响应对象
   * @throws {Error} 当 response.success 为 false 时抛出
   */
  function ensureSuccess(response, fallbackMessage) {
    if (response && response.success === false) {
      const error = new Error(response.message || fallbackMessage || "操作失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  /**
   * 创建分区管理 Store。
   *
   * 提供分区信息的状态管理、事件发布订阅和操作接口。
   * 支持加载分区信息、创建分区、清理分区和获取核心指标。
   *
   * @param {Object} options - 配置选项
   * @param {PartitionService} options.service - 分区服务实例
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @return {Object} Store API 对象
   * @throws {Error} 当 service 无效或 emitter 不可用时抛出
   *
   * @example
   * const store = createPartitionStore({
   *   service: new PartitionService(httpU),
   *   emitter: mitt()
   * });
   * store.init({ autoLoad: true });
   */
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

    /**
     * 统一发布分区 Store 事件。
     *
     * @param {string} eventName 事件名称。
     * @param {Object} [payload] 可选数据，默认附带 state 快照。
     * @returns {void}
     */
    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    /**
     * 更新 loading 状态并广播。
     *
     * @param {string} target 进入 loading 的模块。
     * @param {boolean} loading 当前 loading 状态。
     * @returns {void}
     */
  function emitLoading(target, loading) {
      const SAFE_LOADING_KEYS = new Set(["info", "metrics", "create", "cleanup"]);
      if (SAFE_LOADING_KEYS.has(target)) {
        // eslint-disable-next-line security/detect-object-injection
        state.loading[target] = loading;
      }
      emit(EVENT_NAMES.loading, {
        target: target,
        loading: Object.assign({}, state.loading),
        state: cloneState(state),
      });
    }

    /**
     * 统一处理分区相关错误。
     *
     * @param {Error|Object|string} error 错误对象。
     * @param {Object} meta 附加上下文信息。
     * @returns {void}
     */
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
