(function (global) {
  "use strict";

  const BASE_PATH = "/partition/api";

  /**
   * 统一选择 httpU 客户端。
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("PartitionService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 构造 query string。
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
      search.append(key, value);
    });
    const serialized = search.toString();
    return serialized ? `?${serialized}` : "";
  }

  /**
   * 分区管理服务，包含创建/清理/核心指标等接口。
   */
  class PartitionService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    fetchInfo() {
      return this.httpClient.get(`${BASE_PATH}/info`);
    }

    createPartition(payload) {
      return this.httpClient.post(`${BASE_PATH}/create`, payload || {});
    }

    cleanupPartitions(payload) {
      return this.httpClient.post(`${BASE_PATH}/cleanup`, payload || {});
    }

    fetchCoreMetrics(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`/partition/api/aggregations/core-metrics${query}`);
    }
  }

  global.PartitionService = PartitionService;
})(window);
