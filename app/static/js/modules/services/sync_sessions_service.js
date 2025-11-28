(function (global) {
  "use strict";

  const BASE_PATH = "/history/sessions/api/sessions";

  /**
   * 统一选择 http 客户端。
   *
   * @param {Object} client - HTTP 客户端实例
   * @return {Object} HTTP 客户端实例
   * @throws {Error} 当客户端未初始化时抛出
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("SyncSessionsService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 将过滤条件转换为查询字符串。
   *
   * @param {Object|URLSearchParams|string} filters - 过滤条件
   * @return {string} 格式化的查询字符串
   */
  function toQueryString(filters) {
    if (!filters) {
      return "";
    }
    if (typeof filters === "string") {
      return filters ? `?${filters.replace(/^\?/, "")}` : "";
    }
    if (filters instanceof URLSearchParams) {
      const serialized = filters.toString();
      return serialized ? `?${serialized}` : "";
    }
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item !== undefined && item !== null && item !== "") {
            params.append(key, item);
          }
        });
      } else {
        params.append(key, value);
      }
    });
    const query = params.toString();
    return query ? `?${query}` : "";
  }

  /**
   * 同步会话服务。
   *
   * 提供同步会话的查询、详情、错误日志和取消操作接口。
   *
   * @class
   */
  class SyncSessionsService {
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
     * 获取同步会话列表。
     *
     * @param {Object} filters - 过滤条件
     * @return {Promise<Object>} 会话列表响应
     */
    list(filters) {
      const query = toQueryString(filters);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }

    /**
     * 获取会话详情。
     *
     * @param {string} sessionId - 会话 ID
     * @return {Promise<Object>} 会话详情响应
     * @throws {Error} 当 sessionId 无效时抛出
     */
    detail(sessionId) {
      this.assertSessionId(sessionId, "detail");
      return this.httpClient.get(`${BASE_PATH}/${sessionId}`);
    }

    /**
     * 获取会话错误日志。
     *
     * @param {string} sessionId - 会话 ID
     * @return {Promise<Object>} 错误日志响应
     * @throws {Error} 当 sessionId 无效时抛出
     */
    errorLogs(sessionId) {
      this.assertSessionId(sessionId, "errorLogs");
      return this.httpClient.get(`${BASE_PATH}/${sessionId}/error-logs`);
    }

    /**
     * 取消会话。
     *
     * @param {string} sessionId - 会话 ID
     * @param {Object} payload - 取消参数
     * @return {Promise<Object>} 取消结果响应
     * @throws {Error} 当 sessionId 无效时抛出
     */
    cancel(sessionId, payload) {
      this.assertSessionId(sessionId, "cancel");
      return this.httpClient.post(`${BASE_PATH}/${sessionId}/cancel`, payload || {});
    }

    /**
     * 验证会话 ID 是否有效。
     *
     * @param {string} sessionId - 会话 ID
     * @param {string} action - 操作名称
     * @throws {Error} 当 sessionId 无效时抛出
     */
    assertSessionId(sessionId, action) {
      if (sessionId === undefined || sessionId === null || sessionId === "") {
        throw new Error(`SyncSessionsService: ${action} 需要有效的 sessionId`);
      }
    }
  }

  global.SyncSessionsService = SyncSessionsService;
})(window);
