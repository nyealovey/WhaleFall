(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/accounts/statistics";

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
      throw new Error("AccountsStatisticsService: httpClient 未初始化");
    }
    return resolved;
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
      this.httpClient = ensureHttpClient(httpClient);
    }

    fetchStatistics() {
      return this.httpClient.get(BASE_PATH, {
        headers: { Accept: "application/json" },
      });
    }
  }

  global.AccountsStatisticsService = AccountsStatisticsService;
})(window);
