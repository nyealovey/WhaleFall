(function (window) {
  "use strict";

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法更新容量统计卡片");
    return;
  }

  const { selectOne } = helpers;

  /**
   * 常用卡片值格式化器。
   */
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

  /**
   * 根据 definition 解析 formatter。
   */
  function resolveFormatter(definition) {
    if (!definition || !definition.formatter) {
      return defaultFormatters.passthrough;
    }
    if (typeof definition.formatter === "function") {
      return definition.formatter;
    }
    return defaultFormatters[definition.formatter] || defaultFormatters.passthrough;
  }

  /**
   * 遍历 definitions，写入格式化后的值。
   */
  function updateCards(summary, definitions) {
    if (!definitions || !Array.isArray(definitions)) {
      return;
    }
    definitions.forEach((definition) => {
      if (!definition || !definition.selector) {
        return;
      }
      const element = selectOne(definition.selector);
      if (!element.length) {
        return;
      }
      const formatter = resolveFormatter(definition);
      let value = summary?.[definition.field];
      if (definition.resolve) {
        value = definition.resolve(summary);
      }
      element.text(formatter(value));
    });
  }

  window.CapacityStatsSummaryCards = {
    updateCards,
  };
})(window);
