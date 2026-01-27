(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/instances";

  /**
   * 确保 http 客户端存在。
   *
   * @param {Object} client - HTTP 客户端实例
   * @return {Object} HTTP 客户端实例
   * @throws {Error} 当客户端未初始化时抛出
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("ConnectionService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 连接测试服务。
   *
   * 提供数据库连接测试、参数验证和状态查询接口。
   *
   * @class
   */
  class ConnectionService {
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
     * 测试实例连接。
     *
     * @param {number|string} instanceId - 实例 ID
     * @param {Object} [options] - 可选的测试参数
     * @return {Promise<Object>} 测试结果响应
     * @throws {Error} 当 instanceId 无效时抛出
     */
    testInstanceConnection(instanceId, options) {
      if (instanceId === undefined || instanceId === null || instanceId === "") {
        throw new Error("ConnectionService: testInstanceConnection 需要 instanceId");
      }
      return this.httpClient.post(`${BASE_PATH}/actions/test-connection`, {
        instance_id: instanceId,
        ...(options || {}),
      });
    }

    /**
     * 测试新连接。
     *
     * @param {Object} params - 连接参数
     * @return {Promise<Object>} 测试结果响应
     */
    testNewConnection(params) {
      return this.httpClient.post(`${BASE_PATH}/actions/test-connection`, params || {});
    }

    /**
     * 验证连接参数。
     *
     * @param {Object} params - 连接参数
     * @return {Promise<Object>} 验证结果响应
     */
    validateConnectionParams(params) {
      return this.httpClient.post(`${BASE_PATH}/actions/validate-connection-params`, params || {});
    }

    /**
     * 批量测试连接。
     *
     * @param {Array<number>} instanceIds - 实例 ID 数组
     * @return {Promise<Object>} 批量测试结果响应
     * @throws {Error} 当 instanceIds 不是数组时抛出
     */
    batchTestConnections(instanceIds) {
      if (!Array.isArray(instanceIds)) {
        throw new Error("ConnectionService: batchTestConnections 需要 instanceIds 数组");
      }
      return this.httpClient.post(`${BASE_PATH}/actions/batch-test-connections`, {
        instance_ids: instanceIds,
      });
    }

    /**
     * 获取连接状态。
     *
     * @param {number|string} instanceId - 实例 ID
     * @return {Promise<Object>} 连接状态响应
     * @throws {Error} 当 instanceId 无效时抛出
     */
    getConnectionStatus(instanceId) {
      if (instanceId === undefined || instanceId === null || instanceId === "") {
        throw new Error("ConnectionService: getConnectionStatus 需要 instanceId");
      }
      return this.httpClient.get(`${BASE_PATH}/${instanceId}/connection-status`);
    }
  }

  global.ConnectionService = ConnectionService;
})(window);
