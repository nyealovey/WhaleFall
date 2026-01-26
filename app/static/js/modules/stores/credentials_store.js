(function (window) {
  "use strict";

  /**
   * @typedef {Object} CredentialsService
   * @property {Function} getGridUrl
   * @property {Function} getCredential
   * @property {Function} createCredential
   * @property {Function} updateCredential
   * @property {Function} deleteCredential
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createCredentialsStore: service is required");
    }
    const required = [
      "getGridUrl",
      "getCredential",
      "createCredential",
      "updateCredential",
      "deleteCredential",
    ];
    required.forEach((method) => {
      // 固定白名单方法名，避免动态键注入。
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error("createCredentialsStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createCredentialsStore: 需要 mitt 实例");
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
   * Credentials Store：承载凭据的 CRUD actions 与错误事件。
   *
   * @param {Object} options
   * @param {CredentialsService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createCredentialsStore(options) {
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
      emit("credentials:error", {
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
        load: function (credentialId) {
          if (credentialId === undefined || credentialId === null || credentialId === "") {
            return Promise.reject(new Error("CredentialsStore: load 需要 credentialId"));
          }
          return service
            .getCredential(credentialId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "加载凭据失败");
              const credential = resolved?.data?.credential || null;
              if (!credential) {
                throw new Error(resolved?.message || "加载凭据失败");
              }
              state.lastError = null;
              emit("credentials:loaded", { credential, state: cloneState(state) });
              return credential;
            })
            .catch((error) => {
              handleError(error, { action: "load", credentialId });
              throw error;
            });
        },
        create: function (payload) {
          if (!payload) {
            return Promise.reject(new Error("CredentialsStore: create 需要 payload"));
          }
          return service
            .createCredential(payload)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "添加凭据失败");
              state.lastError = null;
              emit("credentials:created", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "create" });
              throw error;
            });
        },
        update: function (credentialId, payload) {
          if (credentialId === undefined || credentialId === null || credentialId === "") {
            return Promise.reject(new Error("CredentialsStore: update 需要 credentialId"));
          }
          if (!payload) {
            return Promise.reject(new Error("CredentialsStore: update 需要 payload"));
          }
          return service
            .updateCredential(credentialId, payload)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "保存凭据失败");
              state.lastError = null;
              emit("credentials:updated", { response: resolved, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "update", credentialId });
              throw error;
            });
        },
        deleteCredential: function (credentialId) {
          if (credentialId === undefined || credentialId === null || credentialId === "") {
            return Promise.reject(new Error("CredentialsStore: deleteCredential 需要 credentialId"));
          }
          emit("credentials:deleting", { credentialId, state: cloneState(state) });
          return service
            .deleteCredential(credentialId)
            .then((resp) => {
              const resolved = ensureSuccessResponse(resp, "删除凭据失败");
              state.lastError = null;
              emit("credentials:deleted", { response: resolved, credentialId, state: cloneState(state) });
              return resolved;
            })
            .catch((error) => {
              handleError(error, { action: "deleteCredential", credentialId });
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

  window.createCredentialsStore = createCredentialsStore;
})(window);
