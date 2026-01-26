(function (window) {
  "use strict";

  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const isSafeKey = (key) => typeof key === "string" && key && !UNSAFE_KEYS.includes(key);

  const EVENT_NAMES = {
    loading: "tagBatchAssign:loading",
    updated: "tagBatchAssign:updated",
    selectionChanged: "tagBatchAssign:selectionChanged",
    modeChanged: "tagBatchAssign:modeChanged",
    operationSuccess: "tagBatchAssign:operationSuccess",
    error: "tagBatchAssign:error",
  };

  function ensureService(service) {
    if (!service) {
      throw new Error("createTagBatchStore: service is required");
    }
    ["listInstances", "listAllTags", "batchAssign", "batchRemoveAll"].forEach(function (method) {
      // 固定白名单方法名，避免动态键注入。
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error("createTagBatchStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createTagBatchStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function ensureLodash(lodash) {
    const resolved = lodash || window.LodashUtils || null;
    if (!resolved) {
      throw new Error("createTagBatchStore: 需要 LodashUtils");
    }
    return resolved;
  }

  function ensureSuccess(response, fallbackMessage) {
    if (response && response.success === false) {
      const error = new Error(response.message || response.error || fallbackMessage || "操作失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  function toNumericId(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string" && value.trim()) {
      const parsed = Number.parseInt(value, 10);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  function cloneArrayOfObjects(list) {
    if (!Array.isArray(list)) {
      return [];
    }
    return list.map(function (item) {
      return item && typeof item === "object" ? Object.assign({}, item) : item;
    });
  }

  function cloneGroupedObject(grouped) {
    const source = grouped && typeof grouped === "object" ? grouped : {};
    const cloned = {};
    Object.keys(source).forEach(function (key) {
      if (!isSafeKey(key)) {
        return;
      }
      // eslint-disable-next-line security/detect-object-injection
      const list = source[key];
      // eslint-disable-next-line security/detect-object-injection
      cloned[key] = Array.isArray(list) ? cloneArrayOfObjects(list) : [];
    });
    return cloned;
  }

  function cloneState(state) {
    return {
      mode: state.mode,
      instancesByDbType: cloneGroupedObject(state.instancesByDbType),
      tagsByCategory: cloneGroupedObject(state.tagsByCategory),
      selectedInstanceIds: Array.from(state.selectedInstanceIds),
      selectedTagIds: Array.from(state.selectedTagIds),
      loading: Object.assign({}, state.loading),
      lastError: state.lastError,
      lastResult: state.lastResult,
    };
  }

  function extractInstances(response) {
    const payload = response?.data ?? response;
    const instances = payload?.instances ?? payload?.items ?? [];
    return Array.isArray(instances) ? instances : [];
  }

  function extractTags(response) {
    const payload = response?.data ?? response;
    const tags = payload?.tags ?? payload?.items ?? [];
    return Array.isArray(tags) ? tags : [];
  }

  function groupInstancesByDbType(lodash, instances) {
    const groups = lodash.groupBy(instances || [], function (item) {
      return item?.db_type || "unknown";
    });
    return lodash.mapValues(groups, function (items) {
      return lodash.orderBy(
        items,
        [
          function (instance) {
            const name = instance?.name;
            return typeof name === "string" ? name.trim().toLowerCase() : "";
          },
        ],
        ["asc"],
      );
    });
  }

  function groupTagsByCategory(lodash, tags) {
    const groups = lodash.groupBy(tags || [], function (item) {
      return item?.category || "未分类";
    });
    return lodash.mapValues(groups, function (items) {
      return lodash.orderBy(
        items,
        [
          function (tag) {
            const label = tag?.display_name || tag?.name;
            return typeof label === "string" ? label.trim().toLowerCase() : "";
          },
        ],
        ["asc"],
      );
    });
  }

  function buildIdSetFromList(list) {
    const ids = new Set();
    (list || []).forEach(function (item) {
      const id = toNumericId(item?.id);
      if (id !== null) {
        ids.add(id);
      }
    });
    return ids;
  }

  function createTagBatchStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);
    const LodashUtils = ensureLodash(opts.LodashUtils);

    const state = {
      mode: "assign",
      instancesByDbType: {},
      tagsByCategory: {},
      selectedInstanceIds: new Set(),
      selectedTagIds: new Set(),
      loading: {
        data: false,
        operation: false,
      },
      lastError: null,
      lastResult: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function emitLoading(target) {
      emit(EVENT_NAMES.loading, {
        target: target || "unknown",
        loading: Object.assign({}, state.loading),
        state: cloneState(state),
      });
    }

    function emitSelectionChanged(reason) {
      emit(EVENT_NAMES.selectionChanged, {
        reason: reason || "update",
        selectedInstanceIds: Array.from(state.selectedInstanceIds),
        selectedTagIds: Array.from(state.selectedTagIds),
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

    function pruneSelections(availableInstanceIds, availableTagIds) {
      let changed = false;
      state.selectedInstanceIds.forEach(function (id) {
        if (!availableInstanceIds.has(id)) {
          state.selectedInstanceIds.delete(id);
          changed = true;
        }
      });
      state.selectedTagIds.forEach(function (id) {
        if (!availableTagIds.has(id)) {
          state.selectedTagIds.delete(id);
          changed = true;
        }
      });
      if (changed) {
        emitSelectionChanged("prune");
      }
    }

    const actions = {
      setMode: function (mode) {
        if (mode !== "assign" && mode !== "remove") {
          return Promise.reject(new Error("TagBatchStore: mode 必须为 assign/remove"));
        }
        if (state.mode === mode) {
          return Promise.resolve(cloneState(state));
        }
        state.mode = mode;
        if (mode === "remove") {
          state.selectedTagIds.clear();
          emitSelectionChanged("modeChanged");
        }
        emit(EVENT_NAMES.modeChanged, { mode: state.mode, state: cloneState(state) });
        return Promise.resolve(cloneState(state));
      },

      loadData: function () {
        state.loading.data = true;
        emitLoading("data");

        return Promise.all([service.listInstances(), service.listAllTags()])
          .then(function ([instancesResp, tagsResp]) {
            const instancesResult = ensureSuccess(instancesResp, "加载实例失败");
            const tagsResult = ensureSuccess(tagsResp, "加载标签失败");

            const instances = extractInstances(instancesResult);
            const tags = extractTags(tagsResult);

            state.instancesByDbType = groupInstancesByDbType(LodashUtils, instances);
            state.tagsByCategory = groupTagsByCategory(LodashUtils, tags);
            state.lastError = null;

            // 刷新数据后对选择集做一次收敛，避免保留失效 ID。
            pruneSelections(buildIdSetFromList(instances), buildIdSetFromList(tags));

            emit(EVENT_NAMES.updated, { state: cloneState(state) });
            return cloneState(state);
          })
          .catch(function (error) {
            handleError(error, { action: "loadData" });
            throw error;
          })
          .finally(function () {
            state.loading.data = false;
            emitLoading("data");
          });
      },

      clearSelections: function () {
        if (state.selectedInstanceIds.size === 0 && state.selectedTagIds.size === 0) {
          return;
        }
        state.selectedInstanceIds.clear();
        state.selectedTagIds.clear();
        emitSelectionChanged("clear");
      },

      setInstanceSelected: function (instanceId, selected) {
        const id = toNumericId(instanceId);
        if (id === null) {
          return;
        }
        const shouldSelect = Boolean(selected);
        const has = state.selectedInstanceIds.has(id);
        if (shouldSelect && !has) {
          state.selectedInstanceIds.add(id);
          emitSelectionChanged("instance");
        } else if (!shouldSelect && has) {
          state.selectedInstanceIds.delete(id);
          emitSelectionChanged("instance");
        }
      },

      setTagSelected: function (tagId, selected) {
        const id = toNumericId(tagId);
        if (id === null) {
          return;
        }
        const shouldSelect = Boolean(selected);
        const has = state.selectedTagIds.has(id);
        if (shouldSelect && !has) {
          state.selectedTagIds.add(id);
          emitSelectionChanged("tag");
        } else if (!shouldSelect && has) {
          state.selectedTagIds.delete(id);
          emitSelectionChanged("tag");
        }
      },

      setInstancesByDbTypeSelected: function (dbType, selected) {
        if (!isSafeKey(dbType)) {
          return;
        }
        // eslint-disable-next-line security/detect-object-injection
        const group = state.instancesByDbType[dbType];
        if (!Array.isArray(group)) {
          return;
        }

        const shouldSelect = Boolean(selected);
        let changed = false;
        group.forEach(function (item) {
          const id = toNumericId(item?.id);
          if (id === null) {
            return;
          }
          const has = state.selectedInstanceIds.has(id);
          if (shouldSelect && !has) {
            state.selectedInstanceIds.add(id);
            changed = true;
          } else if (!shouldSelect && has) {
            state.selectedInstanceIds.delete(id);
            changed = true;
          }
        });
        if (changed) {
          emitSelectionChanged("instanceGroup");
        }
      },

      setTagsByCategorySelected: function (category, selected) {
        if (!isSafeKey(category)) {
          return;
        }
        // eslint-disable-next-line security/detect-object-injection
        const group = state.tagsByCategory[category];
        if (!Array.isArray(group)) {
          return;
        }

        const shouldSelect = Boolean(selected);
        let changed = false;
        group.forEach(function (item) {
          const id = toNumericId(item?.id);
          if (id === null) {
            return;
          }
          const has = state.selectedTagIds.has(id);
          if (shouldSelect && !has) {
            state.selectedTagIds.add(id);
            changed = true;
          } else if (!shouldSelect && has) {
            state.selectedTagIds.delete(id);
            changed = true;
          }
        });
        if (changed) {
          emitSelectionChanged("tagGroup");
        }
      },

      executeOperation: function () {
        const instanceIds = Array.from(state.selectedInstanceIds);
        if (!instanceIds.length) {
          return Promise.reject(new Error("请选择实例"));
        }
        if (state.mode === "assign") {
          const tagIds = Array.from(state.selectedTagIds);
          if (!tagIds.length) {
            return Promise.reject(new Error("请选择标签"));
          }

          state.loading.operation = true;
          emitLoading("operation");
          return service
            .batchAssign({ instance_ids: instanceIds, tag_ids: tagIds })
            .then(function (response) {
              const result = ensureSuccess(response, "批量分配失败");
              state.lastError = null;
              state.lastResult = result;
              emit(EVENT_NAMES.operationSuccess, { mode: "assign", response: result, state: cloneState(state) });
              return result;
            })
            .catch(function (error) {
              handleError(error, { action: "executeOperation", mode: "assign" });
              throw error;
            })
            .finally(function () {
              state.loading.operation = false;
              emitLoading("operation");
            });
        }

        state.loading.operation = true;
        emitLoading("operation");
        return service
          .batchRemoveAll({ instance_ids: instanceIds })
          .then(function (response) {
            const result = ensureSuccess(response, "批量移除失败");
            state.lastError = null;
            state.lastResult = result;
            emit(EVENT_NAMES.operationSuccess, { mode: "remove", response: result, state: cloneState(state) });
            return result;
          })
          .catch(function (error) {
            handleError(error, { action: "executeOperation", mode: "remove" });
            throw error;
          })
          .finally(function () {
            state.loading.operation = false;
            emitLoading("operation");
          });
      },
    };

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
      actions: actions,
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.mode = "assign";
        state.selectedInstanceIds.clear();
        state.selectedTagIds.clear();
        state.instancesByDbType = {};
        state.tagsByCategory = {};
        state.loading.data = false;
        state.loading.operation = false;
        state.lastError = null;
        state.lastResult = null;
      },
    };

    return api;
  }

  window.createTagBatchStore = createTagBatchStore;
})(window);
