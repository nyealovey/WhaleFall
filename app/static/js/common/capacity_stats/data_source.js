(function (window) {
  "use strict";

  const CapacityStatsService = window.CapacityStatsService;
  if (!CapacityStatsService) {
    throw new Error("CapacityStatsService 未初始化，无法发起容量统计请求");
  }
  const capacityStatsService = new CapacityStatsService(window.httpU);

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

  function unwrapSummary(response) {
    return (
      response?.data?.summary ??
      response?.data ??
      response ??
      {}
    );
  }

  async function fetchSummary(config, params) {
    const response = await capacityStatsService.get(
      config.summaryEndpoint,
      params,
      config.summaryDefaults
    );
    return unwrapSummary(response);
  }

  async function fetchTrend(config, params) {
    const response = await capacityStatsService.get(
      config.trendEndpoint,
      params,
      config.trendDefaults
    );
    return unwrapItems(response);
  }

  async function fetchChange(config, params) {
    const response = await capacityStatsService.get(
      config.changeEndpoint,
      params,
      config.changeDefaults
    );
    return unwrapItems(response);
  }

  async function fetchPercentChange(config, params) {
    const response = await capacityStatsService.get(
      config.percentEndpoint,
      params,
      config.percentDefaults
    );
    return unwrapItems(response);
  }

  async function calculateCurrent(url, payload) {
    await capacityStatsService.post(url, payload || {});
  }

  async function fetchInstances(url, params) {
    const response = await capacityStatsService.get(url, params);
    const instances =
      response?.data?.instances ??
      response?.instances ??
      response?.data ??
      [];
    return Array.isArray(instances) ? instances : [];
  }

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
