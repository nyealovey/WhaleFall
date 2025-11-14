(function (global) {
  "use strict";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("DashboardService: httpClient 未初始化");
    }
    return resolved;
  }

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

