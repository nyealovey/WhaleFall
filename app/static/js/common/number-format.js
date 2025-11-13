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

  function toFiniteNumber(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

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

  function formatWithPattern(value, pattern, fallback) {
    const numeric = toFiniteNumber(value);
    if (numeric === null) {
      return fallback ?? "--";
    }
    return numeralLib(numeric).format(pattern);
  }

  function formatInteger(value, options = {}) {
    const numeric = toFiniteNumber(value);
    if (numeric === null) {
      return options.fallback ?? "0";
    }
    const rounded = Math.round(numeric);
    return numeralLib(rounded).format("0,0");
  }

  function formatDecimal(value, options = {}) {
    const precision =
      Number.isInteger(options.precision) && options.precision >= 0
        ? options.precision
        : 2;
    const trimZero = options.trimZero === undefined ? false : options.trimZero;
    const pattern = buildDecimalPattern(precision, trimZero);
    return formatWithPattern(value, pattern, options.fallback);
  }

  function formatPlain(value, pattern = "0,0.00", fallback) {
    return formatWithPattern(value, pattern, fallback);
  }

  function normalizeUnit(unit) {
    if (!unit) {
      return null;
    }
    const upper = unit.toUpperCase();
    return UNIT_IN_BYTES[upper] ? upper : null;
  }

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

  function formatBytesFromMB(value, options = {}) {
    const numeric = toFiniteNumber(value);
    if (numeric === null || numeric === 0) {
      return options.fallback ?? "0 B";
    }
    const bytes = numeric * UNIT_IN_BYTES.MB;
    return formatBytes(bytes, options);
  }

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

  function formatDurationSeconds(value) {
    const seconds = toFiniteNumber(value);
    if (seconds === null) {
      return '<span class="text-muted">-</span>';
    }
    if (seconds < 60) {
      const text = formatDecimal(seconds, { precision: 1, trimZero: true });
      return `<span class="badge bg-info">${text}秒</span>`;
    }
    if (seconds < 3600) {
      const minutes = seconds / 60;
      const text = formatDecimal(minutes, { precision: 1, trimZero: true });
      return `<span class="badge bg-info">${text}分钟</span>`;
    }
    const hours = seconds / 3600;
    const text = formatDecimal(hours, { precision: 1, trimZero: true });
    return `<span class="badge bg-info">${text}小时</span>`;
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
