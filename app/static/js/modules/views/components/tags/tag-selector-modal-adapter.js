(function (window) {
  "use strict";

  const DOMHelpers = window.DOMHelpers;
  const UI = window.UI || {};

  function toElement(target) {
    if (!target) {
      return null;
    }
    if (target instanceof Element) {
      return target;
    }
    if (typeof target === "string") {
      return document.querySelector(target);
    }
    if (target && typeof target.first === "function") {
      return target.first();
    }
    return null;
  }

  function resolveModalElement(container) {
    if (!container) {
      return null;
    }
    if (container.matches && container.matches(".modal")) {
      return container;
    }
    return container.querySelector ? container.querySelector(".modal") : null;
  }

  function createModalAdapter(container, hooks = {}) {
    const modalElement = resolveModalElement(container);
    if (!modalElement) {
      return null;
    }
    const factory = window.UI?.createModal;
    if (!factory) {
      console.error("TagSelectorModalAdapter: UI.createModal 未加载");
      return null;
    }
    const modal = factory({
      modalSelector: modalElement,
      onOpen: hooks.onOpen,
      onClose: hooks.onClose,
      onConfirm: hooks.onConfirm,
      onCancel: hooks.onCancel,
    });
    return {
      open: modal?.open?.bind(modal) || (() => {}),
      close: modal?.close?.bind(modal) || (() => {}),
      setLoading: modal?.setLoading?.bind(modal) || (() => {}),
      instance: modal,
    };
  }

  window.TagSelectorModalAdapter = {
    resolveModalElement,
    createModalAdapter,
  };
})(window);
