(function (window) {
  "use strict";

  /**
   * @typedef {Object} InstanceCrudService
   * @property {Function} getGridUrl
   * @property {Function} getInstance
   * @property {Function} createInstance
   * @property {Function} updateInstance
   * @property {Function} deleteInstance
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createInstanceCrudStore: service is required");
    }
    const required = [
      "getGridUrl",
      "getInstance",
      "createInstance",
      "updateInstance",
      "deleteInstance",
    ];
    required.forEach((method) => {
      // 固定白名单方法名，避免动态键注入。
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error("createInstanceCrudStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createInstanceCrudStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function ensureSuccessResponse(response, fallbackMessage) {
    if (response && response.success === false) {
      const error = new Error(response.message || fallbackMessage || "操作失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  function cloneState(state) {
    return {
      gridUrl: state.gridUrl,
      lastError: state.lastError,
    };
  }

  /**
   * Instance CRUD Store：承载实例的读取/创建/更新/删除 actions。
   *
   * @param {Object} options
   * @param {InstanceCrudService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createInstanceCrudStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      gridUrl: service.getGridUrl(),
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("instancesCrud:error", {
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
        load: function (instanceId) {
          if (instanceId === undefined || instanceId === null || instanceId === "") {
            return Promise.reject(new Error("InstanceCrudStore: load 需要 instanceId"));
          }
          return service
            .getInstance(instanceId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "加载实例失败");
              const instance = resolved?.data?.instance || null;
              if (!instance) {
                throw new Error(resolved?.message || "加载实例失败");
              }
              state.lastError = null;
              emit("instancesCrud:loaded", { instance, state: cloneState(state) });
              return instance;
            })
            .catch((error) => {
              handleError(error, { action: "load", instanceId });
              throw error;
            });
        },
        create: function (payload) {
          if (!payload) {
            return Promise.reject(new Error("InstanceCrudStore: create 需要 payload"));
          }
          return service
            .createInstance(payload)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "添加实例失败");
              state.lastError = null;
              emit("instancesCrud:created", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "create" });
              throw error;
            });
        },
        update: function (instanceId, payload) {
          if (instanceId === undefined || instanceId === null || instanceId === "") {
            return Promise.reject(new Error("InstanceCrudStore: update 需要 instanceId"));
          }
          if (!payload) {
            return Promise.reject(new Error("InstanceCrudStore: update 需要 payload"));
          }
          return service
            .updateInstance(instanceId, payload)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "保存实例失败");
              state.lastError = null;
              emit("instancesCrud:updated", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "update", instanceId });
              throw error;
            });
        },
        deleteInstance: function (instanceId) {
          if (instanceId === undefined || instanceId === null || instanceId === "") {
            return Promise.reject(new Error("InstanceCrudStore: deleteInstance 需要 instanceId"));
          }
          emit("instancesCrud:deleting", { instanceId, state: cloneState(state) });
          return service
            .deleteInstance(instanceId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "移入回收站失败");
              state.lastError = null;
              emit("instancesCrud:deleted", { response: resolved, instanceId, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "deleteInstance", instanceId });
              throw error;
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.lastError = null;
      },
    };

    return api;
  }

  window.createInstanceCrudStore = createInstanceCrudStore;
})(window);

