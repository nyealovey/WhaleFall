(function (global) {
  "use strict";

  const BASE_PATH = "/logs/api";

  /**
   * 统一选择 http 客户端。
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("LogsService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 构造查询字符串。
   */
  function toQueryString(params) {
    if (!params) {
      return "";
    }
    if (params instanceof URLSearchParams) {
      const serialized = params.toString();
      return serialized ? `?${serialized}` : "";
    }
    if (typeof params === "string") {
      return params ? `?${params.replace(/^\?/, "")}` : "";
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

  /**
   * 日志模块 API 封装。
   */
  class LogsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    fetchModules() {
      return this.httpClient.get(`${BASE_PATH}/modules`);
    }

    fetchStats(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}/stats${query}`);
    }

    searchLogs(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}/search${query}`);
    }

    fetchLogDetail(logId) {
      if (!logId && logId !== 0) {
        throw new Error("LogsService: fetchLogDetail 需要 logId");
      }
      return this.httpClient.get(`${BASE_PATH}/detail/${logId}`);
    }
  }

  global.LogsService = LogsService;
})(window);
