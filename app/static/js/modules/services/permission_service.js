(function (global) {
  "use strict";

  /**
   * 选用 http 客户端，默认 httpU。
   *
   * @param {Object} client - HTTP 客户端实例
   * @return {Object} HTTP 客户端实例
   * @throws {Error} 当客户端未初始化时抛出
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("PermissionService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 权限查询服务，支持账户/实例维度。
   *
   * 提供账户权限和实例账户权限的查询接口。
   *
   * @class
   */
  class PermissionService {
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
     * 获取账户权限信息。
     *
     * @param {number|string} accountId - 账户 ID
     * @return {Promise<Object>} 权限信息响应
     * @throws {Error} 当 accountId 无效时抛出
     */
    fetchAccountPermissions(accountId) {
      if (accountId === undefined || accountId === null || accountId === "") {
        throw new Error("PermissionService: fetchAccountPermissions 需要 accountId");
      }
      return this.httpClient.get(`/api/v1/accounts/ledgers/${accountId}/permissions`);
    }

    /**
     * 获取实例账户权限信息。
     *
     * @param {number|string} instanceId - 实例 ID
     * @param {number|string} accountId - 账户 ID
     * @return {Promise<Object>} 权限信息响应
     * @throws {Error} 当 instanceId 或 accountId 无效时抛出
     */
    fetchInstanceAccountPermissions(instanceId, accountId) {
      if (instanceId === undefined || instanceId === null || instanceId === "") {
        throw new Error("PermissionService: fetchInstanceAccountPermissions 需要 instanceId");
      }
      if (accountId === undefined || accountId === null || accountId === "") {
        throw new Error("PermissionService: fetchInstanceAccountPermissions 需要 accountId");
      }
      return this.httpClient.get(
        `/api/v1/instances/${instanceId}/accounts/${accountId}/permissions`,
      );
    }

    /**
     * 通过 URL 获取权限信息。
     *
     * @param {string} url - API URL
     * @return {Promise<Object>} 权限信息响应
     * @throws {Error} 当 url 为空时抛出
     */
    fetchByUrl(url) {
      if (!url) {
        throw new Error("PermissionService: fetchByUrl 需要 url");
      }
      return this.httpClient.get(url);
    }
  }

  global.PermissionService = PermissionService;
})(window);
