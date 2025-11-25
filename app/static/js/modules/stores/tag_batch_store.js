(function (window) {
  "use strict";

  /**
   * 验证 service 是否实现批量打标签所需的方法。
   *
   * @param {Object} service - 服务对象
   * @param {Function} service.listInstances - 获取实例列表的方法
   * @param {Function} service.listAllTags - 获取所有标签的方法
   * @param {Function} service.batchAssign - 批量分配标签的方法
   * @param {Function} service.batchRemoveAll - 批量移除标签的方法
   * @return {Object} 校验后的服务对象
   * @throws {Error} 当 service 为空或缺少必需方法时抛出
   */
  function ensureService(service) {
    if (!service) {
      throw new Error("createTagBatchStore: service is required");
    }
    ["listInstances", "listAllTags", "batchAssign", "batchRemoveAll"].forEach(function (method) {
      if (typeof service[method] !== "function") {
        throw new Error("createTagBatchStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  /**
   * 获取 mitt 事件总线。
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
      throw new Error("createTagBatchStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  /**
   * 拷贝 state，以便事件 payload 使用。
   *
   * @param {Object} state - 状态对象
   * @return {Object} 状态对象的拷贝
   */
  function cloneState(state) {
    return {
      instances: state.instances.slice(),
      tags: state.tags.slice(),
      selectedInstances: Array.from(state.selectedInstances),
      selectedTags: Array.from(state.selectedTags),
      mode: state.mode,
      loading: Object.assign({}, state.loading),
      lastError: state.lastError,
    };
  }

  /**
   * 将 id 列表转换为数值数组。
   *
   * @param {Array} ids - ID 数组
   * @return {Array} 规范化后的数字 ID 数组
   */
  function normalizeIds(ids) {
    if (!Array.isArray(ids)) {
      return [];
    }
    return ids
      .map(function (value) {
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : null;
      })
      .filter(function (value) {
        return value !== null;
      });
  }

  /**
   * 创建标签批量分配状态管理 Store。
   *
   * 提供批量为实例分配或移除标签的功能，包括实例选择、标签选择和批量操作。
   *
   * @param {Object} options - 配置选项
   * @param {Object} options.service - 标签批量操作服务对象
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @param {string} [options.initialMode='assign'] - 初始模式，'assign' 或 'remove'
   * @return {Object} Store API 对象
   *
   * @example
   * const store = createTagBatchStore({
   *   service: tagBatchService,
   *   initialMode: 'assign'
   * });
   * store.init().then(() => {
   *   console.log(store.getState());
   * });
   */
  function createTagBatchStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      instances: [],
      tags: [],
      selectedInstances: new Set(),
      selectedTags: new Set(),
      mode: opts.initialMode === "remove" ? "remove" : "assign",
      loading: {
        instances: false,
        tags: false,
        operation: false,
      },
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("batchAssign:error", {
        error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function setInstances(instances) {
      state.instances = Array.isArray(instances) ? instances.slice() : [];
      const validIds = new Set(state.instances.map(function (item) {
        return item.id;
      }));
      state.selectedInstances.forEach(function (id) {
        if (!validIds.has(id)) {
          state.selectedInstances.delete(id);
        }
      });
      emit("batchAssign:instancesUpdated", cloneState(state));
    }

    function setTags(tags) {
      state.tags = Array.isArray(tags) ? tags.slice() : [];
      const validIds = new Set(state.tags.map(function (item) {
        return item.id;
      }));
      state.selectedTags.forEach(function (id) {
        if (!validIds.has(id)) {
          state.selectedTags.delete(id);
        }
      });
      emit("batchAssign:tagsUpdated", cloneState(state));
    }

    function emitSelection(kind) {
      emit("batchAssign:selectionChanged", {
        kind: kind,
        selectedInstances: Array.from(state.selectedInstances),
        selectedTags: Array.from(state.selectedTags),
        state: cloneState(state),
      });
    }

    function setSelection(setRef, ids, checked) {
      const incoming = normalizeIds(ids);
      incoming.forEach(function (id) {
        if (checked) {
          setRef.add(id);
        } else {
          setRef.delete(id);
        }
      });
    }

    const api = {
      init: function () {
        return api.actions.loadAll();
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
        loadInstances: function () {
          state.loading.instances = true;
          emit("batchAssign:loading", { target: "instances", state: cloneState(state) });
          return service
            .listInstances()
            .then(function (response) {
              const payload = response?.data ?? response ?? {};
              const instances = Array.isArray(payload.instances) ? payload.instances : [];
              setInstances(instances);
              state.lastError = null;
              return cloneState(state);
            })
            .catch(function (error) {
              handleError(error, { target: "instances" });
              throw error;
            })
            .finally(function () {
              state.loading.instances = false;
            });
        },
        loadTags: function () {
          state.loading.tags = true;
          emit("batchAssign:loading", { target: "tags", state: cloneState(state) });
          return service
            .listAllTags()
            .then(function (response) {
              const payload = response?.data ?? response ?? {};
              const tags = Array.isArray(payload.tags) ? payload.tags : [];
              setTags(tags);
              state.lastError = null;
              return cloneState(state);
            })
            .catch(function (error) {
              handleError(error, { target: "tags" });
              throw error;
            })
            .finally(function () {
              state.loading.tags = false;
            });
        },
        loadAll: function () {
          return Promise.all([api.actions.loadInstances(), api.actions.loadTags()]);
        },
        setMode: function (mode) {
          if (mode !== "assign" && mode !== "remove") {
            return;
          }
          if (state.mode === mode) {
            return;
          }
          state.mode = mode;
          emit("batchAssign:modeChanged", {
            mode: state.mode,
            state: cloneState(state),
          });
        },
        toggleInstance: function (instanceId) {
          const numericId = Number(instanceId);
          if (!Number.isFinite(numericId)) {
            return;
          }
          if (state.selectedInstances.has(numericId)) {
            state.selectedInstances.delete(numericId);
          } else {
            state.selectedInstances.add(numericId);
          }
          emitSelection("instance");
        },
        toggleTag: function (tagId) {
          const numericId = Number(tagId);
          if (!Number.isFinite(numericId)) {
            return;
          }
          if (state.selectedTags.has(numericId)) {
            state.selectedTags.delete(numericId);
          } else {
            state.selectedTags.add(numericId);
          }
          emitSelection("tag");
        },
        setInstanceSelection: function (ids, checked) {
          setSelection(state.selectedInstances, ids, Boolean(checked));
          emitSelection("instance");
        },
        setTagSelection: function (ids, checked) {
          setSelection(state.selectedTags, ids, Boolean(checked));
          emitSelection("tag");
        },
        clearSelections: function () {
          state.selectedInstances.clear();
          state.selectedTags.clear();
          emitSelection("all");
        },
        selectAllInstances: function () {
          const ids = state.instances.map(function (instance) {
            return instance.id;
          });
          state.selectedInstances = new Set(normalizeIds(ids));
          emitSelection("instance");
        },
        selectAllTags: function () {
          const ids = state.tags.map(function (tag) {
            return tag.id;
          });
          state.selectedTags = new Set(normalizeIds(ids));
          emitSelection("tag");
        },
        performAssign: function () {
          const instanceIds = Array.from(state.selectedInstances);
          const tagIds = Array.from(state.selectedTags);
          if (!instanceIds.length || !tagIds.length) {
            return Promise.reject(new Error("请选择实例与标签"));
          }
          state.loading.operation = true;
          emit("batchAssign:operationLoading", { active: true, mode: "assign", state: cloneState(state) });
          return service
            .batchAssign({
              instance_ids: instanceIds,
              tag_ids: tagIds,
            })
            .then(function (response) {
              if (response && response.success === false) {
                const error = new Error(response.message || "批量分配标签失败");
                error.raw = response;
                throw error;
              }
              emit("batchAssign:operationSuccess", {
                mode: "assign",
                response,
                state: cloneState(state),
              });
              return response;
            })
            .catch(function (error) {
              handleError(error, { action: "assign" });
              throw error;
            })
            .finally(function () {
              state.loading.operation = false;
              emit("batchAssign:operationLoading", { active: false, mode: "assign", state: cloneState(state) });
            });
        },
        performRemove: function () {
          const instanceIds = Array.from(state.selectedInstances);
          if (!instanceIds.length) {
            return Promise.reject(new Error("请选择实例"));
          }
          state.loading.operation = true;
          emit("batchAssign:operationLoading", { active: true, mode: "remove", state: cloneState(state) });
          return service
            .batchRemoveAll({
              instance_ids: instanceIds,
            })
            .then(function (response) {
              if (response && response.success === false) {
                const error = new Error(response.message || "批量移除失败");
                error.raw = response;
                throw error;
              }
              emit("batchAssign:operationSuccess", {
                mode: "remove",
                response,
                state: cloneState(state),
              });
              return response;
            })
            .catch(function (error) {
              handleError(error, { action: "remove" });
              throw error;
            })
            .finally(function () {
              state.loading.operation = false;
              emit("batchAssign:operationLoading", { active: false, mode: "remove", state: cloneState(state) });
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.selectedInstances.clear();
        state.selectedTags.clear();
      },
    };

    return api;
  }

  window.createTagBatchStore = createTagBatchStore;
})(window);
