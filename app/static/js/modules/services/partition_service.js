(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/partitions";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("PartitionService: ServiceUtils 未初始化");
  }

  /**
   * 分区管理服务。
   *
   * 提供分区信息查询、创建、清理和核心指标获取等接口。
   *
   * @class
   */
  class PartitionService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     */
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "PartitionService");
    }

    /**
     * 获取分区信息。
     *
     * @return {Promise<Object>} 分区信息响应
     */
    fetchInfo() {
      return this.httpClient.get(`${BASE_PATH}/info`);
    }

    /**
     * 分区列表 Grid 数据源 URL（含默认排序）。
     *
     * @returns {string} API URL
     */
    getGridUrl() {
      const params = new URLSearchParams();
      params.set("sort", "name");
      params.set("order", "asc");
      return `${BASE_PATH}?${params.toString()}`;
    }

    /**
     * 创建分区。
     *
     * @param {Object} payload - 创建参数
     * @param {string} payload.date - 分区日期
     * @return {Promise<Object>} 创建结果响应
     */
    createPartition(payload) {
      return this.httpClient.post(`${BASE_PATH}`, payload || {});
    }

    /**
     * 清理旧分区。
     *
     * @param {Object} payload - 清理参数
     * @param {number} payload.retention_months - 保留月数
     * @return {Promise<Object>} 清理结果响应
     */
    cleanupPartitions(payload) {
      return this.httpClient.post(`${BASE_PATH}/actions/cleanup`, payload || {});
    }

    /**
     * 获取核心指标数据。
     *
     * @param {Object} params - 查询参数
     * @param {string} [params.period_type] - 统计周期类型
     * @param {number} [params.days] - 天数
     * @return {Promise<Object>} 指标数据响应
     */
    fetchCoreMetrics(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}/core-metrics${query}`);
    }

    /**
     * 获取分区列表。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 分区列表响应
     */
    fetchPartitions(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }

    fetchHealthStatus() {
      return this.httpClient.get("/api/v1/health");
    }
  }

  global.PartitionService = PartitionService;
})(window);
