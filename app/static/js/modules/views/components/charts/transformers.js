(function (window) {
  "use strict";

  const LodashUtils = window.LodashUtils;
  if (!LodashUtils) {
    throw new Error("LodashUtils 未初始化");
  }

  const COLOR_PALETTE = [
    "#FF6384",
    "#36A2EB",
    "#FFCE56",
    "#4BC0C0",
    "#9966FF",
    "#FF9F40",
    "#C9CBCF",
    "#FF6B6B",
    "#4ECDC4",
    "#45B7D1",
    "#96CEB4",
    "#FFEAA7",
    "#DDA0DD",
    "#98D8C8",
    "#F7DC6F",
    "#BB8FCE",
    "#85C1E9",
    "#F8C471",
    "#82E0AA",
  ];

  /**
   * 将 hex 颜色转换为带透明度的 rgba。
   *
   * @param {string} hexColor - 十六进制颜色值
   * @param {number} alpha - 透明度（0-1）
   * @return {string} rgba 颜色字符串
   */
  function colorWithAlpha(hexColor, alpha) {
    const normalized = hexColor.startsWith("#")
      ? hexColor.slice(1)
      : hexColor;
    if (normalized.length !== 6) {
      return `rgba(0, 0, 0, ${alpha})`;
    }
    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  /**
   * 解析标签，支持函数或字段名。
   *
   * @param {Function|string} extractor - 标签提取函数或字段名
   * @param {Object} item - 数据项
   * @return {Object} 包含 key 和 label 的对象
   */
  function normalizeLabel(extractor, item) {
    if (typeof extractor === "function") {
      const result = extractor(item) || {};
      return {
        key: result.key || result.label || "unknown",
        label: result.label || result.key || "未知",
      };
    }
    const label = item?.[extractor] ?? "未知";
    return { key: label, label };
  }

  /**
   * 将值转换为 number，无法解析返回 null。
   *
   * @param {*} value 原始数值。
   * @returns {number|null} 可用数字或 null。
   */
  function normalizeValue(value) {
    if (value === null || value === undefined) {
      return null;
    }
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  /**
   * 将数据按日期与标签 key 组织成矩阵，便于生成 datasets。
   *
   * @param {Array<Object>} items 原始数据列表。
   * @param {Function|string} labelExtractor 标签提取器。
   * @param {Function} valueAccessor 返回数值的函数。
   * @returns {{dateMatrix: Map<string, Map<string, number|null>>, labelMaxValue: Map<string, number>, labelNames: Map<string, string>}}
   */
  function collectDateMatrix(items, labelExtractor, valueAccessor) {
    const dateMatrix = new Map(); // date -> Map(key -> value)
    const labelMaxValue = new Map(); // key -> max absolute value
    const labelNames = new Map(); // key -> display label

    items.forEach((item) => {
      const date = item?.period_end;
      if (!date) {
        return;
      }

      const { key, label } = normalizeLabel(labelExtractor, item);
      labelNames.set(key, label);

      const value = valueAccessor(item);
      if (!dateMatrix.has(date)) {
        dateMatrix.set(date, new Map());
      }
      dateMatrix.get(date).set(key, value);

      if (value !== null) {
        const absValue = Math.abs(value);
        const existing = labelMaxValue.get(key) || 0;
        if (absValue > existing) {
          labelMaxValue.set(key, absValue);
        }
      }
    });

    return { dateMatrix, labelMaxValue, labelNames };
  }

  /**
   * 根据矩阵与配色生成 Chart.js datasets。
   *
   * @param {Object} config 构建配置。
   * @param {Array<string>} config.labels 日期标签列表。
   * @param {Array<string>} config.sortedKeys 需要渲染的 key 顺序。
   * @param {Map<string, Map<string, number|null>>} config.dateMatrix 日期矩阵。
   * @param {Map<string, string>} config.labelNames key 与展示文本。
   * @param {Array<string>} config.palette 颜色列表。
   * @param {string} config.chartType 图表类型。
   * @param {string} config.unit 数据单位（size/change/percent）。
   * @param {Function} config.valueTransform 数值转换函数。
   * @param {Function} [config.dynamicBackground] 自定义背景色生成器。
   * @returns {Array<Object>} Chart.js datasets。
   */
  function buildDatasets({
    labels,
    sortedKeys,
    dateMatrix,
    labelNames,
    palette,
    chartType,
    unit,
    valueTransform,
    dynamicBackground,
  }) {
    const datasets = [];
    sortedKeys.forEach((key, index) => {
      const baseColor = palette[index % palette.length];
      let lastKnownValue = null;
      const data = labels.map((date) => {
        const value = dateMatrix.get(date)?.get(key);
        if (value === null || value === undefined) {
          if (lastKnownValue === null) {
            return null;
          }
          return valueTransform(lastKnownValue);
        }
        lastKnownValue = value;
        return valueTransform(value);
      });

      const dataset = {
        label: labelNames.get(key) || key,
        data,
        borderColor: baseColor,
        backgroundColor: dynamicBackground
          ? dynamicBackground(baseColor)
          : chartType === "line"
          ? colorWithAlpha(baseColor, 0.1)
          : colorWithAlpha(baseColor, 0.65),
        fill: chartType !== "line",
        tension: chartType === "line" ? 0.1 : 0,
      };

      if (unit === "change") {
        dataset.segment = chartType === "line"
          ? {
              borderDash: (ctx) => {
                const prev = ctx.p0?.parsed?.y ?? 0;
                const curr = ctx.p1?.parsed?.y ?? 0;
                const bothPositive = prev >= 0 && curr >= 0;
                return bothPositive ? [] : [6, 4];
              },
            }
          : undefined;
        dataset.backgroundColor = (ctx) => {
          const value = ctx.parsed?.y ?? 0;
          if (chartType === "line") {
            return colorWithAlpha(baseColor, 0.1);
          }
          return value >= 0
            ? colorWithAlpha(baseColor, 0.65)
            : colorWithAlpha(baseColor, 0.35);
        };
      }

      if (unit === "percent") {
        dataset.tension = chartType === "line" ? 0.3 : 0;
        if (chartType === "line") {
          dataset.segment = {
            borderDash: (ctx) => {
              const prev = ctx.p0?.parsed?.y ?? 0;
              const curr = ctx.p1?.parsed?.y ?? 0;
              const bothPositive = prev >= 0 && curr >= 0;
              return bothPositive ? [] : [6, 4];
            },
            borderColor: () => baseColor,
          };
          dataset.pointRadius = (ctx) =>
            Math.abs(ctx.parsed?.y ?? 0) < 0.001 ? 3 : 4;
          dataset.pointHoverRadius = 5;
          dataset.pointBackgroundColor = (ctx) => {
            const value = ctx.parsed?.y ?? 0;
            return value >= 0
              ? colorWithAlpha(baseColor, 0.85)
              : "#ffffff";
          };
          dataset.pointBorderColor = baseColor;
          dataset.pointBorderWidth = (ctx) =>
            (ctx.parsed?.y ?? 0) >= 0 ? 1 : 2;
        } else {
          dataset.borderWidth = 1.5;
          dataset.borderDash = (ctx) =>
            (ctx.parsed?.y ?? 0) >= 0 ? [] : [6, 4];
        }
        dataset.backgroundColor = (ctx) => {
          const value = ctx.parsed?.y ?? 0;
          if (chartType === "line") {
            return colorWithAlpha(baseColor, 0.1);
          }
          return value >= 0
            ? colorWithAlpha(baseColor, 0.65)
            : colorWithAlpha(baseColor, 0.35);
        };
      }

      datasets.push(dataset);
    });
    return datasets;
  }

  /**
   * 构造容量趋势图的数据。
   *
   * @param {Object} options 配置项。
   * @param {Array<Object>} options.items 数据列表。
   * @param {Function|string} options.labelExtractor 标签提取器。
   * @param {number} options.topN 需要展示的前 N 个系列。
   * @param {string} options.chartType chart.js 类型。
   * @returns {{labels: Array<string>, datasets: Array<Object>}} 渲染数据。
   */
  function prepareTrendChartData({ items, labelExtractor, topN, chartType }) {
    const { dateMatrix, labelMaxValue, labelNames } = collectDateMatrix(
      items,
      labelExtractor,
      (item) => normalizeValue(item.total_size_mb ?? item.avg_size_mb)
    );
    const labels = LodashUtils.sortBy(Array.from(dateMatrix.keys()));
    const sortedKeys = LodashUtils.orderBy(
      Array.from(labelMaxValue.entries()),
      [(entry) => entry[1]],
      ["desc"]
    )
      .slice(0, topN)
      .map(([key]) => key);

    const datasets = buildDatasets({
      labels,
      sortedKeys,
      dateMatrix,
      labelNames,
      palette: COLOR_PALETTE,
      chartType,
      unit: "size",
      valueTransform: (value) =>
        value === null ? null : Number(value) / 1024,
    });

    return { labels, datasets };
  }

  /**
   * 构造容量变化（绝对值）图的数据。
   *
   * @param {Object} options 配置项。
   * @param {Array<Object>} options.items 数据列表。
   * @param {Function|string} options.labelExtractor 标签提取器。
   * @param {number} options.topN 渲染的系列数量。
   * @param {string} options.chartType 图表类型。
   * @param {string} options.valueField 备用字段名。
   * @returns {{labels: Array<string>, datasets: Array<Object>}} 渲染数据。
   */
  function prepareChangeChartData({
    items,
    labelExtractor,
    topN,
    chartType,
    valueField,
  }) {
    const { dateMatrix, labelMaxValue, labelNames } = collectDateMatrix(
      items,
      labelExtractor,
      (item) => normalizeValue(item[valueField] ?? item.size_change_mb)
    );
    const labels = LodashUtils.sortBy(Array.from(dateMatrix.keys()));
    const sortedKeys = LodashUtils.orderBy(
      Array.from(labelMaxValue.entries()),
      [(entry) => entry[1]],
      ["desc"]
    )
      .slice(0, topN)
      .map(([key]) => key);

    const datasets = buildDatasets({
      labels,
      sortedKeys,
      dateMatrix,
      labelNames,
      palette: COLOR_PALETTE,
      chartType,
      unit: "change",
      valueTransform: (value) =>
        value === null ? 0 : Number(value) / 1024,
    });

    return { labels, datasets };
  }

  /**
   * 构造容量变化百分比图的数据。
   *
   * @param {Object} options 配置项。
   * @param {Array<Object>} options.items 数据列表。
   * @param {Function|string} options.labelExtractor 标签提取器。
   * @param {number} options.topN 显示的系列数量。
   * @param {string} options.chartType 图表类型。
   * @param {string} options.valueField 使用的字段。
   * @returns {{labels: Array<string>, datasets: Array<Object>}} 渲染数据。
   */
  function prepareChangePercentChartData({
    items,
    labelExtractor,
    topN,
    chartType,
    valueField,
  }) {
    const { dateMatrix, labelMaxValue, labelNames } = collectDateMatrix(
      items,
      labelExtractor,
      (item) => normalizeValue(item[valueField] ?? item.size_change_percent)
    );
    const labels = LodashUtils.sortBy(Array.from(dateMatrix.keys()));
    const sortedKeys = LodashUtils.orderBy(
      Array.from(labelMaxValue.entries()),
      [(entry) => entry[1]],
      ["desc"]
    )
      .slice(0, topN)
      .map(([key]) => key);

    const datasets = buildDatasets({
      labels,
      sortedKeys,
      dateMatrix,
      labelNames,
      palette: COLOR_PALETTE,
      chartType,
      unit: "percent",
      valueTransform: (value) =>
        value === null ? 0 : Number(value),
    });

    return { labels, datasets };
  }

  window.CapacityStatsTransformers = {
    prepareTrendChartData,
    prepareChangeChartData,
    prepareChangePercentChartData,
    colorWithAlpha,
  };
})(window);
