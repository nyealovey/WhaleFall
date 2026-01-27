(function (global) {
  "use strict";

  function escapeHtml(value) {
    if (value === undefined || value === null) {
      return "";
    }
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function resolveErrorMessage(error, fallback = "操作失败") {
    const fallbackText = fallback || "操作失败";
    if (!error) {
      return fallbackText;
    }
    if (typeof error === "string") {
      return error;
    }
    if (typeof error.message === "string" && error.message.trim()) {
      return error.message;
    }
    if (typeof error.error === "string" && error.error.trim()) {
      return error.error;
    }
    if (typeof error.detail === "string" && error.detail.trim()) {
      return error.detail;
    }

    const nested = error?.response?.data || error?.data || null;
    if (nested) {
      if (typeof nested === "string") {
        return nested;
      }
      if (typeof nested.message === "string" && nested.message.trim()) {
        return nested.message;
      }
      if (typeof nested.error === "string" && nested.error.trim()) {
        return nested.error;
      }
      if (typeof nested.detail === "string" && nested.detail.trim()) {
        return nested.detail;
      }
    }

    return fallbackText;
  }

  function renderChipStack(names, options = {}) {
    const {
      gridHtml,
      emptyText = "无数据",
      baseClass = "ledger-chip",
      baseModifier = "",
      counterClass = "ledger-chip ledger-chip--counter",
      maxItems = 2,
      separator = " · ",
      wrapperClass = "ledger-chip-stack",
    } = options;

    const sanitized = (names || [])
      .filter((name) => typeof name === "string" && name.trim().length > 0)
      .map((name) => escapeHtml(name.trim()));

    if (!sanitized.length) {
      return gridHtml
        ? gridHtml(`<span class="text-muted">${escapeHtml(emptyText)}</span>`)
        : emptyText;
    }

    if (typeof gridHtml !== "function") {
      return sanitized.join(", ");
    }

    const limit = Number.isFinite(maxItems) ? maxItems : sanitized.length;
    const visible = sanitized.slice(0, limit).join(separator);
    const baseClasses = [baseClass, baseModifier].filter(Boolean).join(" ").trim();
    const chips = [`<span class="${baseClasses}">${visible}</span>`];

    if (sanitized.length > limit) {
      const rest = sanitized.length - limit;
      chips.push(`<span class="${counterClass}">+${rest}</span>`);
    }

    return gridHtml(`<div class="${wrapperClass}">${chips.join("")}</div>`);
  }

  global.UI.escapeHtml = escapeHtml;
  global.UI.resolveErrorMessage = resolveErrorMessage;
  global.UI.renderChipStack = renderChipStack;
})(window);
