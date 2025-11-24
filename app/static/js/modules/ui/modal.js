(function (global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法注册 Modal 组件");
    return;
  }

  /**
   * 解析多种输入为 DOM 元素。
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
   */
  function ensureBootstrap() {
    const bootstrap = global.bootstrap;
    if (!bootstrap?.Modal) {
      throw new Error("bootstrap.Modal 未加载");
    }
    return bootstrap;
  }

  /**
   * 通用模态包装器：支持 onOpen/onClose/onConfirm/onCancel。
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
    const bootstrap = ensureBootstrap();
    const modalElement = toElement(modalSelector);
    if (!modalElement) {
      console.error("Modal 元素未找到", modalSelector);
      return null;
    }

    const instance = bootstrap.Modal.getOrCreateInstance(modalElement);
    const listeners = [];
    let confirmButton = loadingSelector ? toElement(loadingSelector) : modalElement.querySelector(confirmSelector);

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

    function open(payload) {
      modalElement.dataset.modalPayload = payload ? JSON.stringify(payload) : "";
      instance.show();
    }

    function close() {
      instance.hide();
    }

    function handleShown(event) {
      onOpen?.({ event, modal: api, payload: modalElement.dataset.modalPayload });
    }

    function handleHidden(event) {
      onClose?.({ event, modal: api, payload: modalElement.dataset.modalPayload });
      modalElement.dataset.modalPayload = "";
      setLoading(false);
    }

    function handleConfirm(event) {
      event?.preventDefault?.();
      onConfirm?.({ event, modal: api, payload: modalElement.dataset.modalPayload });
    }

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
