(function (window) {
  "use strict";

  const DOMHelpers = window.DOMHelpers;
  const UI = window.UI || {};

  /**
   * 解析目标为 DOM 元素，兼容选择器和 umbrella 的 first()。
   *
   * @param {string|Element|Object} target - 目标元素或选择器
   * @return {Element|null} DOM 元素，未找到则返回 null
   */
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

  /**
   * 在容器中解析实际的 .modal 元素，支持直接传入 modal 节点。
   *
   * @param {Element} container - 容器元素
   * @return {Element|null} 模态框元素，未找到则返回 null
   */
  function resolveModalElement(container) {
    if (!container) {
      return null;
    }
    if (container.matches && container.matches(".modal")) {
      return container;
    }
    return container.querySelector ? container.querySelector(".modal") : null;
  }

  /**
   * 为标签选择器创建模态适配层，统一封装 open/close/setLoading。
   *
   * @param {Element} container - 容器元素
   * @param {Object} [hooks] - 钩子函数
   * @param {Function} [hooks.onOpen] - 打开回调
   * @param {Function} [hooks.onClose] - 关闭回调
   * @param {Function} [hooks.onConfirm] - 确认回调
   * @param {Function} [hooks.onCancel] - 取消回调
   * @return {Object|null} 模态适配器对象，包含 open、close、setLoading 方法
   */
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
      confirmSelector: '[data-tag-selector-action="confirm"]',
      cancelSelector: '[data-tag-selector-action="cancel"]',
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
