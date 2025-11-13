(function (window) {
  "use strict";

  const defaultFormatters = {
    number(value) {
      if (window.NumberFormat) {
        return window.NumberFormat.formatInteger(value, { fallback: "0" });
      }
      const numeric = Number(value);
      return Number.isFinite(numeric) ? `${Math.round(numeric)}` : "0";
    },
    sizeFromMB(value, options = {}) {
      if (window.NumberFormat) {
        return window.NumberFormat.formatBytesFromMB(value, {
          unit: options.unit || "auto",
          precision:
            Number.isInteger(options.precision) && options.precision >= 0
              ? options.precision
              : 2,
          fallback: "0 B",
        });
      }
      const numeric = Number(value);
      if (!Number.isFinite(numeric) || numeric <= 0) {
        return "0 B";
      }
      if (numeric < 1024) {
        return `${numeric} MB`;
      }
      if (numeric < 1024 * 1024) {
        return `${numeric / 1024} GB`;
      }
      return `${numeric / (1024 * 1024)} TB`;
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
