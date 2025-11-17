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

  function ensureService(service) {
    if (!service) {
      throw new Error("createTagManagementStore: service is required");
    }
    ["listTags", "listCategories", "batchDelete"].forEach(function (method) {
      if (typeof service[method] !== "function") {
        throw new Error("createTagManagementStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createTagManagementStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function normalizeFilters(filters) {
    const source = filters && typeof filters === "object" ? filters : {};
    return {
      category: (source.category || DEFAULT_FILTERS.category).toLowerCase(),
      search: (source.search || DEFAULT_FILTERS.search).trim().toLowerCase(),
    };
  }

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

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function handleError(error, target) {
      state.lastError = error;
      emit(EVENT_NAMES.error, {
        error,
        target,
        state: cloneState(state),
      });
    }

    function updateStats() {
      const total = state.tags.length;
      const selected = state.selection.size;
      const active = state.tags.filter(function (tag) {
        return tag.is_active !== false;
      }).length;
      const filtered = state.filteredTags.length;
      state.stats = { total, selected, active, filtered };
    }

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
        const description = (tag.description || "").toLowerCase();
        return (
          name.includes(query) ||
          displayName.includes(query) ||
          description.includes(query) ||
          categoryValue.includes(query)
        );
      });
      state.filteredTags = orderTags(filtered);
      updateStats();
    }

    function emitTagsUpdated() {
      emit(EVENT_NAMES.tagsUpdated, {
        tags: state.tags.slice(),
        filteredTags: state.filteredTags.slice(),
        filters: Object.assign({}, state.filters),
        stats: Object.assign({}, state.stats),
        state: cloneState(state),
      });
    }

    function emitSelectionChanged(reason, meta) {
      emit(EVENT_NAMES.selectionChanged, {
        reason: reason || "update",
        meta: meta || {},
        selectedIds: Array.from(state.selection),
        state: cloneState(state),
      });
    }

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

      const compareFn = function (tag) {
        if (key === "id") {
          return String(tag.id);
        }
        return String(tag?.[key] ?? tag?.name ?? "");
      };

      const lookup = new Set(
        normalizedValues.map(function (value) {
          return String(value);
        }),
      );

      state.selection.clear();
      state.tags.forEach(function (tag) {
        if (lookup.has(compareFn(tag))) {
          state.selection.add(tag.id);
        }
      });
      emitSelectionChanged("sync");
    }

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
          state.loading.categories = true;
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
              state.loading.categories = false;
            });
        },
        deleteTags: function (tagIds) {
          const ids = normalizeIds(tagIds);
          if (!ids.length) {
            return Promise.reject(new Error("TagManagementStore: 请选择要删除的标签"));
          }
          state.loading.operation = true;
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
              state.loading.operation = false;
              emit(EVENT_NAMES.loading, {
                target: "operation",
                state: cloneState(state),
              });
            });
        },
        loadTags: function (options) {
          const silent = Boolean(options && options.silent);
          state.loading.tags = true;
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
              state.loading.tags = false;
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

  window.createTagManagementStore = createTagManagementStore;
})(window);
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
