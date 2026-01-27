(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/account-change-logs";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("AccountChangeLogsService: httpClient 未初始化");
    }
    return resolved;
  }

  function toQueryString(params) {
    if (!params) {
      return "";
    }
    if (params instanceof URLSearchParams) {
      const serialized = params.toString();
      return serialized ? `?${serialized}` : "";
    }
    if (typeof params === "string") {
      return params ? `?${params.replace(/^\\?/, "")}` : "";
    }
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item !== undefined && item !== null && item !== "") {
            search.append(key, item);
          }
        });
      } else {
        search.append(key, value);
      }
    });
    const serialized = search.toString();
    return serialized ? `?${serialized}` : "";
  }

  class AccountChangeLogsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
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
