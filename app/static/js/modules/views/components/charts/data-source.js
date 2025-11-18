(function (window) {
  "use strict";

  const CapacityStatsService = window.CapacityStatsService;
  if (!CapacityStatsService) {
    throw new Error("CapacityStatsService 未初始化，无法发起容量统计请求");
  }
  const capacityStatsService = new CapacityStatsService(window.httpU);

  /**
   * 按常见字段尝试提取列表数据。
   */
  function unwrapItems(response) {
    const candidates = [
      response?.data?.items,
      response?.data?.list,
      response?.data?.data,
      response?.data,
      response?.items,
      response?.list,
      response,
    ];

    for (const value of candidates) {
      if (Array.isArray(value)) {
        return value;
      }
      if (value && Array.isArray(value.data)) {
        return value.data;
      }
    }

    return [];
  }

  /**
   * 提取汇总对象，兼容不同返回结构。
   */
  function unwrapSummary(response) {
    return (
      response?.data?.summary ??
      response?.data ??
      response ??
      {}
    );
  }

  /**
   * 拉取汇总数据。
   */
  async function fetchSummary(config, params) {
    const response = await capacityStatsService.get(
      config.summaryEndpoint,
      params,
      config.summaryDefaults
    );
    return unwrapSummary(response);
  }

  /**
   * 拉取趋势数据。
   */
  async function fetchTrend(config, params) {
    const response = await capacityStatsService.get(
      config.trendEndpoint,
      params,
      config.trendDefaults
    );
    return unwrapItems(response);
  }

  /**
   * 拉取变化数据。
   */
  async function fetchChange(config, params) {
    const response = await capacityStatsService.get(
      config.changeEndpoint,
      params,
      config.changeDefaults
    );
    return unwrapItems(response);
  }

  /**
   * 拉取变化百分比数据。
   */
  async function fetchPercentChange(config, params) {
    const response = await capacityStatsService.get(
      config.percentEndpoint,
      params,
      config.percentDefaults
    );
    return unwrapItems(response);
  }

  /**
   * 提交容量即时计算任务。
   */
  async function calculateCurrent(url, payload) {
    await capacityStatsService.post(url, payload || {});
  }

  /**
   * 获取实例下拉数据。
   */
  async function fetchInstances(url, params) {
    const response = await capacityStatsService.get(url, params);
    const instances =
      response?.data?.instances ??
      response?.instances ??
      response?.data ??
      [];
    return Array.isArray(instances) ? instances : [];
  }

  /**
   * 获取数据库下拉数据。
   */
  async function fetchDatabases(url, params) {
    const response = await capacityStatsService.get(url, params);
    const databases =
      response?.data?.databases ??
      response?.databases ??
      response?.data ??
      [];
    return Array.isArray(databases) ? databases : [];
  }

  window.CapacityStatsDataSource = {
    fetchSummary,
    fetchTrend,
    fetchChange,
    fetchPercentChange,
    calculateCurrent,
    fetchInstances,
    fetchDatabases,
  };
})(window);
