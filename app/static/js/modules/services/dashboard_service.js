(function (global) {
  "use strict";

  /**
   * 统一选择 http 客户端。
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("DashboardService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 仪表盘数据服务。
   */
  class DashboardService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    fetchCharts(params) {
      const query = params ? `?${new URLSearchParams(params).toString()}` : "";
      return this.httpClient.get(`/dashboard/api/charts${query}`);
    }
  }

  global.DashboardService = DashboardService;
})(window);
