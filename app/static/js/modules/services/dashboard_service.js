  (function (global) {
    "use strict";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("DashboardService: ServiceUtils 未初始化");
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
      this.httpClient = ensureHttpClient(httpClient, "DashboardService");
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
