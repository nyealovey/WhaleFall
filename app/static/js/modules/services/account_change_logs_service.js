(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/account-change-logs";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("AccountChangeLogsService: ServiceUtils 未初始化");
  }

  class AccountChangeLogsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "AccountChangeLogsService");
    }

    getGridUrl() {
      const params = new URLSearchParams();
      params.set("sort", "change_time");
      params.set("order", "desc");
      return `${BASE_PATH}?${params.toString()}`;
    }

    fetchStats(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}/statistics${query}`);
    }

    fetchChangeLogs(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }

    fetchDetail(logId) {
      if (!logId && logId !== 0) {
        throw new Error("AccountChangeLogsService: fetchDetail 需要 logId");
      }
      return this.httpClient.get(`${BASE_PATH}/${logId}`);
    }
  }

  global.AccountChangeLogsService = AccountChangeLogsService;
})(window);
