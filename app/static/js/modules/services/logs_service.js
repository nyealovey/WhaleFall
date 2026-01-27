(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/logs";

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
      throw new Error("LogsService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 构造查询字符串。
   *
   * @param {Object|URLSearchParams|string} params - 查询参数
   * @return {string} 格式化的查询字符串
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
      this.httpClient = ensureHttpClient(httpClient);
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
