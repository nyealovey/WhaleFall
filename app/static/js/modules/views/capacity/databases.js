/**
 * 挂载数据库容量聚合统计页面。
 *
 * 初始化数据库维度的容量统计管理器，配置图表、筛选器和数据端点。
 *
 * @param {Window} window - 全局 window 对象
 * @return {void}
 */
function mountCapacityDatabasesPage(window) {
  "use strict";

  const helpers = window.DOMHelpers;
  if (!helpers) {
    console.error("DOMHelpers 未初始化，无法加载数据库容量统计页面");
    return;
  }

  const { ready } = helpers;

  /**
   * 解析数据库标签，输出 key/label。
   *
   * 从数据项中提取数据库名称和实例名称，生成唯一键和显示标签。
   *
   * @param {Object} item - 数据项对象
   * @param {string} [item.database_name] - 数据库名称
   * @param {Object} [item.database] - 数据库对象
   * @param {Object} [item.instance] - 实例对象
   * @param {string} [item.instance_name] - 实例名称
   * @return {Object} 包含 key 和 label 的对象
   * @return {string} return.key - 唯一键，格式为 'instanceId::databaseName'
   * @return {string} return.label - 显示标签，格式为 'databaseName (instanceName)'
   */
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

  /**
   * 初始化 CapacityStats.Manager（数据库维度）。
   *
   * 创建数据库容量统计管理器实例，配置图表选择器、API 端点、
   * 汇总卡片和筛选器。如果 CapacityStats.Manager 未加载，则延迟重试。
   *
   * @param {void} 无参数。函数依赖全局 CapacityStats。
   * @returns {void}
   */
  function initManager() {
    if (!window.CapacityStats || !window.CapacityStats.Manager) {
      setTimeout(initManager, 50);
      return;
    }

    const apiFactory = window.CapacityStatsService?.buildDatabaseApiConfig;
    if (typeof apiFactory !== "function") {
      console.error("CapacityStatsService 未初始化，无法加载容量统计页面");
      return;
    }

    window.databaseCapacityStatsManager = new window.CapacityStats.Manager({
      labelExtractor,
      supportsDatabaseFilter: true,
      includeDatabaseName: true,
      scope: "database",
      filterFormId: "#database-aggregations-filter-form",
      autoApplyOnFilterChange: false,
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
      api: apiFactory(),
      fields: {
        change: "size_change_mb",
        percent: "size_change_percent",
      },
      summaryCards: [
        {
          selector: "#totalDatabases",
          field: "total_databases",
          formatter: "number",
          meta: [
            { selector: "#capDbMetaInstances", field: "total_instances", formatter: "number" },
            {
              selector: "#capDbMetaDbPerInstance",
              resolve: (summary) => {
                const total = Number(summary?.total_databases ?? 0) || 0;
                const instances = Number(summary?.total_instances ?? 0) || 0;
                return instances > 0 ? total / instances : 0;
              },
              formatter: (value) =>
                window.NumberFormat.formatDecimal(value, { precision: 1, trimZero: true, fallback: "0" }),
            },
          ],
        },
        {
          selector: "#totalCapacity",
          field: "total_size_mb",
          formatter: "sizeFromMB",
          meta: [
            {
              selector: "#capDbMetaGrowthRate",
              field: "growth_rate",
              formatter: (value) =>
                window.NumberFormat.formatPercent(value, { precision: 1, trimZero: true, inputType: "percent", fallback: "0%" }),
            },
          ],
        },
        {
          selector: "#averageSize",
          field: "avg_size_mb",
          formatter: "sizeFromMB",
          meta: [
            {
              selector: "#capDbMetaMaxToAvg",
              resolve: (summary) => {
                const max = Number(summary?.max_size_mb ?? 0) || 0;
                const avg = Number(summary?.avg_size_mb ?? 0) || 0;
                return avg > 0 ? max / avg : 0;
              },
              formatter: (value) =>
                `${window.NumberFormat.formatDecimal(value, { precision: 1, trimZero: true, fallback: "0" })}x`,
            },
          ],
        },
        {
          selector: "#maxSize",
          field: "max_size_mb",
          formatter: "sizeFromMB",
          meta: [
            {
              selector: "#capDbMetaLargestShare",
              resolve: (summary) => {
                const max = Number(summary?.max_size_mb ?? 0) || 0;
                const total = Number(summary?.total_size_mb ?? 0) || 0;
                return total > 0 ? max / total : 0;
              },
              formatter: (value) =>
                window.NumberFormat.formatPercent(value, { precision: 1, trimZero: true, inputType: "ratio", fallback: "0%" }),
            },
          ],
        },
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
        formSelector: "#database-aggregations-filter-form",
        autoSubmitOnChange: false,
        onSubmit: ({ event }) => event?.preventDefault?.(),
        onClear: ({ event }) => event?.preventDefault?.(),
      });
    }
  }

  ready(initManager);
}

window.CapacityDatabasesPage = {
  mount: () => mountCapacityDatabasesPage(window),
};
