(function (window) {
  "use strict";

  function ensureService(service) {
    if (!service) {
      throw new Error("createCredentialsStore: service is required");
    }
    if (typeof service.deleteCredential !== "function") {
      throw new Error("createCredentialsStore: service.deleteCredential 未实现");
    }
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

  function ensureDeleteResponse(response) {
    if (response && response.success === false) {
      const error = new Error(response.message || "删除凭据失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  function cloneState(state) {
    return {
      deletingIds: new Set(state.deletingIds),
      lastError: state.lastError,
    };
  }

  function createCredentialsStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      deletingIds: new Set(),
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
        deleteCredential: function (credentialId) {
          if (!credentialId && credentialId !== 0) {
            return Promise.reject(
              new Error("CredentialsStore: 需要 credentialId"),
            );
          }
          const numericId = Number(credentialId);
          state.deletingIds.add(numericId);
          emit("credentials:deleting", {
            credentialId: numericId,
            state: cloneState(state),
          });
          return service
            .deleteCredential(numericId)
            .then(function (response) {
              const result = ensureDeleteResponse(response);
              state.lastError = null;
              emit("credentials:deleted", {
                credentialId: numericId,
                response: result,
                state: cloneState(state),
              });
              return result;
            })
            .catch(function (error) {
              handleError(error, { credentialId: numericId });
              throw error;
            })
            .finally(function () {
              state.deletingIds.delete(numericId);
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.deletingIds.clear();
      },
    };

    return api;
  }

  window.createCredentialsStore = createCredentialsStore;
})(window);
