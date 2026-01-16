/**
 * 挂载实例容量聚合统计页面。
 *
 * 初始化实例维度的容量统计管理器，配置图表、筛选器和数据端点。
 *
 * @param {Window} window - 全局 window 对象
 * @return {void}
 */
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
   *
   * 从数据项中提取实例名称和 ID，生成唯一键和显示标签。
   *
   * @param {Object} item - 数据项对象
   * @param {Object} [item.instance] - 实例对象
   * @param {string} [item.instance_name] - 实例名称
   * @param {string} [item.name] - 名称
   * @param {number} [item.instance_id] - 实例 ID
   * @return {Object} 包含 key 和 label 的对象
   * @return {string} return.key - 唯一键（实例 ID 字符串）
   * @return {string} return.label - 显示标签（实例名称）
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
   *
   * 创建实例容量统计管理器实例，配置图表选择器、API 端点、
   * 汇总卡片和筛选器。如果 CapacityStats.Manager 未加载，则延迟重试。
   *
   * @param {void} 无参数。依赖全局 CapacityStats。
   * @returns {void}
   */
  function initManager() {
    if (!window.CapacityStats || !window.CapacityStats.Manager) {
      setTimeout(initManager, 50);
      return;
    }

    const apiFactory = window.CapacityStatsService?.buildInstanceApiConfig;
    if (typeof apiFactory !== "function") {
      console.error("CapacityStatsService 未初始化，无法加载容量统计页面");
      return;
    }

    window.instanceCapacityStatsManager = new window.CapacityStats.Manager({
      labelExtractor,
      scope: "instance",
      filterFormId: "#instance-aggregations-filter-form",
      autoApplyOnFilterChange: false,
      api: apiFactory(),
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
