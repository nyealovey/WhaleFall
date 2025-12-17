(function (window) {
  "use strict";

  /**
   * @typedef {Object} InstanceMeta
   * @property {number} id - 实例 ID
   * @property {string} name - 实例名称
   * @property {string|null} dbType - 数据库类型
   */

  /**
   * @typedef {Object} InstanceStats
   * @property {number} total_instances - 实例总数
   * @property {number} active_instances - 活跃实例数
   * @property {number} inactive_instances - 非活跃实例数
   * @property {number} total_accounts - 账户总数
   * @property {number} total_databases - 数据库总数
   * @property {number} db_types_count - 数据库类型数
   */

  /**
   * @typedef {Object} InstanceState
   * @property {Object} filters - 筛选条件
   * @property {Array<InstanceMeta>} instances - 实例列表
   * @property {Set<number>} availableInstanceIds - 可用实例 ID 集合
   * @property {Set<number>} selection - 已选择实例 ID 集合
   * @property {InstanceStats} stats - 统计信息
   * @property {Object} loading - 加载状态
   * @property {Object} operations - 操作状态
   * @property {Object|null} uploadResult - 上传结果
   * @property {Error|null} lastError - 最后的错误
   */

  /**
   * @typedef {Object} InstanceService
   * @property {Function} syncInstanceAccounts - 同步实例账户
   * @property {Function} syncInstanceCapacity - 同步实例容量
   * @property {Function} syncAllAccounts - 同步所有账户
   * @property {Function} batchDeleteInstances - 批量删除实例
   * @property {Function} batchCreateInstances - 批量创建实例
   * @property {Function} fetchStatistics - 获取统计信息
   */

  const EVENT_NAMES = {
    updated: "instances:updated",
    selectionChanged: "instances:selectionChanged",
    filtersUpdated: "instances:filtersUpdated",
    statsUpdated: "instances:statsUpdated",
    loading: "instances:loading",
    operation: "instances:operation",
    batchDeleteSuccess: "instances:batchDelete:success",
    batchCreateSuccess: "instances:batchCreate:success",
    error: "instances:error",
  };

  /**
   * 校验 service 是否具备实例 store 依赖的方法。
   *
   * @param {InstanceService} service - 服务对象
   * @return {InstanceService} 校验后的服务对象
   * @throws {Error} 当 service 为空或缺少必需方法时抛出
   */
  function ensureService(service) {
    if (!service) {
      throw new Error("createInstanceStore: service is required");
    }
    [
      "syncInstanceAccounts",
      "syncInstanceCapacity",
      "syncAllAccounts",
      "batchDeleteInstances",
      "batchCreateInstances",
      "fetchStatistics",
    ].forEach(function (method) {
      // 固定白名单方法名，避免动态键注入。
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error("createInstanceStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  /**
   * 获取 mitt 事件总线实例。
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
      throw new Error("createInstanceStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const LOADING_KEYS = new Set(["stats", "batchDelete", "batchCreate"]);
  const OPERATION_KEYS = new Set(["syncAccounts", "syncCapacity", "syncAllAccounts"]);
  const isSafeKey = (key) => typeof key === "string" && !UNSAFE_KEYS.includes(key);

  function setMapValue(map, key, value, allowedKeys) {
    if (!isSafeKey(key)) {
      return;
    }
    if (allowedKeys && !allowedKeys.has(key)) {
      return;
    }
    // eslint-disable-next-line security/detect-object-injection
    map[key] = value;
  }

  function addToSet(targetSet, value) {
    if (value === null || value === undefined) {
      return;
    }
    targetSet.add(value);
  }

  /**
   * 将输入转换为 ID 数组。
   *
   * @param {*|Array|Set} ids 待标准化的单个 ID、数组或 Set。
   * @returns {Array<number|string>} 由原始输入转换得到的 ID 数组。
   */
  function normalizeIds(ids) {
    if (!ids) {
      return [];
    }
    if (ids instanceof Set) {
      return Array.from(ids);
    }
    if (!Array.isArray(ids)) {
      return [ids];
    }
    return ids;
  }

  /**
   * 安全解析 ID。
   *
   * @param {*} value 任意可表示 ID 的值。
   * @returns {number|null} 有效的数字 ID，无法转换时返回 null。
   */
  function toNumericId(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  /**
   * 将实例元数据统一为 {id,name,dbType}。
   *
   * @param {Array<InstanceMeta|number|string>} items 原始实例列表。
   * @returns {Array<InstanceMeta>} 规范化后的实例数组。
   */
  function normalizeInstanceMeta(items) {
    return (items || [])
      .map(function (item) {
        if (typeof item === "number" || typeof item === "string") {
          const id = toNumericId(item);
          if (id === null) {
            return null;
          }
          return { id: id, name: "" };
        }
        const id = toNumericId(item?.id);
        if (id === null) {
          return null;
        }
        return {
          id: id,
          name: item.name || item.label || "",
          dbType: item.dbType || item.db_type || null,
        };
      })
      .filter(Boolean);
  }

  /**
   * 深拷贝实例元数据数组。
   *
   * @param {Array<InstanceMeta|number|string>} items 原始实例列表。
   * @returns {Array<InstanceMeta>} 新的实例元数据数组。
   */
  function cloneInstancesMeta(items) {
    return normalizeInstanceMeta(items).map(function (item) {
      return Object.assign({}, item);
    });
  }

  /**
   * 生成 state 副本，供事件 payload 使用。
   *
   * @param {InstanceState} state 当前状态。
   * @returns {InstanceState} 深拷贝后的状态快照。
   */
  function cloneState(state) {
    return {
      filters: Object.assign({}, state.filters),
      instances: cloneInstancesMeta(state.instances),
      availableInstanceIds: Array.from(state.availableInstanceIds),
      selection: Array.from(state.selection),
      stats: Object.assign({}, state.stats),
      loading: Object.assign({}, state.loading),
      operations: {
        syncAccounts: Array.from(state.operations.syncAccounts),
        syncCapacity: Array.from(state.operations.syncCapacity),
        syncAllAccounts: state.operations.syncAllAccounts,
      },
      uploadResult: state.uploadResult ? Object.assign({}, state.uploadResult) : null,
      lastError: state.lastError,
    };
  }

  /**
   * 从响应中提取统计字段。
   *
   * @param {Object} response 后端响应对象。
   * @returns {InstanceStats|Object} 统计信息。
   */
  function extractStats(response) {
    const payload = response?.data ?? response ?? {};
    if (payload.stats) {
      return Object.assign({}, payload.stats);
    }
    return Object.assign({}, payload);
  }

  /**
   * 后端返回 success=false 时抛错。
   *
   * @param {Object} response 后端响应对象。
   * @param {string} [fallbackMessage] 默认错误提示。
   * @returns {Object} 原始响应。
   * @throws {Error} 当 success=false 时抛出错误。
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
   * 创建实例管理 Store。
   *
   * 提供实例的状态管理、选择管理、同步操作和批量操作。
   * 支持实例筛选、统计信息加载、账户同步、容量同步等功能。
   *
   * @param {Object} options - 配置选项
   * @param {InstanceService} options.service - 实例服务实例
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @param {Object} [options.initialFilters] - 初始筛选条件
   * @param {Array<InstanceMeta>} [options.instances] - 初始实例列表
   * @param {Array<number>} [options.availableInstanceIds] - 可用实例 ID 列表
   * @param {Array<number>} [options.initialSelection] - 初始选择的实例 ID 列表
   * @param {InstanceStats} [options.initialStats] - 初始统计信息
   * @return {Object} Store API 对象
   * @throws {Error} 当 service 无效或 emitter 不可用时抛出
   *
   * @example
   * const store = createInstanceStore({
   *   service: new InstanceManagementService(httpU),
   *   emitter: mitt()
   * });
   * store.init({ autoLoad: true });
   */
  function createInstanceStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      filters: Object.assign({}, opts.initialFilters || {}),
      instances: cloneInstancesMeta(opts.instances || []),
      availableInstanceIds: new Set(),
      selection: new Set(),
      stats: Object.assign(
        {
          total_instances: 0,
          active_instances: 0,
          inactive_instances: 0,
          total_accounts: 0,
          total_databases: 0,
          db_types_count: 0,
        },
        opts.initialStats || {},
      ),
      loading: {
        stats: false,
        batchDelete: false,
        batchCreate: false,
      },
      operations: {
        syncAccounts: new Set(),
        syncCapacity: new Set(),
        syncAllAccounts: false,
      },
      uploadResult: null,
      lastError: null,
    };

    if (opts.availableInstanceIds) {
      normalizeIds(opts.availableInstanceIds).forEach(function (value) {
        const id = toNumericId(value);
        if (id !== null) {
          addToSet(state.availableInstanceIds, id);
        }
      });
    }
    normalizeIds(opts.initialSelection).forEach(function (value) {
      const id = toNumericId(value);
      if (id !== null) {
        addToSet(state.selection, id);
      }
    });

    /**
     * 发布 mitt 事件并附带最新状态。
     *
     * @param {string} eventName 事件名称。
     * @param {Object} [payload] 可选 payload，默认为 state 快照。
     * @returns {void}
     */
    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    /**
     * 统一处理实例相关错误。
     *
     * @param {Error|Object|string} error 捕获到的异常。
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

    /**
     * 当选择集发生变化时广播变更事件。
     *
     * @param {string} [reason="update"] 触发原因，便于上层区分来源。
     * @returns {void}
     */
    function emitSelectionChanged(reason) {
      emit(EVENT_NAMES.selectionChanged, {
        reason: reason || "update",
        selectedIds: Array.from(state.selection),
        availableInstanceIds: Array.from(state.availableInstanceIds),
        state: cloneState(state),
      });
    }

    /**
     * 更新当前选择集，仅保留合法实例 ID。
     *
     * @param {Iterable<number|string>} ids 待应用的 ID 列表。
     * @param {string} [reason] 触发原因。
     * @returns {boolean} 选择集发生变化时返回 true。
     */
    function applySelection(ids, reason) {
      const normalized = new Set();
      normalizeIds(ids).forEach(function (value) {
        const id = toNumericId(value);
        if (id !== null && state.availableInstanceIds.has(id)) {
          normalized.add(id);
        }
      });

      let changed = false;
      state.selection.forEach(function (id) {
        if (!normalized.has(id)) {
          state.selection.delete(id);
          changed = true;
        }
      });
      normalized.forEach(function (id) {
        if (!state.selection.has(id)) {
          state.selection.add(id);
          changed = true;
        }
      });
      if (changed) {
        emitSelectionChanged(reason);
      }
      return changed;
    }

    /**
     * 从选择集移除已不在可选范围内的实例。
     *
     * @param {string} [reason="prune"] 触发原因，默认为 prune。
     * @returns {void}
     */
    function pruneSelection(reason) {
      let changed = false;
      state.selection.forEach(function (id) {
        if (!state.availableInstanceIds.has(id)) {
          state.selection.delete(id);
          changed = true;
        }
      });
      if (changed) {
        emitSelectionChanged(reason || "prune");
      }
    }

    /**
     * 广播 loading 状态，供 UI 响应。
     *
     * @param {string} target 当前进入 loading 的模块名称。
     * @returns {void}
     */
    function emitLoading(target) {
      emit(EVENT_NAMES.loading, {
        target: target,
        loading: Object.assign({}, state.loading),
        state: cloneState(state),
      });
    }

    /**
     * 标记某实例的异步操作状态。
     *
     * @param {string} operation 操作名称，如 syncAccounts。
     * @param {number|string} instanceId 实例 ID。
     * @param {boolean} inProgress 是否进入执行状态。
     * @returns {void}
     */
    function markOperation(operation, instanceId, inProgress) {
      const targetSet = OPERATION_KEYS.has(operation)
        ? state.operations[operation] // eslint-disable-line security/detect-object-injection
        : null;
      if (!targetSet || typeof targetSet.add !== "function") {
        return;
      }
      const numeric = toNumericId(instanceId);
      if (numeric === null) {
        return;
      }
      if (inProgress) {
        targetSet.add(numeric);
      } else {
        targetSet.delete(numeric);
      }
      emit(EVENT_NAMES.operation, {
        operation: operation,
        instanceId: numeric,
        inProgress: inProgress,
        operations: {
          syncAccounts: Array.from(state.operations.syncAccounts),
          syncCapacity: Array.from(state.operations.syncCapacity),
          syncAllAccounts: state.operations.syncAllAccounts,
        },
        state: cloneState(state),
      });
    }

    const actions = {
      setAvailableInstances: function (items) {
        state.instances = cloneInstancesMeta(items);
        state.availableInstanceIds = new Set(
          state.instances.map(function (instance) {
            return instance.id;
          }),
        );
        pruneSelection("availableChanged");
        emit(EVENT_NAMES.updated, {
          instances: cloneInstancesMeta(state.instances),
          state: cloneState(state),
        });
      },
      setSelection: function (ids, options) {
        applySelection(ids, options?.reason || "setSelection");
      },
      toggleSelection: function (instanceId) {
        const id = toNumericId(instanceId);
        if (id === null || !state.availableInstanceIds.has(id)) {
          return;
        }
        if (state.selection.has(id)) {
          state.selection.delete(id);
        } else {
          state.selection.add(id);
        }
        emitSelectionChanged("toggle");
      },
      clearSelection: function () {
        if (!state.selection.size) {
          return;
        }
        state.selection.clear();
        emitSelectionChanged("clear");
      },
      selectAll: function () {
        applySelection(Array.from(state.availableInstanceIds), "selectAll");
      },
      applyFilters: function (filters) {
        state.filters = Object.assign({}, filters || {});
        emit(EVENT_NAMES.filtersUpdated, {
          filters: Object.assign({}, state.filters),
          state: cloneState(state),
        });
      },
      loadStats: function (options) {
        const silent = Boolean(options && options.silent);
        if (!silent) {
          setMapValue(state.loading, "stats", true, LOADING_KEYS);
          emitLoading("stats");
        }
        return service
          .fetchStatistics()
          .then(function (response) {
            const stats = extractStats(response);
            state.stats = Object.assign({}, stats);
            state.lastError = null;
            emit(EVENT_NAMES.statsUpdated, {
              stats: Object.assign({}, state.stats),
              state: cloneState(state),
            });
            return stats;
          })
          .catch(function (error) {
            handleError(error, { target: "stats" });
            throw error;
          })
          .finally(function () {
            if (!silent) {
              setMapValue(state.loading, "stats", false, LOADING_KEYS);
              emitLoading("stats");
            }
          });
      },
      syncInstanceAccounts: function (instanceId, options) {
        const id = toNumericId(instanceId);
        if (id === null) {
          return Promise.reject(new Error("InstanceStore: 需要 instanceId"));
        }
        markOperation("syncAccounts", id, true);
        return service
          .syncInstanceAccounts(id, options)
          .then(function (response) {
            ensureSuccess(response, "同步账户失败");
            state.lastError = null;
            emit("instances:syncAccounts:success", {
              instanceId: id,
              response: response,
              state: cloneState(state),
            });
            return response;
          })
          .catch(function (error) {
            handleError(error, { target: "syncAccounts", instanceId: id });
            throw error;
          })
          .finally(function () {
            markOperation("syncAccounts", id, false);
          });
      },
      syncInstanceCapacity: function (instanceId) {
        const id = toNumericId(instanceId);
        if (id === null) {
          return Promise.reject(new Error("InstanceStore: 需要 instanceId"));
        }
        markOperation("syncCapacity", id, true);
        return service
          .syncInstanceCapacity(id)
          .then(function (response) {
            ensureSuccess(response, "同步容量失败");
            state.lastError = null;
            emit("instances:syncCapacity:success", {
              instanceId: id,
              response: response,
              state: cloneState(state),
            });
            return response;
          })
          .catch(function (error) {
            handleError(error, { target: "syncCapacity", instanceId: id });
            throw error;
          })
          .finally(function () {
            markOperation("syncCapacity", id, false);
          });
      },
      syncAllAccounts: function () {
        if (state.operations.syncAllAccounts) {
          return Promise.resolve();
        }
        state.operations.syncAllAccounts = true;
        emit(EVENT_NAMES.operation, {
          operation: "syncAllAccounts",
          inProgress: true,
          state: cloneState(state),
        });
        return service
          .syncAllAccounts()
          .then(function (response) {
            ensureSuccess(response, "同步所有账户失败");
            state.lastError = null;
            emit("instances:syncAllAccounts:success", {
              response: response,
              state: cloneState(state),
            });
            return response;
          })
          .catch(function (error) {
            handleError(error, { target: "syncAllAccounts" });
            throw error;
          })
          .finally(function () {
            state.operations.syncAllAccounts = false;
            emit(EVENT_NAMES.operation, {
              operation: "syncAllAccounts",
              inProgress: false,
              state: cloneState(state),
            });
          });
      },
      batchDeleteSelected: function () {
        if (!state.selection.size) {
          return Promise.reject(new Error("InstanceStore: 未选择任何实例"));
        }
        const ids = Array.from(state.selection);
        setMapValue(state.loading, "batchDelete", true, LOADING_KEYS);
        emitLoading("batchDelete");
        return service
          .batchDeleteInstances(ids)
          .then(function (response) {
            const result = ensureSuccess(response, "批量删除实例失败");
            state.selection.clear();
            state.lastError = null;
            emitSelectionChanged("batchDelete");
            emit(EVENT_NAMES.batchDeleteSuccess, {
              instanceIds: ids.slice(),
              response: result,
              state: cloneState(state),
            });
            return result;
          })
          .catch(function (error) {
            handleError(error, { target: "batchDelete", instanceIds: ids.slice() });
            throw error;
          })
          .finally(function () {
            setMapValue(state.loading, "batchDelete", false, LOADING_KEYS);
            emitLoading("batchDelete");
          });
      },
      batchCreateInstances: function (formData) {
        if (!(formData instanceof FormData)) {
          return Promise.reject(new Error("InstanceStore: 需要 FormData 进行批量创建"));
        }
        setMapValue(state.loading, "batchCreate", true, LOADING_KEYS);
        emitLoading("batchCreate");
        return service
          .batchCreateInstances(formData)
          .then(function (response) {
            const result = ensureSuccess(response, "批量创建实例失败");
            state.uploadResult = {
              message: result.message || "",
              errors: Array.isArray(result.errors) ? result.errors.slice() : [],
            };
            state.lastError = null;
            emit(EVENT_NAMES.batchCreateSuccess, {
              response: result,
              uploadResult: Object.assign({}, state.uploadResult),
              state: cloneState(state),
            });
            return result;
          })
          .catch(function (error) {
            handleError(error, { target: "batchCreate" });
            throw error;
          })
          .finally(function () {
            setMapValue(state.loading, "batchCreate", false, LOADING_KEYS);
            emitLoading("batchCreate");
          });
      },
    };

    const api = {
      init: function (payload) {
        if (payload && Array.isArray(payload.instances)) {
          actions.setAvailableInstances(payload.instances);
        } else if (state.instances.length) {
          actions.setAvailableInstances(state.instances);
        }
        if (payload && payload.filters) {
          actions.applyFilters(payload.filters);
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
        state.selection.clear();
        state.instances = [];
        state.availableInstanceIds.clear();
      },
    };

    return api;
  }

  window.createInstanceStore = createInstanceStore;
})(window);
