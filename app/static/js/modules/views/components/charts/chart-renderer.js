(function (window) {
  "use strict";

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法渲染容量统计图表");
    return;
  }

  const ColorTokens = window.ColorTokens;
  if (!ColorTokens) {
    console.error('ColorTokens 未初始化，无法渲染容量统计图表');
    return;
  }

  const { selectOne } = helpers;

  const contrastColor = ColorTokens.resolveCssVar('--surface-contrast') || 'var(--surface-contrast)';
  const emptyBackground = ColorTokens.getOrangeColor({ tone: 'muted', alpha: 0.2 })
    || ColorTokens.getChartColor(0, 0.2)
    || ColorTokens.getSurfaceColor(0.2)
    || ColorTokens.withAlpha(contrastColor, 0.08)
    || ColorTokens.withAlpha(getComputedStyle(document.documentElement).color, 0.08);
  const emptyBorder = ColorTokens.getOrangeColor({ tone: 'strong' })
    || ColorTokens.withAlpha(contrastColor, 0.2);
  const DEFAULT_EMPTY_DATASET = {
    label: "暂无数据",
    data: [0],
    backgroundColor: emptyBackground,
    borderColor: emptyBorder,
    borderWidth: 1,
  };

  /**
   * 根据数据集估算 y 轴范围，避免曲线贴边。
   *
   * 计算数据集中所有数值的最小值和最大值，并添加 10% 的边距。
   *
   * @param {Array<Object>} datasets - Chart.js 数据集数组
   * @param {Array<number>} datasets[].data - 数据点数组
   * @return {Object|null} 包含 suggestedMin 和 suggestedMax 的对象，无数据时返回 null
   */
  function computeRange(datasets) {
    const values = [];
    (datasets || []).forEach((dataset) => {
      (dataset.data || []).forEach((value) => {
        if (typeof value === "number" && !Number.isNaN(value)) {
          values.push(value);
        }
      });
    });
    if (!values.length) {
      return null;
    }
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 0);
    if (min === 0 && max === 0) {
      return { suggestedMin: -1, suggestedMax: 1 };
    }
    const padding = Math.max((max - min) * 0.1, 1);
    return {
      suggestedMin: Math.min(min - padding, 0),
      suggestedMax: Math.max(max + padding, 0),
    };
  }

  /**
   * 当没有数据时渲染提示占位图表。
   *
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D 上下文
   * @param {string} title - 图表标题
   * @return {Chart} Chart.js 实例
   */
  function renderEmptyChart(ctx, title) {
    return new window.Chart(ctx, {
      type: "bar",
      data: {
        labels: ["暂无数据"],
        datasets: [DEFAULT_EMPTY_DATASET],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: `${title || "数据"} - 暂无数据`,
          },
          legend: {
            display: false,
          },
        },
      },
    });
  }

  /**
   * 统一解析 selector / element。
   *
   * @param {string|Element} target 选择器或 DOM 元素。
   * @return {Element|null} 命中的元素或 null。
   */
  function resolveElement(target) {
    if (!target) {
      return null;
    }
    if (typeof target === "string") {
      return selectOne(target).first() || null;
    }
    return target instanceof Element ? target : null;
  }

  /**
   * 解析 dataset 用于图例色标的主色。
   *
   * @param {Object} dataset Chart.js dataset。
   * @return {string} 图例色标颜色。
   */
  function resolveLegendColor(dataset) {
    const borderColor = dataset?.borderColor;
    if (Array.isArray(borderColor)) {
      return borderColor[0] || emptyBorder;
    }
    if (typeof borderColor === "string" && borderColor) {
      return borderColor;
    }

    const backgroundColor = dataset?.backgroundColor;
    if (Array.isArray(backgroundColor)) {
      return backgroundColor[0] || emptyBorder;
    }
    if (typeof backgroundColor === "string" && backgroundColor) {
      return backgroundColor;
    }

    return emptyBorder;
  }

  /**
   * 渲染外部单列图例。
   *
   * @param {string|Element} legendContainer 图例容器。
   * @param {Chart|null} chart 图表实例。
   * @return {void}
   */
  function renderExternalLegend(legendContainer, chart) {
    const container = resolveElement(legendContainer);
    if (!container) {
      return;
    }

    container.replaceChildren();

    const datasets = chart?.data?.datasets;
    if (!Array.isArray(datasets) || !datasets.length || datasets[0]?.label === DEFAULT_EMPTY_DATASET.label) {
      container.hidden = true;
      container.dataset.empty = "true";
      return;
    }

    const fragment = document.createDocumentFragment();
    datasets.forEach((dataset) => {
      const item = document.createElement("div");
      item.className = "capacity-chart-legend__item";

      const swatch = document.createElement("span");
      swatch.className = "capacity-chart-legend__swatch";
      const color = resolveLegendColor(dataset);
      swatch.style.setProperty("--legend-color", color);

      const label = document.createElement("span");
      label.className = "capacity-chart-legend__label";
      label.textContent = dataset?.label || "未命名系列";

      item.appendChild(swatch);
      item.appendChild(label);
      fragment.appendChild(item);
    });

    container.appendChild(fragment);
    container.hidden = false;
    container.dataset.empty = "false";
  }

  /**
   * 构造 Chart.js 配置，支持不同单位与类型。
   *
   * @param {Object} config - 配置对象
   * @param {string} config.title - 图表标题
   * @param {string} config.yLabel - Y 轴标签
   * @param {string} config.unit - 数据单位：'size'、'change'、'percent'
   * @param {Object} [config.range] - Y 轴范围配置
   * @param {number} [config.range.suggestedMin] - 建议最小值
   * @param {number} [config.range.suggestedMax] - 建议最大值
   * @return {Object} Chart.js 配置对象
   */
  function buildOptions({ title, yLabel, unit, range }) {
    const contrast = ColorTokens.resolveCssVar('--surface-contrast') || 'var(--surface-contrast)';
    const gridColor = ColorTokens.withAlpha(contrast, 0.08);
    return {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: {
          top: 18,
          right: 8,
          bottom: 24,
          left: 6,
        },
      },
      plugins: {
        title: {
          display: true,
          text: title,
          padding: {
            bottom: 18,
          },
        },
        legend: {
          display: false,
        },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: {
            label(context) {
              const label = context.dataset?.label || "";
              const value = context.parsed?.y;
              if (value === null || value === undefined || Number.isNaN(value)) {
                return `${label}: 无数据`;
              }
              switch (unit) {
                case "size": {
                  const formatted = window.NumberFormat.formatPlain(
                    value,
                    "0,0.00",
                    "0",
                  );
                  return `${label}: ${formatted} GB`;
                }
                case "change": {
                  const formatted = window.NumberFormat.formatPlain(
                    value,
                    "+0,0.00",
                    "0",
                  );
                  return `${label}: ${formatted} GB`;
                }
                case "percent":
                  return `${label}: ${window.NumberFormat.formatPercent(value, {
                    precision: 2,
                    showSign: true,
                  })}`;
                default: {
                  const fallback = window.NumberFormat.formatPlain(value, "0,0.[00]", "0");
                  return `${label}: ${fallback}`;
                }
              }
            },
          },
        },
      },
      interaction: {
        mode: "nearest",
        axis: "x",
        intersect: false,
      },
      scales: {
        x: {
          display: true,
          title: {
            display: true,
            text: "时间",
          },
          ticks: {
            padding: 10,
          },
        },
        y: {
          display: true,
          title: {
            display: true,
            text: yLabel,
          },
          suggestedMin: range?.suggestedMin,
          suggestedMax: range?.suggestedMax,
          beginAtZero: unit === "size",
          grace: unit === "size" ? "4%" : "8%",
          ticks: {
            padding: 8,
          },
          grid: {
            color: (context) => {
              if (context.tick?.value === 0) {
                return contrast;
              }
              return gridColor;
            },
            lineWidth: (context) => (context.tick?.value === 0 ? 2 : 1),
            borderDash: (context) =>
              context.tick?.value === 0 ? [] : [2, 2],
          },
        },
      },
    };
  }

  /**
   * 通用图表渲染入口，负责销毁旧实例与渲染新图。
   *
   * @param {Object} config - 渲染配置
   * @param {string|HTMLCanvasElement} config.canvasSelector - Canvas 选择器或元素
   * @param {Chart} [config.previousChart] - 之前的图表实例，用于销毁
   * @param {string} config.chartType - 图表类型：'line'、'bar'
   * @param {Object} config.chartData - Chart.js 数据对象
   * @param {Array<string>} config.chartData.labels - 标签数组
   * @param {Array<Object>} config.chartData.datasets - 数据集数组
   * @param {Object} config.options - 图表选项
   * @param {string} config.options.title - 图表标题
   * @param {string} config.options.yLabel - Y 轴标签
   * @param {string} config.unit - 数据单位：'size'、'change'、'percent'
   * @return {Chart|null} Chart.js 实例，失败时返回 null
   */
  function renderChart({
    canvasSelector,
    legendContainer,
    previousChart,
    chartType,
    chartData,
    options,
    unit,
  }) {
    const canvas = resolveElement(canvasSelector);
    if (!canvas) {
      return previousChart || null;
    }

    const ctx = canvas.getContext("2d");
    if (previousChart) {
      previousChart.destroy();
    }

    const hasData =
      chartData &&
      Array.isArray(chartData.labels) &&
      chartData.labels.length > 0 &&
      Array.isArray(chartData.datasets) &&
      chartData.datasets.length > 0;

    if (!hasData) {
      renderExternalLegend(legendContainer, null);
      return renderEmptyChart(ctx, options?.title);
    }

    const range = unit === "size" ? null : computeRange(chartData.datasets);
    const chartOptions = buildOptions({
      title: options?.title,
      yLabel: options?.yLabel,
      unit,
      range,
    });

    const instance = new window.Chart(ctx, {
      type: chartType,
      data: chartData,
      options: chartOptions,
    });
    renderExternalLegend(legendContainer, instance);
    return instance;
  }

  /**
   * 渲染容量趋势图表。
   *
   * @param {Object} config - 配置对象
   * @param {string|HTMLCanvasElement} config.canvas - Canvas 选择器或元素
   * @param {Chart} [config.instance] - 之前的图表实例
   * @param {string} config.type - 图表类型：'line'、'bar'
   * @param {Object} config.data - Chart.js 数据对象
   * @param {string} [config.title] - 图表标题
   * @param {string} [config.yLabel] - Y 轴标签
   * @return {Chart} Chart.js 实例
   */
  function renderTrendChart(config) {
    return renderChart({
      canvasSelector: config.canvas,
      legendContainer: config.legendContainer,
      previousChart: config.instance,
      chartType: config.type,
      chartData: config.data,
      options: {
        title: config.title || "容量统计趋势图",
        yLabel: config.yLabel || "大小 (GB)",
      },
      unit: "size",
    });
  }

  /**
   * 渲染容量变化图表。
   *
   * @param {Object} config - 配置对象
   * @param {string|HTMLCanvasElement} config.canvas - Canvas 选择器或元素
   * @param {Chart} [config.instance] - 之前的图表实例
   * @param {string} config.type - 图表类型：'line'、'bar'
   * @param {Object} config.data - Chart.js 数据对象
   * @param {string} [config.title] - 图表标题
   * @param {string} [config.yLabel] - Y 轴标签
   * @return {Chart} Chart.js 实例
   */
  function renderChangeChart(config) {
    return renderChart({
      canvasSelector: config.canvas,
      legendContainer: config.legendContainer,
      previousChart: config.instance,
      chartType: config.type,
      chartData: config.data,
      options: {
        title: config.title || "容量变化趋势图",
        yLabel: config.yLabel || "变化量 (GB)",
      },
      unit: "change",
    });
  }

  /**
   * 渲染容量变化百分比图表。
   *
   * @param {Object} config - 配置对象
   * @param {string|HTMLCanvasElement} config.canvas - Canvas 选择器或元素
   * @param {Chart} [config.instance] - 之前的图表实例
   * @param {string} config.type - 图表类型：'line'、'bar'
   * @param {Object} config.data - Chart.js 数据对象
   * @param {string} [config.title] - 图表标题
   * @param {string} [config.yLabel] - Y 轴标签
   * @return {Chart} Chart.js 实例
   */
  function renderChangePercentChart(config) {
    return renderChart({
      canvasSelector: config.canvas,
      legendContainer: config.legendContainer,
      previousChart: config.instance,
      chartType: config.type,
      chartData: config.data,
      options: {
        title: config.title || "容量变化趋势图 (百分比)",
        yLabel: config.yLabel || "变化率 (%)",
      },
      unit: "percent",
    });
  }

  window.CapacityStatsChartRenderer = {
    renderTrendChart,
    renderChangeChart,
    renderChangePercentChart,
  };
})(window);
