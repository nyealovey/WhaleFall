(function (global) {
  "use strict";

  const helpers = global.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法注册按钮 loading 工具");
    return;
  }

  const { from } = helpers;

  /**
   * 判断按钮是否为 icon-only（默认通过 btn-icon 约定识别）。
   *
   * @param {Element} node DOM 节点。
   * @returns {boolean} 是否 icon-only。
   */
  function isIconOnlyButton(node) {
    return Boolean(node?.classList?.contains("btn-icon"));
  }

  /**
   * 为按钮渲染 spinner，并在需要时附加 loading 文案。
   *
   * @param {HTMLButtonElement} node 按钮节点。
   * @param {Object} options 配置项。
   * @param {string} [options.loadingText] loading 文案。
   * @param {boolean} [options.iconOnly] 是否为 icon-only。
   * @returns {void}
   */
  function renderLoadingContent(node, { loadingText, iconOnly }) {
    node.innerHTML = "";

    const icon = document.createElement("i");
    icon.className = iconOnly ? "fas fa-spinner fa-spin" : "fas fa-spinner fa-spin me-2";
    icon.setAttribute("aria-hidden", "true");
    node.appendChild(icon);

    if (!iconOnly && loadingText) {
      node.appendChild(document.createTextNode(loadingText));
    }
  }

  /**
   * 统一设置按钮加载态。
   *
   * @param {string|Element|NodeList|Array<Element>|Object} target 目标按钮或选择器/Umbrella 集合。
   * @param {Object} [options={}] 配置项。
   * @param {string} [options.loadingText] loading 文案。
   * @param {"auto"|"icon-only"|"with-text"} [options.mode="auto"] 渲染模式。
   * @returns {void}
   */
  function setButtonLoading(target, options = {}) {
    const elements = from(target);
    if (!elements.length) {
      return;
    }

    const mode = options?.mode || "auto";
    const loadingText = options?.loadingText || "";

    elements.each((node) => {
      if (!node) {
        return;
      }

      const dataset = node.dataset || {};
      if (typeof dataset.uiOriginalHtml === "undefined") {
        dataset.uiOriginalHtml = node.innerHTML;
      }
      if (typeof dataset.uiOriginalDisabled === "undefined" && "disabled" in node) {
        dataset.uiOriginalDisabled = node.disabled ? "1" : "0";
      }

      let iconOnly = false;
      if (mode === "icon-only") {
        iconOnly = true;
      } else if (mode === "with-text") {
        iconOnly = false;
      } else {
        iconOnly = isIconOnlyButton(node);
      }

      renderLoadingContent(node, { loadingText, iconOnly });
      dataset.uiLoading = "1";
      node.setAttribute("aria-busy", "true");

      const hasAriaLabel = node.hasAttribute?.("aria-label");
      const hasAriaLabelledBy = node.hasAttribute?.("aria-labelledby");
      const title = node.getAttribute?.("title");
      if (!hasAriaLabel && !hasAriaLabelledBy && title) {
        node.setAttribute("aria-label", title);
      }

      if ("disabled" in node) {
        node.disabled = true;
      } else {
        node.setAttribute("aria-disabled", "true");
      }
    });
  }

  /**
   * 清理按钮加载态并恢复原内容。
   *
   * @param {string|Element|NodeList|Array<Element>|Object} target 目标按钮或选择器/Umbrella 集合。
   * @param {Object} [options={}] 配置项。
   * @param {string} [options.fallbackText] 找不到缓存内容时的兜底文本。
   * @returns {void}
   */
  function clearButtonLoading(target, options = {}) {
    const elements = from(target);
    if (!elements.length) {
      return;
    }

    const fallbackText = options?.fallbackText || "";

    elements.each((node) => {
      if (!node) {
        return;
      }

      const dataset = node.dataset || {};
      const originalHtml = dataset.uiOriginalHtml;
      if (typeof originalHtml !== "undefined") {
        node.innerHTML = originalHtml;
        delete dataset.uiOriginalHtml;
      } else if (fallbackText) {
        node.textContent = fallbackText;
      }

      delete dataset.uiLoading;
      node.removeAttribute?.("aria-busy");
      node.removeAttribute?.("aria-disabled");

      if ("disabled" in node) {
        const originalDisabled = dataset.uiOriginalDisabled;
        if (typeof originalDisabled !== "undefined") {
          node.disabled = originalDisabled === "1";
          delete dataset.uiOriginalDisabled;
        } else {
          node.disabled = false;
        }
      }
    });
  }

  global.UI = global.UI || {};
  global.UI.setButtonLoading = setButtonLoading;
  global.UI.clearButtonLoading = clearButtonLoading;
})(window);
