(function (window) {
  "use strict";

  /**
   * @typedef {Object} AuthState
   * @property {boolean} isLoading
   * @property {Error|Object|string|null} lastError
   */

  /**
   * @typedef {Object} AuthService
   * @property {Function} changePassword
   * @property {Function} logout
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createAuthStore: service is required");
    }
    if (typeof service.changePassword !== "function") {
      throw new Error("createAuthStore: service.changePassword 未实现");
    }
    if (typeof service.logout !== "function") {
      throw new Error("createAuthStore: service.logout 未实现");
    }
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createAuthStore: 需要 mitt 实例");
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
      isLoading: Boolean(state.isLoading),
      lastError: state.lastError,
    };
  }

  /**
   * Auth Store：统一承载认证相关的业务动作（修改密码/登出）。
   *
   * @param {Object} options
   * @param {AuthService} options.service
   * @param {Object} [options.emitter]
   * @return {Object} Store API
   */
  function createAuthStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      isLoading: false,
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function setLoading(loading, meta) {
      state.isLoading = Boolean(loading);
      emit("auth:loading", {
        loading: state.isLoading,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("auth:error", {
        error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

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
      actions: {
        changePassword: function (payload) {
          if (!payload) {
            return Promise.reject(
              new Error("AuthStore: changePassword 需要 payload"),
            );
          }
          setLoading(true, { action: "changePassword" });
          return service
            .changePassword(payload)
            .then(function (response) {
              const result = ensureSuccessResponse(response, "密码修改失败");
              state.lastError = null;
              emit("auth:passwordChanged", {
                response: result,
                state: cloneState(state),
              });
              return result;
            })
            .catch(function (error) {
              handleError(error, { action: "changePassword" });
              throw error;
            })
            .finally(function () {
              setLoading(false, { action: "changePassword" });
            });
        },
        logout: function () {
          setLoading(true, { action: "logout" });
          return service
            .logout()
            .then(function (response) {
              const result = ensureSuccessResponse(response, "登出失败");
              state.lastError = null;
              emit("auth:loggedOut", {
                response: result,
                state: cloneState(state),
              });
              return result;
            })
            .catch(function (error) {
              handleError(error, { action: "logout" });
              throw error;
            })
            .finally(function () {
              setLoading(false, { action: "logout" });
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.isLoading = false;
        state.lastError = null;
      },
    };

    return api;
  }

  window.createAuthStore = createAuthStore;
})(window);

