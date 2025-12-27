(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/credentials";

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
      throw new Error("CredentialsService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 凭据管理服务。
   *
   * 提供凭据的增删改查接口。
   *
   * @class
   */
  class CredentialsService {
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
     * 获取凭据列表。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 凭据列表响应
     */
    list(params) {
      return this.httpClient.get(`${BASE_PATH}`, params || {});
    }

    /**
     * 获取单个凭据详情。
     *
     * @param {number|string} id - 凭据 ID
     * @return {Promise<Object>} 凭据详情响应
     * @throws {Error} 当 id 为空时抛出
     */
    getCredential(id) {
      if (id === undefined || id === null || id === "") {
        throw new Error("CredentialsService: getCredential 需要 credentialId");
      }
      return this.httpClient.get(`${BASE_PATH}/${id}`);
    }

    /**
     * 创建凭据。
     *
     * @param {Object} payload - 凭据数据
     * @return {Promise<Object>} 创建结果响应
     * @throws {Error} 当 payload 为空时抛出
     */
    createCredential(payload) {
      if (!payload) {
        throw new Error("CredentialsService: createCredential 需要 payload");
      }
      return this.httpClient.post(`${BASE_PATH}`, payload);
    }

    /**
     * 更新凭据。
     *
     * @param {number|string} id - 凭据 ID
     * @param {Object} payload - 更新数据
     * @return {Promise<Object>} 更新结果响应
     * @throws {Error} 当 id 或 payload 为空时抛出
     */
    updateCredential(id, payload) {
      if (id === undefined || id === null || id === "") {
        throw new Error("CredentialsService: updateCredential 需要 credentialId");
      }
      if (!payload) {
        throw new Error("CredentialsService: updateCredential 需要 payload");
      }
      return this.httpClient.put(`${BASE_PATH}/${id}`, payload);
    }

    /**
     * 删除凭据。
     *
     * @param {number} credentialId - 凭据 ID
     * @return {Promise<Object>} 删除结果响应
     * @throws {Error} 当 credentialId 为空时抛出
     */
    deleteCredential(credentialId) {
      if (!credentialId && credentialId !== 0) {
        throw new Error("CredentialsService: deleteCredential 需要 credentialId");
      }
      return this.httpClient.post(`${BASE_PATH}/${credentialId}/delete`);
    }
  }

  global.CredentialsService = CredentialsService;
})(window);
