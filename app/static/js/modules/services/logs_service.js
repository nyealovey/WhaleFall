(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/logs";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("LogsService: ServiceUtils 未初始化");
  }

  /**
   * 日志服务。
   *
   * 提供日志查询、统计和详情获取接口。
   *
   * @class
   */
  class LogsService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     */
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "LogsService");
    }

    /**
     * 获取日志模块列表。
     *
     * @return {Promise<Object>} 模块列表响应
     */
    fetchModules() {
      return this.httpClient.get(`${BASE_PATH}/modules`);
    }

    /**
     * 日志列表 Grid 数据源 URL（含默认排序）。
     *
     * @returns {string} API URL
     */
    getGridUrl() {
      const params = new URLSearchParams();
      params.set("sort", "timestamp");
      params.set("order", "desc");
      return `${BASE_PATH}?${params.toString()}`;
    }

    /**
     * 获取日志统计信息。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 统计信息响应
     */
    fetchStats(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}/statistics${query}`);
    }

    /**
     * 搜索日志。
     *
     * @param {Object} params - 搜索参数
     * @return {Promise<Object>} 搜索结果响应
     */
    searchLogs(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }

    /**
     * 获取日志列表。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 日志列表响应
     */
    fetchLogList(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }

    /**
     * 获取日志详情。
     *
     * @param {number} logId - 日志 ID
     * @return {Promise<Object>} 日志详情响应
     * @throws {Error} 当 logId 为空时抛出
     */
    fetchLogDetail(logId) {
      if (!logId && logId !== 0) {
        throw new Error("LogsService: fetchLogDetail 需要 logId");
      }
      return this.httpClient.get(`${BASE_PATH}/${logId}`);
    }
  }

  global.LogsService = LogsService;
})(window);
