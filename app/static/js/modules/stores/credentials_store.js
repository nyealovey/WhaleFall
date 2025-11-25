(function (window) {
  "use strict";

  /**
   * @typedef {Object} CredentialsState
   * @property {Set<number>} deletingIds - 正在删除的凭据 ID 集合
   * @property {Error|null} lastError - 最后的错误
   */

  /**
   * @typedef {Object} CredentialsService
   * @property {Function} deleteCredential - 删除凭据的方法
   */

  /**
   * 校验 service 是否实现删除接口。
   *
   * 检查服务对象是否存在，并验证是否实现了 deleteCredential 方法。
   *
   * @param {CredentialsService} service - 服务对象
   * @return {CredentialsService} 校验后的服务对象
   * @throws {Error} 当 service 为空或缺少 deleteCredential 方法时抛出
   */
  function ensureService(service) {
    if (!service) {
      throw new Error("createCredentialsStore: service is required");
    }
    if (typeof service.deleteCredential !== "function") {
      throw new Error("createCredentialsStore: service.deleteCredential 未实现");
    }
    return service;
  }

  /**
   * 获取 mitt 事件总线实例。
   *
   * 如果提供了 emitter 则直接返回，否则尝试从 window.mitt 创建新实例。
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
      throw new Error("createCredentialsStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  /**
   * 检查删除响应是否成功。
   *
   * @param {Object} response - 后端响应对象
   * @return {Object} 响应对象
   * @throws {Error} 当 response.success 为 false 时抛出
   */
  function ensureDeleteResponse(response) {
    if (response && response.success === false) {
      const error = new Error(response.message || "删除凭据失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  /**
   * 复制 state，用于事件传值。
   *
   * @param {CredentialsState} state - 状态对象
   * @return {CredentialsState} 深拷贝后的状态快照
   */
  function cloneState(state) {
    return {
      deletingIds: new Set(state.deletingIds),
      lastError: state.lastError,
    };
  }

  /**
   * 创建凭据管理 Store。
   *
   * 提供凭据删除操作的状态管理和事件发布订阅。
   * 支持删除凭据、跟踪删除状态和错误处理。
   *
   * @param {Object} options - 配置选项
   * @param {CredentialsService} options.service - 凭据服务实例
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @return {Object} Store API 对象
   * @throws {Error} 当 service 无效或 emitter 不可用时抛出
   *
   * @example
   * const store = createCredentialsStore({
   *   service: new CredentialsService(httpU),
   *   emitter: mitt()
   * });
   * store.actions.deleteCredential(123);
   */
  function createCredentialsStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      deletingIds: new Set(),
      lastError: null,
    };

    /**
     * 发布 mitt 事件并附带最新状态。
     *
     * @param {string} eventName 事件名称。
     * @param {Object} [payload] 附加信息，默认携带 state 快照。
     */
    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    /**
     * 统一处理错误并广播 error 事件。
     *
     * @param {Error|Object|string} error 服务返回的错误。
     * @param {Object} meta 调试所需的上下文字段。
     */
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
