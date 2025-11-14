(function (window) {
  "use strict";

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法渲染容量统计图表");
    return;
  }

  const { selectOne } = helpers;

  const DEFAULT_EMPTY_DATASET = {
    label: "暂无数据",
    data: [0],
    backgroundColor: "#f8f9fa",
    borderColor: "#dee2e6",
    borderWidth: 1,
  };

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

  function buildOptions({ title, yLabel, unit, chartType, range }) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: title,
        },
        legend: {
          display: true,
          position: "right",
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
          grid: {
            color: (context) => {
              if (context.tick?.value === 0) {
                return "#212529";
              }
              return "rgba(0, 0, 0, 0.08)";
            },
            lineWidth: (context) => (context.tick?.value === 0 ? 2 : 1),
            borderDash: (context) =>
              context.tick?.value === 0 ? [] : [2, 2],
          },
        },
      },
    };
  }

  function renderChart({
    canvasSelector,
    previousChart,
    chartType,
    chartData,
    options,
    unit,
  }) {
    const canvas =
      typeof canvasSelector === "string"
        ? selectOne(canvasSelector).first()
        : canvasSelector;
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
      return renderEmptyChart(ctx, options?.title);
    }

    const range = unit === "size" ? null : computeRange(chartData.datasets);
    const chartOptions = buildOptions({
      title: options?.title,
      yLabel: options?.yLabel,
      unit,
      chartType,
      range,
    });

    return new window.Chart(ctx, {
      type: chartType,
      data: chartData,
      options: chartOptions,
    });
  }

  function renderTrendChart(config) {
    return renderChart({
      canvasSelector: config.canvas,
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

  function renderChangeChart(config) {
    return renderChart({
      canvasSelector: config.canvas,
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

  function renderChangePercentChart(config) {
    return renderChart({
      canvasSelector: config.canvas,
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
