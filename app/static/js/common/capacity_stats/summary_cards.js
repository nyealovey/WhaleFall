(function (window) {
  "use strict";

  const defaultFormatters = {
    number(value) {
      return window.NumberFormat.formatInteger(value, { fallback: "0" });
    },
    sizeFromMB(value, options = {}) {
      return window.NumberFormat.formatBytesFromMB(value, {
        unit: options.unit || "auto",
        precision:
          Number.isInteger(options.precision) && options.precision >= 0
            ? options.precision
            : 2,
        fallback: "0 B",
      });
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
