(function (window, document) {
  "use strict";

  function labelExtractor(item) {
    const instanceName =
      item?.instance?.name ||
      item?.instance_name ||
      item?.name ||
      "未知实例";
    const instanceId =
      item?.instance?.id ||
      item?.instance_id ||
      instanceName;
    return {
      key: String(instanceId),
      label: instanceName,
    };
  }

  function initManager() {
    if (!window.CapacityStats || !window.CapacityStats.Manager) {
      setTimeout(initManager, 50);
      return;
    }

    window.instanceCapacityStatsManager = new window.CapacityStats.Manager({
      labelExtractor,
      scope: "instance",
      api: {
        summaryEndpoint: "/instance_aggr/api/instances/aggregations/summary",
        trendEndpoint: "/instance_aggr/api/instances/aggregations",
        changeEndpoint: "/instance_aggr/api/instances/aggregations",
        percentEndpoint: "/instance_aggr/api/instances/aggregations",
        summaryDefaults: {},
        trendDefaults: {
          chart_mode: "instance",
          get_all: "true",
        },
        changeDefaults: {
          get_all: "true",
        },
        percentDefaults: {
          get_all: "true",
        },
        calculateEndpoint: "/aggregations/api/aggregate-current",
        instanceOptionsEndpoint: "/api/instances-options",
      },
      summaryCards: [
        { selector: "#totalInstances", field: "total_instances", formatter: "number" },
        { selector: "#totalDatabases", field: "total_size_mb", formatter: "sizeFromMB" },
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
      window.FilterUtils.registerFilterForm("#instance-aggregations-filter-form", {
        onSubmit: () => window.instanceCapacityStatsManager.applyFilters(),
        onClear: () => window.instanceCapacityStatsManager.resetFilters(),
        autoSubmitOnChange: false,
      });
    }
  }

  document.addEventListener("DOMContentLoaded", initManager);
})(window, document);
