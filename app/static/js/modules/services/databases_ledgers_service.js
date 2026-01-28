(function (global) {
  "use strict";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("DatabasesLedgersService: ServiceUtils 未初始化");
  }

  const DEFAULT_SYNC_ENDPOINT = "/api/v1/databases/ledgers/actions/sync-all";

  /**
   * 数据库台账 API 封装：同步等动作。
   *
   * @class
   */
  class DatabasesLedgersService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "DatabasesLedgersService", "post");
    }

    syncAllDatabases(options = {}) {
      const customUrl = options?.customUrl;
      const endpoint =
        typeof customUrl === "string" && customUrl.trim()
          ? customUrl.trim()
          : DEFAULT_SYNC_ENDPOINT;
      return this.httpClient.post(endpoint, {});
    }
  }

  global.DatabasesLedgersService = DatabasesLedgersService;
})(window);

