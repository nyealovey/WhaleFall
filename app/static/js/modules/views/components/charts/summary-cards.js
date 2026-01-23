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
   *
   * @typedef {Object} Formatters
   * @property {Function} number - 格式化整数
   * @property {Function} sizeFromMB - 格式化字节大小（从 MB 转换）
   * @property {Function} passthrough - 直接返回值
   */
  const defaultFormatters = {
    /**
     * 格式化整数。
     *
     * @param {number} value - 数值
     * @return {string} 格式化后的字符串
     */
    number(value) {
      return window.NumberFormat.formatInteger(value, { fallback: "0" });
    },
    /**
     * 格式化字节大小（从 MB 转换）。
     *
     * @param {number} value - MB 值
     * @param {Object} [options] - 格式化选项
     * @param {string} [options.unit] - 单位，默认 'auto'
     * @param {number} [options.precision] - 精度，默认 2
     * @return {string} 格式化后的字符串
     */
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
    /**
     * 直接返回值。
     *
     * @param {*} value - 任意值
     * @return {string} 值或 '-'
     */
    passthrough(value) {
      if (value === undefined || value === null) {
        return "-";
      }
      return value;
    },
  };

  /**
   * 根据 definition 解析 formatter。
   *
   * @param {Object} definition - 卡片定义对象
   * @param {string|Function} [definition.formatter] - 格式化器名称或函数
   * @return {Function} 格式化函数
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
   *
   * @param {Object} summary - 汇总数据对象
   * @param {Array<Object>} definitions - 卡片定义数组
   * @param {string} definitions[].selector - DOM 选择器
   * @param {string} definitions[].field - 数据字段名
   * @param {string|Function} [definitions[].formatter] - 格式化器
   * @param {Function} [definitions[].resolve] - 自定义解析函数
   * @return {void}
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

      const meta = definition.meta;
      if (!meta || !Array.isArray(meta)) {
        return;
      }
      meta.forEach((metaDef) => {
        if (!metaDef || !metaDef.selector) {
          return;
        }
        const metaEl = selectOne(metaDef.selector);
        if (!metaEl.length) {
          return;
        }
        const metaFormatter = resolveFormatter(metaDef);
        let metaValue = summary?.[metaDef.field];
        if (metaDef.resolve) {
          metaValue = metaDef.resolve(summary);
        }
        metaEl.text(metaFormatter(metaValue));
      });
    });
  }

  window.CapacityStatsSummaryCards = {
    updateCards,
  };
})(window);
