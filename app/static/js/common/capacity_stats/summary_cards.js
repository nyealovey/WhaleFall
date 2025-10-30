(function (window) {
  "use strict";

  const defaultFormatters = {
    number(value) {
      if (value === undefined || value === null || Number.isNaN(Number(value))) {
        return "0";
      }
      return Number(value).toLocaleString();
    },
    sizeFromMB(value) {
      const numeric = Number(value);
      if (!Number.isFinite(numeric) || numeric <= 0) {
        return "0 B";
      }
      if (numeric < 1024) {
        return `${numeric.toFixed(2)} MB`;
      }
      if (numeric < 1024 * 1024) {
        return `${(numeric / 1024).toFixed(2)} GB`;
      }
      return `${(numeric / (1024 * 1024)).toFixed(2)} TB`;
    },
    passthrough(value) {
      if (value === undefined || value === null) {
        return "-";
      }
      return value;
    },
  };

  function resolveFormatter(definition) {
    if (!definition || !definition.formatter) {
      return defaultFormatters.passthrough;
    }
    if (typeof definition.formatter === "function") {
      return definition.formatter;
    }
    return defaultFormatters[definition.formatter] || defaultFormatters.passthrough;
  }

  function updateCards(summary, definitions) {
    if (!definitions || !Array.isArray(definitions)) {
      return;
    }
    definitions.forEach((definition) => {
      if (!definition || !definition.selector) {
        return;
      }
      const element = document.querySelector(definition.selector);
      if (!element) {
        return;
      }
      const formatter = resolveFormatter(definition);
      let value = summary?.[definition.field];
      if (definition.resolve) {
        value = definition.resolve(summary);
      }
      element.textContent = formatter(value);
    });
  }

  window.CapacityStatsSummaryCards = {
    updateCards,
  };
})(window);
