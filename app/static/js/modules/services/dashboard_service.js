(function (global) {
  "use strict";

  /**
   * 统一选择 http 客户端。
   *
   * @param {Object} client - HTTP 客户端实例
   * @return {Object} HTTP 客户端实例
   * @throws {Error} 当客户端未初始化时抛出
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("DashboardService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 仪表盘数据服务。
   *
   * 提供仪表盘图表数据查询接口。
   *
   * @class
   */
  class DashboardService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     */
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    /**
     * 获取仪表盘图表数据。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 图表数据响应
     */
    fetchCharts(params) {
      const query = params ? `?${new URLSearchParams(params).toString()}` : "";
      return this.httpClient.get(`/api/v1/dashboard/charts${query}`);
    }
  }

  global.DashboardService = DashboardService;
})(window);
