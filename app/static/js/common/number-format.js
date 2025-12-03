(function (window) {
  "use strict";

  const numeralLib = window.numeral;
  if (typeof numeralLib !== "function") {
    throw new Error("Numeral.js 未加载，无法初始化 NumberFormat");
  }

  const UNIT_IN_BYTES = {
    B: 1,
    KB: 1024,
    MB: 1024 * 1024,
    GB: 1024 * 1024 * 1024,
    TB: 1024 * 1024 * 1024 * 1024,
  };

  /**
   * 将任意输入转换为有限数值。
   *
   * @param {*} value 任意原始输入。
   * @returns {number|null} 有限数值，无法转换时返回 null。
   */
  function toFiniteNumber(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  /**
   * 根据精度与是否保留尾零生成 Numeral 模式。
   *
   * @param {number} precision 需要显示的小数位数。
   * @param {boolean} trimZero 是否去掉尾随零。
   * @returns {string} Numeral.js 支持的格式化模式。
   */
  function buildDecimalPattern(precision, trimZero) {
    if (precision <= 0) {
      return "0,0";
    }
    const zeros = "0".repeat(precision);
    if (trimZero) {
      return `0,0.[${zeros}]`;
    }
    return `0,0.${zeros}`;
  }

  /**
   * 通用格式化函数，value 不可解析时返回 fallback。
   *
   * @param {*} value 待格式化值。
   * @param {string} pattern Numeral.js 模式。
   * @param {string} [fallback] 失败时的回退文本。
   * @returns {string} 格式化结果或回退值。
   */
  function formatWithPattern(value, pattern, fallback) {
    const numeric = toFiniteNumber(value);
    if (numeric === null) {
      return fallback ?? "--";
    }
    return numeralLib(numeric).format(pattern);
  }

  /**
   * 千分位整数格式化，非数字时回退 fallback。
   *
   * @param {*} value 待格式化数值。
   * @param {Object} [options={}] 配置项。
   * @param {string} [options.fallback="0"] 非数字回退文本。
   * @returns {string} 千分位字符串。
   */
  function formatInteger(value, options = {}) {
    const numeric = toFiniteNumber(value);
    if (numeric === null) {
      return options.fallback ?? "0";
    }
    const rounded = Math.round(numeric);
    return numeralLib(rounded).format("0,0");
  }

  /**
   * 保留指定小数的数值格式化。
   *
   * @param {*} value 待格式化数值。
   * @param {Object} [options={}] 配置项。
   * @param {number} [options.precision=2] 小数位。
   * @param {boolean} [options.trimZero=false] 是否去除尾零。
   * @param {string} [options.fallback] 失败时回退文本。
   * @returns {string} 格式化结果。
   */
  function formatDecimal(value, options = {}) {
    const precision =
      Number.isInteger(options.precision) && options.precision >= 0
        ? options.precision
        : 2;
    const trimZero = options.trimZero === undefined ? false : options.trimZero;
    const pattern = buildDecimalPattern(precision, trimZero);
    return formatWithPattern(value, pattern, options.fallback);
  }

  /**
   * 直接使用 Numeral pattern 的封装。
   *
   * @param {*} value 待格式化值。
   * @param {string} [pattern="0,0.00"] Numeral 模式。
   * @param {string} [fallback] 失败回退。
   * @returns {string} 格式化结果。
   */
  function formatPlain(value, pattern = "0,0.00", fallback) {
    return formatWithPattern(value, pattern, fallback);
  }

  /**
   * 规范化单位，确保只返回 B/KB/MB/GB/TB。
   *
   * @param {string} unit 输入单位。
   * @returns {string|null} 合法单位或 null。
   */
  function normalizeUnit(unit) {
    if (!unit) {
      return null;
    }
    const upper = unit.toUpperCase();
    return UNIT_IN_BYTES[upper] ? upper : null;
  }

  /**
   * 将字节数格式化为可读字符串，可指定单位或自动选择。
   *
   * @param {*} bytes 原始字节数。
   * @param {Object} [options={}] 配置项。
   * @param {number} [options.precision=2] 小数位。
   * @param {string} [options.unit] 目标单位（B/KB/.../auto）。
   * @param {boolean} [options.trimZero=true] 是否去尾零。
   * @param {string} [options.fallback="0 B"] 失败时文本。
   * @returns {string} 格式化结果。
   */
  function formatBytes(bytes, options = {}) {
    const numeric = toFiniteNumber(bytes);
    if (numeric === null || numeric === 0) {
      return options.fallback ?? "0 B";
    }
    const precision =
      Number.isInteger(options.precision) && options.precision >= 0
        ? options.precision
        : 2;
    const targetUnit = normalizeUnit(options.unit);
    if (!targetUnit || options.unit === "auto") {
      const pattern = precision > 0 ? `0,0.${"0".repeat(precision)} b` : "0,0 b";
      return numeralLib(numeric).format(pattern);
    }
    const value = numeric / UNIT_IN_BYTES[targetUnit];
    const pattern = buildDecimalPattern(precision, options.trimZero ?? true);
    return `${numeralLib(value).format(pattern)} ${targetUnit}`;
  }

  /**
   * MB 转字节再格式化，常用于容量接口返回 MB。
   *
   * @param {*} value MB 数值。
   * @param {Object} [options={}] 同 formatBytes。
   * @returns {string} 格式化结果。
   */
  function formatBytesFromMB(value, options = {}) {
    const numeric = toFiniteNumber(value);
    if (numeric === null || numeric === 0) {
      return options.fallback ?? "0 B";
    }
    const bytes = numeric * UNIT_IN_BYTES.MB;
    return formatBytes(bytes, options);
  }

  /**
   * 以 GB 为单位输出字符串。
   *
   * @param {*} value 数值。
   * @param {Object} [options={}] 配置项。
   * @returns {string} 格式化后的 GB 文本。
   */
  function formatGigabytes(value, options = {}) {
    const precision =
      Number.isInteger(options.precision) && options.precision >= 0
        ? options.precision
        : 3;
    const formatted = formatDecimal(value, {
      precision,
      trimZero: options.trimZero ?? false,
      fallback: options.fallback ?? "0",
    });
    return `${formatted} GB`;
  }

  /**
   * 百分比格式化，可选择输入为 ratio 或 percent。
   *
   * @param {*} value 输入值。
   * @param {Object} [options={}] 配置项。
   * @param {number} [options.precision=1] 小数位。
   * @param {boolean} [options.trimZero=false] 是否去尾零。
   * @param {boolean} [options.showSign=false] 是否显示 + 号。
   * @param {"ratio"|"percent"} [options.inputType="percent"] 输入类型。
   * @param {string} [options.fallback="0%"] 失败回退。
   * @returns {string} 百分比字符串。
   */
  function formatPercent(value, options = {}) {
    const numeric = toFiniteNumber(value);
    if (numeric === null) {
      return options.fallback ?? "0%";
    }
    const precision =
      Number.isInteger(options.precision) && options.precision >= 0
        ? options.precision
        : 1;
    const inputType = options.inputType === "ratio" ? "ratio" : "percent";
    const ratio = inputType === "ratio" ? numeric : numeric / 100;
    const basePattern = buildDecimalPattern(precision, options.trimZero ?? false);
    const pattern = `${options.showSign ? "+" : ""}${basePattern}%`;
    return numeralLib(ratio).format(pattern);
  }

  /**
   * 将秒数格式化为中文耗时文本。
   *
   * 默认返回纯文本，若需要沿用旧版 badge 展示，可设置 `options.asBadge=true`。
   *
   * @param {*} value 秒数。
   * @param {Object} [options={}] 配置项。
   * @param {boolean} [options.asBadge=false] 是否输出 badge HTML。
   * @param {string} [options.badgeClass='badge bg-info'] 自定义 badge 样式。
   * @returns {string} 文本或 HTML 字符串。
   */
  function formatDurationSeconds(value, options = {}) {
    const seconds = toFiniteNumber(value);
    const asBadge = options.asBadge === true;
    if (seconds === null) {
      return asBadge ? '<span class="text-muted">-</span>' : '-';
    }
    const text = buildDurationText(seconds);
    if (asBadge) {
      const badgeClass = options.badgeClass || 'badge bg-info';
      return `<span class="${badgeClass}">${text}</span>`;
    }
    return text;
  }

  /**
   * 根据秒数生成中文耗时描述。
   *
   * @param {number} seconds 秒数。
   * @returns {string} 耗时文本。
   */
  function buildDurationText(seconds) {
    if (seconds < 60) {
      const text = formatDecimal(seconds, { precision: 1, trimZero: true });
      return `${text}秒`;
    }
    if (seconds < 3600) {
      const minutes = seconds / 60;
      const text = formatDecimal(minutes, { precision: 1, trimZero: true });
      return `${text}分钟`;
    }
    const hours = seconds / 3600;
    const text = formatDecimal(hours, { precision: 1, trimZero: true });
    return `${text}小时`;
  }

  window.NumberFormat = {
    formatInteger,
    formatDecimal,
    formatPlain,
    formatBytes,
    formatBytesFromMB,
    formatGigabytes,
    formatPercent,
    formatDurationSeconds,
  };
})(window);
