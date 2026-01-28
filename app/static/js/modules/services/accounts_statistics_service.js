(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/accounts/statistics";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("AccountsStatisticsService: ServiceUtils 未初始化");
  }

  /**
   * 账户统计服务。
   *
   * 提供账户统计刷新与查询接口。
   *
   * @class
   */
  class AccountsStatisticsService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     */
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "AccountsStatisticsService");
    }

    fetchStatistics() {
      return this.httpClient.get(BASE_PATH, {
        headers: { Accept: "application/json" },
      });
    }
  }

  global.AccountsStatisticsService = AccountsStatisticsService;
})(window);
