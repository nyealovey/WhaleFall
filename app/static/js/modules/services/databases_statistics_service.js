(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/databases/statistics";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("DatabasesStatisticsService: ServiceUtils 未初始化");
  }

  class DatabasesStatisticsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "DatabasesStatisticsService");
    }

    fetchStatistics() {
      return this.httpClient.get(BASE_PATH, {
        headers: { Accept: "application/json" },
      });
    }
  }

  global.DatabasesStatisticsService = DatabasesStatisticsService;
})(window);
