(function (window, document) {
  "use strict";

  function labelExtractor(item) {
    const databaseName =
      item?.database_name ||
      item?.database?.database_name ||
      "未知数据库";
    const instanceName =
      item?.instance?.name ||
      item?.instance_name ||
      "未知实例";
    const instanceId =
      item?.instance?.id ||
      item?.instance_id ||
      `unknown-${instanceName}`;
    const key = `${instanceId}::${databaseName}`;
    return {
      key,
      label: `${databaseName} (${instanceName})`,
    };
  }

  function initManager() {
    if (!window.CapacityStats || !window.CapacityStats.Manager) {
      setTimeout(initManager, 50);
      return;
    }

    window.databaseCapacityStatsManager = new window.CapacityStats.Manager({
      labelExtractor,
      supportsDatabaseFilter: true,
      includeDatabaseName: true,
      scope: "database",
      selectors: {
        charts: {
          trend: "#databaseChart",
          change: "#databaseChangeChart",
          percent: "#databaseChangePercentChart",
        },
        loaders: {
          trend: "#chartLoading",
          change: "#changeChartLoading",
          percent: "#changePercentChartLoading",
        },
      },
      api: {
        summaryEndpoint: "/database_aggr/api/databases/aggregations/summary",
        trendEndpoint: "/database_aggr/api/databases/aggregations",
        changeEndpoint: "/database_aggr/api/databases/aggregations",
        percentEndpoint: "/database_aggr/api/databases/aggregations",
        summaryDefaults: {
          api: "true",
        },
        trendDefaults: {
          api: "true",
          chart_mode: "database",
          get_all: "true",
        },
        changeDefaults: {
          api: "true",
          chart_mode: "database",
          get_all: "true",
        },
        percentDefaults: {
          api: "true",
          chart_mode: "database",
          get_all: "true",
        },
        calculateEndpoint: "/aggregations/api/aggregate-current",
        instanceOptionsEndpoint: "/api/instances-options",
        databaseOptionsEndpoint: "/api/databases-options",
      },
      fields: {
        change: "size_change_mb",
        percent: "size_change_percent",
      },
      summaryCards: [
        { selector: "#totalDatabases", field: "total_databases", formatter: "number" },
        { selector: "#totalCapacity", field: "total_size_mb", formatter: "sizeFromMB" },
        { selector: "#averageSize", field: "avg_size_mb", formatter: "sizeFromMB" },
        { selector: "#maxSize", field: "max_size_mb", formatter: "sizeFromMB" },
      ],
      chartTitles: {
        trend: "容量统计趋势图",
        change: "容量变化趋势图",
        percent: "容量变化趋势图 (百分比)",
      },
      axisLabels: {
        trend: "大小 (GB)",
        change: "变化量 (GB)",
        percent: "变化率 (%)",
      },
    });

    if (window.FilterUtils) {
      window.FilterUtils.registerFilterForm("#database-aggregations-filter-form", {
        onSubmit: () => window.databaseCapacityStatsManager.applyFilters(),
        onClear: () => window.databaseCapacityStatsManager.resetFilters(),
        autoSubmitOnChange: false,
      });
    }
  }

  document.addEventListener("DOMContentLoaded", initManager);
})(window, document);
