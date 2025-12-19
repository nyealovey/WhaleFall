(function (window) {
  "use strict";

  const CapacityStatsService = window.CapacityStatsService;
  if (!CapacityStatsService) {
    throw new Error("CapacityStatsService 未初始化，无法发起容量统计请求");
  }
  const capacityStatsService = new CapacityStatsService(window.httpU);

  /**
   * 确保响应包含 data 对象。
   *
   * @param {Object} response - API 响应对象
   * @param {string} errorMessage - 缺失 data 时的错误提示
   * @returns {Object} data 对象
   * @throws {Error} 当 data 缺失或格式不合法时抛出
   */
  function ensureDataObject(response, errorMessage) {
    const payload = response?.data;
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      throw new Error(errorMessage || "容量接口响应缺少 data");
    }
    return payload;
  }

  /**
   * 提取汇总对象（严格要求 data.summary）。
   *
   * @param {Object} response - API 响应对象
   * @return {Object} 汇总数据对象
   * @throws {Error} 当 summary 缺失或格式错误时抛出
   */
  function extractSummary(response) {
    const payload = ensureDataObject(response, "容量汇总响应缺少 data");
    const summary = payload.summary;
    if (!summary || typeof summary !== "object" || Array.isArray(summary)) {
      throw new Error("容量汇总响应缺少 summary 对象");
    }
    return summary;
  }

  /**
   * 提取列表数据（严格要求 data.items）。
   *
   * @param {Object} response - API 响应对象
   * @returns {Array} 数据数组
   * @throws {Error} 当 items 缺失或非数组时抛出
   */
  function extractItems(response) {
    const payload = ensureDataObject(response, "容量数据响应缺少 data");
    const items = Array.isArray(payload.items) ? payload.items : payload.data;
    if (!Array.isArray(items)) {
      throw new Error("容量数据响应缺少 items 数组");
    }
    return items;
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
    return extractSummary(response);
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
    return extractItems(response);
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
    return extractItems(response);
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
    return extractItems(response);
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
    const payload = ensureDataObject(response, "实例选项响应缺少 data");
    if (!Array.isArray(payload.instances)) {
      throw new Error("实例选项响应缺少 instances 数组");
    }
    return payload.instances;
  }

  /**
   * 获取数据库下拉数据。
   */
  async function fetchDatabases(url, params) {
    const response = await capacityStatsService.get(url, params);
    const payload = ensureDataObject(response, "数据库选项响应缺少 data");
    if (!Array.isArray(payload.databases)) {
      throw new Error("数据库选项响应缺少 databases 数组");
    }
    return payload.databases;
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
