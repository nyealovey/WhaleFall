(function (window) {
  "use strict";

  /**
   * @typedef {Object} UsersService
   * @property {Function} getGridUrl
   * @property {Function} getUser
   * @property {Function} createUser
   * @property {Function} updateUser
   * @property {Function} deleteUser
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createUsersStore: service is required");
    }
    const required = ["getGridUrl", "getUser", "createUser", "updateUser", "deleteUser"];
    required.forEach((method) => {
      if (typeof service[method] !== "function") {
        throw new Error(`createUsersStore: service.${method} 未实现`);
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createUsersStore: 需要 mitt 实例");
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
      loading: { ...state.loading },
      lastError: state.lastError,
    };
  }

  /**
   * Users Store：承载用户管理的 actions（读取/创建/更新/删除）。
   *
   * @param {Object} options
   * @param {UsersService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createUsersStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      gridUrl: service.getGridUrl(),
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
      emit("users:loading", {
        loading: { ...state.loading },
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("users:error", {
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
        load: function (userId) {
          if (userId === undefined || userId === null || userId === "") {
            return Promise.reject(new Error("UsersStore: load 需要 userId"));
          }
          setLoading("load", true, { action: "load" });
          return service
            .getUser(userId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "获取用户信息失败");
              const payload = resolved?.data || resolved || {};
              const user = payload?.user || payload?.data?.user || null;
              if (!user) {
                throw new Error(resolved?.message || "获取用户信息失败");
              }
              state.lastError = null;
              emit("users:loaded", { user, state: cloneState(state) });
              return user;
            })
            .catch((error) => {
              handleError(error, { action: "load" });
              throw error;
            })
            .finally(() => setLoading("load", false, { action: "load" }));
        },
        create: function (payload) {
          if (!payload) {
            return Promise.reject(new Error("UsersStore: create 需要 payload"));
          }
          setLoading("create", true, { action: "create" });
          return service
            .createUser(payload)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "创建用户失败");
              state.lastError = null;
              emit("users:created", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "create" });
              throw error;
            })
            .finally(() => setLoading("create", false, { action: "create" }));
        },
        update: function (userId, payload) {
          if (userId === undefined || userId === null || userId === "") {
            return Promise.reject(new Error("UsersStore: update 需要 userId"));
          }
          if (!payload) {
            return Promise.reject(new Error("UsersStore: update 需要 payload"));
          }
          setLoading("update", true, { action: "update" });
          return service
            .updateUser(userId, payload)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "更新用户失败");
              state.lastError = null;
              emit("users:updated", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "update" });
              throw error;
            })
            .finally(() => setLoading("update", false, { action: "update" }));
        },
        remove: function (userId) {
          if (userId === undefined || userId === null || userId === "") {
            return Promise.reject(new Error("UsersStore: remove 需要 userId"));
          }
          setLoading("remove", true, { action: "remove" });
          return service
            .deleteUser(userId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "删除用户失败");
              state.lastError = null;
              emit("users:removed", { response: resolved, state: cloneState(state) });
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
        state.lastError = null;
        state.loading.load = false;
        state.loading.create = false;
        state.loading.update = false;
        state.loading.remove = false;
      },
    };

    return api;
  }

  window.createUsersStore = createUsersStore;
})(window);

