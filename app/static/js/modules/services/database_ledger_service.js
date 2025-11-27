(function (global) {
  "use strict";

  /**
   * 确保 HTTP 客户端可用。
   *
    * @param {Object} client - HTTP 客户端实例
   * @returns {Object} 已验证的 HTTP 客户端
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("DatabaseLedgerService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 构建查询字符串。
   *
   * @param {Object|URLSearchParams|string} params 查询对象
   * @returns {string} 查询字符串（含 ?）
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
        return;
      }
      search.append(key, value);
    });
    const serialized = search.toString();
    return serialized ? `?${serialized}` : "";
  }

  /**
   * 数据库台账 API 封装。
   *
   * @class
   */
  class DatabaseLedgerService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    fetchLedger(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`/databases/api/ledger${query}`);
    }

    fetchCapacityTrend(databaseId, params) {
      if (!databaseId && databaseId !== 0) {
        throw new Error("DatabaseLedgerService: fetchCapacityTrend 需要 databaseId");
      }
      const query = toQueryString(params);
      return this.httpClient.get(
        `/databases/api/ledger/${databaseId}/capacity-trend${query}`,
      );
    }
  }

  global.DatabaseLedgerService = DatabaseLedgerService;
})(window);
