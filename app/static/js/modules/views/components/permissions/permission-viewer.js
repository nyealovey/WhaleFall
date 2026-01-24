(function (window) {
  "use strict";

  /**
   * PermissionViewer：权限查看组件（纯 views），通过依赖注入获取数据源与展示能力。
   *
   * MUST:
   * - 不在组件内部 new Service
   * - 不直连 httpU
   * - 必须先 configure(...) 再调用 viewAccountPermissions(...)
   */

  const state = {
    /** @type {Function|null} */
    fetchPermissions: null,
    /** @type {Function|null} */
    showPermissionsModal: null,
    /** @type {Object|null} */
    toast: null,
  };

  function ensureConfigured() {
    if (typeof state.fetchPermissions !== "function") {
      throw new Error("PermissionViewer 未配置: 缺少 fetchPermissions");
    }
    if (typeof state.showPermissionsModal !== "function") {
      throw new Error("PermissionViewer 未配置: 缺少 showPermissionsModal");
    }
    if (!state.toast) {
      throw new Error("PermissionViewer 未配置: 缺少 toast");
    }
  }

  /**
   * 配置依赖（由 Page Entry 调用）。
   *
   * @param {Object} options
   * @param {Function} options.fetchPermissions - (params) => Promise(response)
   * @param {Function} options.showPermissionsModal - (permissions, account, { scope }) => void
   * @param {Object} options.toast - toast 实例
   */
  function configure(options) {
    const opts = options || {};
    if (typeof opts.fetchPermissions !== "function") {
      throw new Error("PermissionViewer.configure: fetchPermissions 必须为函数");
    }
    if (typeof opts.showPermissionsModal !== "function") {
      throw new Error("PermissionViewer.configure: showPermissionsModal 必须为函数");
    }
    if (!opts.toast) {
      throw new Error("PermissionViewer.configure: toast 未提供");
    }
    state.fetchPermissions = opts.fetchPermissions;
    state.showPermissionsModal = opts.showPermissionsModal;
    state.toast = opts.toast;
  }

  /**
   * 从事件或传入引用解析出按钮。
   *
   * @param {Element|Event|Object} trigger - 按钮引用或事件对象
   * @return {Element|null} 按钮元素，未找到则返回 null
   */
  function resolveButton(trigger) {
    if (trigger instanceof Element) {
      return trigger;
    }
    if (trigger?.currentTarget instanceof Element) {
      return trigger.currentTarget;
    }
    if (trigger?.target instanceof Element) {
      return trigger.target;
    }
    return null;
  }

  /**
   * 控制按钮 loading 状态，防重复点击。
   *
   * @param {Element|null} button - 按钮元素
   * @param {boolean} isLoading - 是否显示加载状态
   * @return {void}
   */
  function toggleButtonLoading(button, isLoading) {
    if (!(button instanceof Element)) {
      return;
    }
    if (isLoading) {
      if (!button.dataset.originalHtml) {
        button.dataset.originalHtml = button.innerHTML || "";
      }
      button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>加载中...';
      button.setAttribute("disabled", "disabled");
      button.setAttribute("aria-busy", "true");
      return;
    }
    const original = button.dataset.originalHtml || "";
    if (original) {
      button.innerHTML = original;
      delete button.dataset.originalHtml;
    }
    button.removeAttribute("disabled");
    button.removeAttribute("aria-busy");
  }

  /**
   * 入口：查看账户权限并展示模态。
   *
   * @param {number|string} accountId - 账户 ID
   * @param {Object} [options] - 配置选项
   * @param {string} [options.apiUrl] - API 地址（可选，优先级高于 accountId 默认路径）
   * @param {Function} [options.onSuccess] - 成功回调
   * @param {Function} [options.onError] - 错误回调
   * @param {Function} [options.onFinally] - 完成回调
   * @param {Element|Event} [options.trigger] - 触发元素
   * @param {string} [options.scope] - 权限模态框 scope，用于派生 DOM id
   * @return {void}
   */
  function viewAccountPermissions(accountId, options) {
    ensureConfigured();

    const opts = options || {};
    const triggerButton = resolveButton(opts.trigger);
    toggleButtonLoading(triggerButton, true);

    state.fetchPermissions({ accountId, apiUrl: opts.apiUrl })
      .then((data) => {
        const responsePayload = data?.data;
        if (data?.success && responsePayload && typeof responsePayload === "object") {
          state.showPermissionsModal(
            responsePayload?.permissions,
            responsePayload?.account,
            { scope: opts.scope },
          );
          opts.onSuccess?.(responsePayload);
          return;
        }
        const errorMsg = data?.error || data?.message || "获取权限信息失败";
        state.toast?.error?.(errorMsg);
        opts.onError?.(data);
      })
      .catch((error) => {
        state.toast?.error?.("获取权限信息失败");
        opts.onError?.(error);
      })
      .finally(() => {
        toggleButtonLoading(triggerButton, false);
        opts.onFinally?.();
      });
  }

  /**
   * 直接拉取账户权限数据（返回 Promise）。
   *
   * @param {number|string} accountId - 账户 ID
   * @param {Object} [options]
   * @param {string} [options.apiUrl] - API 地址
   * @return {Promise<Object>} 权限数据 Promise
   * @throws {Error} 当获取失败时抛出
   */
  function fetchAccountPermissions(accountId, options) {
    ensureConfigured();
    const opts = options || {};
    return state.fetchPermissions({ accountId, apiUrl: opts.apiUrl }).then((data) => {
      if (data?.success && data.data && typeof data.data === "object") {
        return data.data;
      }
      throw new Error(data?.error || data?.message || "获取权限信息失败");
    });
  }

  window.PermissionViewer = {
    configure,
    viewAccountPermissions,
    fetchAccountPermissions,
  };
})(window);

