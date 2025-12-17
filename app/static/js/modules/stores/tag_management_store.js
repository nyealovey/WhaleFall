(function (window) {
  "use strict";

  const DEFAULT_FILTERS = { category: "all", search: "" };
  const EVENT_NAMES = {
    loading: "tagManagement:loading",
    categoriesUpdated: "tagManagement:categoriesUpdated",
    tagsUpdated: "tagManagement:tagsUpdated",
    selectionChanged: "tagManagement:selectionChanged",
    operationSuccess: "tagManagement:operationSuccess",
    error: "tagManagement:error",
  };

  /**
   * 校验 service 是否具备 store 运行所需的 API。
   *
   * @param {Object} service - 服务对象
   * @param {Function} service.listTags - 获取标签列表的方法
   * @param {Function} service.listCategories - 获取分类列表的方法
   * @param {Function} service.batchDelete - 批量删除标签的方法
   * @return {Object} 校验后的服务对象
   * @throws {Error} 当 service 为空或缺少必需方法时抛出
   */
  function ensureService(service) {
    if (!service) {
      throw new Error("createTagManagementStore: service is required");
    }
    const REQUIRED_METHODS = ["listTags", "listCategories", "batchDelete"];
    REQUIRED_METHODS.forEach(function (method) {
      // 固定白名单方法名，避免动态键注入。
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error("createTagManagementStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  /**
   * 补全一个 mitt 事件总线，若未传入则退回全局 mitt。
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
      throw new Error("createTagManagementStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const LOADING_KEYS = new Set(["categories", "tags", "operation"]);
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

  /**
   * 统一处理分类/搜索过滤器，避免大小写或空白差异。
   *
   * @param {Object} filters - 过滤条件对象
   * @return {Object} 规范化后的过滤条件
   */
  function normalizeFilters(filters) {
    const source = filters && typeof filters === "object" ? filters : {};
    return {
      category: (source.category || DEFAULT_FILTERS.category).toLowerCase(),
      search: (source.search || DEFAULT_FILTERS.search).trim().toLowerCase(),
    };
  }

  /**
   * 按激活状态与名称对标签排序，确保 UI 展示一致。
   *
   * @param {Array} items - 标签数组
   * @return {Array} 排序后的标签数组
   */
  function orderTags(items) {
    if (!Array.isArray(items)) {
      return [];
    }
    const utils = window.LodashUtils;
    if (utils && typeof utils.orderBy === "function") {
      return utils.orderBy(
        items,
        [
          function (tag) {
            return tag.is_active === false ? 1 : 0;
          },
          function (tag) {
            return (tag.display_name || tag.name || "").toLowerCase();
          },
        ],
        ["asc", "asc"],
      );
    }
    return items.slice().sort(function (a, b) {
      const inactiveDiff = (a.is_active === false ? 1 : 0) - (b.is_active === false ? 1 : 0);
      if (inactiveDiff !== 0) {
        return inactiveDiff;
      }
      const nameA = (a.display_name || a.name || "").toLowerCase();
      const nameB = (b.display_name || b.name || "").toLowerCase();
      return nameA.localeCompare(nameB);
    });
  }

  /**
   * 深拷贝 store 状态的核心字段，用于事件派发。
   *
   * @param {Object} state - 状态对象
   * @return {Object} 状态对象的拷贝
   */
  function cloneState(state) {
    return {
      categories: state.categories.slice(),
      tags: state.tags.slice(),
      filteredTags: state.filteredTags.slice(),
      filters: Object.assign({}, state.filters),
      selection: Array.from(state.selection),
      stats: Object.assign({}, state.stats),
      loading: Object.assign({}, state.loading),
      lastError: state.lastError,
    };
  }

  /**
   * 创建标签管理状态管理 Store。
   *
   * 提供标签和分类的查询、过滤、选择、删除等功能的状态管理。
   *
   * @param {Object} options - 配置选项
   * @param {Object} options.service - 标签管理服务对象
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @param {Object} [options.initialFilters] - 初始过滤条件
   * @return {Object} Store API 对象
   *
   * @example
   * const store = createTagManagementStore({
   *   service: tagManagementService,
   *   initialFilters: { category: 'all', search: '' }
   * });
   * store.init().then(() => {
   *   console.log(store.getState());
   * });
   */
  function createTagManagementStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);
    let pendingSelection = null;

    const state = {
      categories: [],
      tags: [],
      filteredTags: [],
      filters: normalizeFilters(opts.initialFilters || DEFAULT_FILTERS),
      selection: new Set(),
      stats: {
        total: 0,
        selected: 0,
        active: 0,
        filtered: 0,
      },
      loading: {
        categories: false,
        tags: false,
        operation: false,
      },
      lastError: null,
    };

    /**
     * 向 mitt 广播事件，默认附带当前状态快照。
     *
     * @param {string} eventName 事件名。
     * @param {Object} [payload] 自定义数据，默认为 cloneState(state)。
     * @returns {void}
     */
    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    /**
     * 统一错误处理，记录目标并广播 error 事件。
     *
     * @param {Error|Object|string} error 捕获的异常。
     * @param {string} target 出错阶段标识。
     * @returns {void}
     */
    function handleError(error, target) {
      state.lastError = error;
      emit(EVENT_NAMES.error, {
        error,
        target,
        state: cloneState(state),
      });
    }

    /**
     * 根据当前标签/选择更新统计数据。
     *
     * @param {void} 无参数。该函数直接读取内部 state。
     * @returns {void}
     */
    function updateStats() {
      const total = state.tags.length;
      const selected = state.selection.size;
      const active = state.tags.filter(function (tag) {
        return tag.is_active !== false;
      }).length;
      const filtered = state.filteredTags.length;
      state.stats = { total, selected, active, filtered };
    }

    /**
     * 应用分类与搜索过滤，生成 filteredTags。
     *
     * @param {void} 无参数。过滤条件来自内部 state.filters。
     * @returns {void}
     */
    function updateFilteredTags() {
      const filters = state.filters;
      const filtered = state.tags.filter(function (tag) {
        const categoryValue = (tag.category || "").toLowerCase();
        const matchesCategory =
          filters.category === "all" || categoryValue === filters.category;
        if (!matchesCategory) {
          return false;
        }
        if (!filters.search) {
          return true;
        }
        const query = filters.search;
        const name = (tag.name || "").toLowerCase();
        const displayName = (tag.display_name || "").toLowerCase();
        return (
          name.includes(query) ||
          displayName.includes(query) ||
          categoryValue.includes(query)
        );
      });
      state.filteredTags = orderTags(filtered);
      updateStats();
    }

    /**
     * 广播标签变化事件，供订阅方刷新 UI。
     *
     * @param {void} 无参数。事件数据由当前 state 自动生成。
     * @returns {void}
     */
    function emitTagsUpdated() {
      emit(EVENT_NAMES.tagsUpdated, {
        tags: state.tags.slice(),
        filteredTags: state.filteredTags.slice(),
        filters: Object.assign({}, state.filters),
        stats: Object.assign({}, state.stats),
        state: cloneState(state),
      });
    }

    /**
     * 广播选择变化，附带原因与额外上下文。
     *
     * @param {string} [reason="update"] 触发原因。
     * @param {Object} [meta] 额外上下文。
     * @returns {void}
     */
    function emitSelectionChanged(reason, meta) {
      emit(EVENT_NAMES.selectionChanged, {
        reason: reason || "update",
        meta: meta || {},
        selectedIds: Array.from(state.selection),
        state: cloneState(state),
      });
    }

    /**
     * 根据 id 或 name 同步已有选择；数据未加载时暂存。
     *
     * @param {Array<string>|string} values 待同步的值列表或逗号字符串。
     * @param {"id"|string} [key="id"] 用于匹配的字段，默认为 id。
     * @returns {void}
     */
    function applySelection(values, key) {
      const normalizedValues = Array.isArray(values)
        ? values
        : typeof values === "string"
        ? values
            .split(",")
            .map(function (item) {
              return item.trim();
            })
            .filter(Boolean)
        : [];

      if (!state.tags.length) {
        pendingSelection = { values: normalizedValues, key };
        return;
      }

      /**
       * 根据 key 生成比较用字符串。
       *
       * @param {Object} tag 标签对象。
       * @returns {string} 用于匹配 selection 的值。
       */
      const compareFn = function (tag) {
        if (key === "id") {
          return String(tag.id);
        }
        // 仅允许受控字段，避免任意键访问。
        if (key === "name") {
          return String(tag?.name ?? "");
        }
        if (key === "display_name") {
          return String(tag?.display_name ?? "");
        }
        return String(tag?.name ?? "");
      };

      const lookup = new Set(
        normalizedValues.map(function (value) {
          return String(value);
        }),
      );

      state.selection.clear();
      state.tags.forEach(function (tag) {
        const token = compareFn(tag);
        if (!token) {
          return;
        }
        // compareFn 仅返回受控 key 的字符串，不含用户可控路径
        if (lookup.has(token)) {
          state.selection.add(tag.id);
        }
      });
      emitSelectionChanged("sync");
    }

    /**
     * 当标签列表加载完成后应用暂存的选择。
     *
     * @param {void} 无参数。函数读取 pendingSelection 内部缓冲。
     * @returns {void}
     */
    function applyPendingSelection() {
      if (!pendingSelection) {
        return;
      }
      const payload = pendingSelection;
      pendingSelection = null;
      applySelection(payload.values, payload.key);
    }

    const api = {
      init: function (initialFilters) {
        if (initialFilters && typeof initialFilters === "object") {
          state.filters = normalizeFilters(initialFilters);
        }
        return Promise.all([
          api.actions.loadCategories({ silent: true }),
          api.actions.loadTags({ silent: true }),
        ]);
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
        loadCategories: function (options) {
          const silent = Boolean(options && options.silent);
          setMapValue(state.loading, "categories", true, LOADING_KEYS);
          if (!silent) {
            emit(EVENT_NAMES.loading, {
              target: "categories",
              state: cloneState(state),
            });
          }
          return service
            .listCategories()
            .then(function (response) {
              const payload =
                response?.categories ??
                response?.data?.categories ??
                response?.data ??
                [];
              state.categories = Array.isArray(payload) ? payload.slice() : [];
              emit(EVENT_NAMES.categoriesUpdated, {
                categories: state.categories.slice(),
                state: cloneState(state),
              });
              return state.categories.slice();
            })
            .catch(function (error) {
              handleError(error, "categories");
              throw error;
            })
            .finally(function () {
              setMapValue(state.loading, "categories", false, LOADING_KEYS);
            });
        },
        deleteTags: function (tagIds) {
          const ids = normalizeIds(tagIds);
          if (!ids.length) {
            return Promise.reject(new Error("TagManagementStore: 请选择要删除的标签"));
          }
          setMapValue(state.loading, "operation", true, LOADING_KEYS);
          emit(EVENT_NAMES.loading, {
            target: "operation",
            state: cloneState(state),
          });
          return service
            .batchDelete({
              tag_ids: ids,
            })
            .then(function (response) {
              if (response && response.success === false) {
                const error = new Error(response.message || "删除标签失败");
                error.raw = response;
                throw error;
              }
              emit(EVENT_NAMES.operationSuccess, {
                action: "deleteTags",
                tagIds: ids.slice(),
                response,
                state: cloneState(state),
              });
              return api.actions.loadTags({ silent: true }).then(function () {
                return response;
              });
            })
            .catch(function (error) {
              handleError(error, "operation");
              throw error;
            })
            .finally(function () {
              setMapValue(state.loading, "operation", false, LOADING_KEYS);
              emit(EVENT_NAMES.loading, {
                target: "operation",
                state: cloneState(state),
              });
            });
        },
        loadTags: function (options) {
          const silent = Boolean(options && options.silent);
          setMapValue(state.loading, "tags", true, LOADING_KEYS);
          if (!silent) {
            emit(EVENT_NAMES.loading, {
              target: "tags",
              state: cloneState(state),
            });
          }
          return service
            .listTags()
            .then(function (response) {
              const payload =
                response?.data?.tags ??
                response?.tags ??
                response?.data ??
                [];
              state.tags = Array.isArray(payload) ? payload.slice() : [];
              state.tags = orderTags(state.tags);
              updateFilteredTags();
              emitTagsUpdated();
              applyPendingSelection();
              emitSelectionChanged("sync");
              return state.tags.slice();
            })
            .catch(function (error) {
              handleError(error, "tags");
              throw error;
            })
            .finally(function () {
              setMapValue(state.loading, "tags", false, LOADING_KEYS);
            });
        },
        setCategory: function (value) {
          const nextValue = (value || "all").toLowerCase();
          if (state.filters.category === nextValue) {
            return;
          }
          state.filters.category = nextValue;
          updateFilteredTags();
          emitTagsUpdated();
        },
        setSearch: function (query) {
          const nextSearch = (query || "").trim().toLowerCase();
          if (state.filters.search === nextSearch) {
            return;
          }
          state.filters.search = nextSearch;
          updateFilteredTags();
          emitTagsUpdated();
        },
        addTag: function (tagId) {
          const numericId = Number(tagId);
          if (!Number.isFinite(numericId)) {
            return;
          }
          const tag = state.tags.find(function (item) {
            return item.id === numericId;
          });
          if (!tag) {
            return;
          }
          if (state.selection.has(numericId)) {
            return;
          }
          state.selection.add(numericId);
          emitSelectionChanged("add", { tag: tag });
        },
        removeTag: function (tagId) {
          const numericId = Number(tagId);
          if (!state.selection.has(numericId)) {
            return;
          }
          const tag = state.tags.find(function (item) {
            return item.id === numericId;
          });
          state.selection.delete(numericId);
          emitSelectionChanged("remove", { tag: tag || null });
        },
        clearSelection: function () {
          if (!state.selection.size) {
            return;
          }
          state.selection.clear();
          emitSelectionChanged("clear");
        },
        replaceSelection: function (ids) {
          const incoming = Array.isArray(ids) ? ids : [];
          state.selection.clear();
          incoming.forEach(function (value) {
            const numericId = Number(value);
            if (!Number.isFinite(numericId)) {
              return;
            }
            if (
              state.tags.some(function (tag) {
                return tag.id === numericId;
              })
            ) {
              state.selection.add(numericId);
            }
          });
          emitSelectionChanged("replace");
        },
        selectBy: function (values, key) {
          applySelection(values, key);
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.selection.clear();
        pendingSelection = null;
      },
    };

    return api;
  }

  /**
   * 规范化 ID 数组，过滤无效值。
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

  window.createTagManagementStore = createTagManagementStore;
})(window);
