(function (window) {
  "use strict";

  /**
   * @typedef {Object} TagListService
   * @property {Function} getGridUrl
   * @property {Function} getTag
   * @property {Function} createTag
   * @property {Function} updateTag
   * @property {Function} deleteTag
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createTagListStore: service is required");
    }
    const required = ["getGridUrl", "getTag", "createTag", "updateTag", "deleteTag"];
    required.forEach((method) => {
      if (typeof service[method] !== "function") {
        throw new Error(`createTagListStore: service.${method} 未实现`);
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createTagListStore: 需要 mitt 实例");
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
      stats: state.stats ? { ...state.stats } : null,
      loading: { ...state.loading },
      lastError: state.lastError,
    };
  }

  /**
   * TagList Store：承载标签管理页的状态与 actions（统计、读取、创建、更新、删除）。
   *
   * @param {Object} options
   * @param {TagListService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createTagListStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      gridUrl: service.getGridUrl(),
      stats: null,
      loading: {
        load: false,
        create: false,
        update: false,
        remove: false,
      },
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function setLoading(key, loading, meta) {
      state.loading[key] = Boolean(loading);
      emit("tags:loading", {
        loading: { ...state.loading },
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("tags:error", {
        error,
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
          state.stats = raw.stats && typeof raw.stats === "object" ? { ...raw.stats } : null;
          emit("tags:statsUpdated", { stats: state.stats, state: cloneState(state) });
          return Array.isArray(raw.items) ? raw.items : [];
        },
        load: function (tagId) {
          if (tagId === undefined || tagId === null || tagId === "") {
            return Promise.reject(new Error("TagListStore: load 需要 tagId"));
          }
          setLoading("load", true, { action: "load" });
          return service
            .getTag(tagId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "加载标签失败");
              const payload = resolved?.data || resolved || {};
              const tag = payload?.tag || payload?.data?.tag || null;
              if (!tag) {
                throw new Error(resolved?.message || "加载标签失败");
              }
              state.lastError = null;
              emit("tags:loaded", { tag, state: cloneState(state) });
              return tag;
            })
            .catch((error) => {
              handleError(error, { action: "load" });
              throw error;
            })
            .finally(() => setLoading("load", false, { action: "load" }));
        },
        create: function (payload) {
          if (!payload) {
            return Promise.reject(new Error("TagListStore: create 需要 payload"));
          }
          setLoading("create", true, { action: "create" });
          return service
            .createTag(payload)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "创建标签失败");
              state.lastError = null;
              emit("tags:created", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "create" });
              throw error;
            })
            .finally(() => setLoading("create", false, { action: "create" }));
        },
        update: function (tagId, payload) {
          if (tagId === undefined || tagId === null || tagId === "") {
            return Promise.reject(new Error("TagListStore: update 需要 tagId"));
          }
          if (!payload) {
            return Promise.reject(new Error("TagListStore: update 需要 payload"));
          }
          setLoading("update", true, { action: "update" });
          return service
            .updateTag(tagId, payload)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "更新标签失败");
              state.lastError = null;
              emit("tags:updated", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "update" });
              throw error;
            })
            .finally(() => setLoading("update", false, { action: "update" }));
        },
        remove: function (tagId) {
          if (tagId === undefined || tagId === null || tagId === "") {
            return Promise.reject(new Error("TagListStore: remove 需要 tagId"));
          }
          setLoading("remove", true, { action: "remove" });
          return service
            .deleteTag(tagId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "删除标签失败");
              state.lastError = null;
              emit("tags:removed", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "remove" });
              throw error;
            })
            .finally(() => setLoading("remove", false, { action: "remove" }));
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.stats = null;
        state.lastError = null;
        state.loading.load = false;
        state.loading.create = false;
        state.loading.update = false;
        state.loading.remove = false;
      },
    };

    return api;
  }

  window.createTagListStore = createTagListStore;
})(window);

