function mountInstanceAggregationsPage(window) {
  "use strict";

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法加载实例容量统计页面");
    return;
  }

  const { ready } = helpers;

  /**
   * 统一从接口数据解析实例标签/键。
   */
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

  /**
   * 懒加载 CapacityStats.Manager 并初始化配置。
   */
  function initManager() {
    if (!window.CapacityStats || !window.CapacityStats.Manager) {
      setTimeout(initManager, 50);
      return;
    }

    window.instanceCapacityStatsManager = new window.CapacityStats.Manager({
      labelExtractor,
      scope: "instance",
      filterFormId: "#instance-aggregations-filter-form",
      autoApplyOnFilterChange: false,
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
        instanceOptionsEndpoint: "/common/api/instances-options",
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

    const filterCardFactory = window.UI?.createFilterCard;
    if (filterCardFactory) {
      filterCardFactory({
        formSelector: "#instance-aggregations-filter-form",
        autoSubmitOnChange: false,
        onSubmit: ({ event }) => event?.preventDefault?.(),
        onClear: ({ event }) => event?.preventDefault?.(),
      });
    }
  }

  ready(initManager);
}

window.InstanceAggregationsPage = {
  mount: () => mountInstanceAggregationsPage(window),
};
