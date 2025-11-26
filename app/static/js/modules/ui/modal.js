(function (global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法注册 Modal 组件");
    return;
  }

  /**
   * 解析多种输入为 DOM 元素。
   *
   * @param {string|Element|Object} target 选择器、原生元素或 umbrella 对象。
   * @returns {Element|null} 匹配到的元素。
   */
  function toElement(target) {
    if (!target) {
      return null;
    }
    if (typeof target === "string") {
      return document.querySelector(target);
    }
    if (target instanceof Element) {
      return target;
    }
    if (target && typeof target.first === "function") {
      return target.first();
    }
    return null;
  }

  /**
   * 确保 bootstrap.Modal 已加载。
   *
   * @param {Window} [context=global] 可选的 bootstrap 来源。
   * @returns {Object} bootstrap 全局对象。
   * @throws {Error} 当 Modal 插件缺失时抛出。
   */
  function ensureBootstrap(context = global) {
    const bootstrap = context.bootstrap;
    if (!bootstrap?.Modal) {
      throw new Error("bootstrap.Modal 未加载");
    }
    return bootstrap;
  }

  /**
   * 通用模态包装器：支持 onOpen/onClose/onConfirm/onCancel。
   *
   * @param {Object} [options={}] 组件配置。
   * @param {string|Element|Object} options.modalSelector 目标模态元素。
   * @param {Function} [options.onOpen] 打开回调。
   * @param {Function} [options.onClose] 关闭回调。
   * @param {Function} [options.onConfirm] 确认回调。
   * @param {Function} [options.onCancel] 取消回调。
   * @param {string} [options.confirmSelector] 确认按钮选择器。
   * @param {string} [options.cancelSelector] 取消按钮选择器。
   * @param {string|Element|Object} [options.loadingSelector] 自定义 loading 目标。
   * @param {string} [options.loadingText="处理中..."] Loading 文案。
   * @returns {Object|null} 暴露 open/close/setLoading/destroy 的 API。
   */
  function createModal({
    modalSelector,
    onOpen,
    onClose,
    onConfirm,
    onCancel,
    confirmSelector = "[data-modal-confirm]",
    cancelSelector = "[data-modal-cancel]",
    loadingSelector,
    loadingText = "处理中...",
  } = {}) {
    const bootstrap = ensureBootstrap(global);
    const modalElement = toElement(modalSelector);
    if (!modalElement) {
      console.error("Modal 元素未找到", modalSelector);
      return null;
    }

    const instance = bootstrap.Modal.getOrCreateInstance(modalElement);
    const listeners = [];
    let confirmButton = loadingSelector ? toElement(loadingSelector) : modalElement.querySelector(confirmSelector);

    /**
     * 切换确认按钮 loading 状态。
     *
     * @param {boolean} isLoading 是否开启 loading。
     * @param {string} [text=loadingText] 自定义展示文案。
     * @returns {void}
     */
    function setLoading(isLoading, text = loadingText) {
      if (!confirmButton) {
        return;
      }
      if (isLoading) {
        confirmButton.dataset.originalHtml = confirmButton.innerHTML;
        confirmButton.innerHTML = `<span class=\"spinner-border spinner-border-sm me-2\"></span>${text}`;
        confirmButton.disabled = true;
      } else {
        confirmButton.innerHTML = confirmButton.dataset.originalHtml || confirmButton.innerHTML;
        confirmButton.disabled = false;
        delete confirmButton.dataset.originalHtml;
      }
    }

    /**
     * 打开模态框并记录 payload。
     *
     * @param {*} payload 需要在 confirm/cancel 时传回的数据。
     * @returns {void}
     */
    function open(payload) {
      modalElement.dataset.modalPayload = payload ? JSON.stringify(payload) : "";
      instance.show();
    }

    /**
     * 关闭模态框。
     *
     * @param {Event} [event] 可选触发事件，用于阻止默认行为。
     * @returns {void}
     */
    function close(event) {
      event?.preventDefault?.();
      instance.hide();
    }

    /**
     * `shown.bs.modal` 回调。
     *
     * @param {Event} event Bootstrap 事件对象。
     * @returns {void}
     */
    function handleShown(event) {
      onOpen?.({ event, modal: api, payload: modalElement.dataset.modalPayload });
    }

    /**
     * `hidden.bs.modal` 回调，负责清理状态。
     *
     * @param {Event} event Bootstrap 事件对象。
     * @returns {void}
     */
    function handleHidden(event) {
      onClose?.({ event, modal: api, payload: modalElement.dataset.modalPayload });
      modalElement.dataset.modalPayload = "";
      setLoading(false);
    }

    /**
     * 处理确认按钮点击。
     *
     * @param {Event} event 鼠标或键盘事件。
     * @returns {void}
     */
    function handleConfirm(event) {
      event?.preventDefault?.();
      onConfirm?.({ event, modal: api, payload: modalElement.dataset.modalPayload });
    }

    /**
     * 处理取消按钮点击。
     *
     * @param {Event} event 原始事件。
     * @returns {void}
     */
    function handleCancel(event) {
      onCancel?.({ event, modal: api, payload: modalElement.dataset.modalPayload });
    }

    modalElement.addEventListener("shown.bs.modal", handleShown);
    modalElement.addEventListener("hidden.bs.modal", handleHidden);
    listeners.push(() => {
      modalElement.removeEventListener("shown.bs.modal", handleShown);
      modalElement.removeEventListener("hidden.bs.modal", handleHidden);
    });

    const confirmEl = modalElement.querySelector(confirmSelector) || confirmButton;
    if (confirmEl) {
      confirmEl.addEventListener("click", handleConfirm);
      listeners.push(() => confirmEl.removeEventListener("click", handleConfirm));
    }

    const cancelEl = modalElement.querySelector(cancelSelector) || modalElement.querySelector("[data-bs-dismiss='modal']");
    if (cancelEl) {
      cancelEl.addEventListener("click", handleCancel);
      listeners.push(() => cancelEl.removeEventListener("click", handleCancel));
    }

    const api = {
      element: modalElement,
      open,
      close,
      setLoading,
      destroy() {
        listeners.forEach((fn) => fn());
        instance.dispose();
      },
    };

    return api;
  }

  global.UI = global.UI || {};
  global.UI.createModal = createModal;
})(window);
