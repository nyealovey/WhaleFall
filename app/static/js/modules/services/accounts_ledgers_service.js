(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/accounts/ledgers";
  const EXPORT_PATH = "/api/v1/accounts/ledgers/exports";

  class AccountsLedgersService {
    constructor(httpClient) {
      const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
      this.httpClient = typeof ensureHttpClient === "function" ? ensureHttpClient(httpClient, "AccountsLedgersService") : null;
    }

    /**
     * 账户台账列表的 Grid 数据源 URL（含默认排序）。
     *
     * @returns {string} API URL
     */
    getGridUrl() {
      const params = new URLSearchParams();
      params.set("sort", "username");
      params.set("order", "asc");
      return `${BASE_PATH}?${params.toString()}`;
    }

    /**
     * 账户台账导出 CSV 的 endpoint。
     *
     * @returns {string} API endpoint
     */
    getExportUrl() {
      return EXPORT_PATH;
    }

    list(params) {
      if (!this.httpClient) {
        throw new Error("AccountsLedgersService: httpClient 未初始化");
      }
      return this.httpClient.get(BASE_PATH, { params: params || {} });
    }
  }

  global.AccountsLedgersService = AccountsLedgersService;
})(window);
