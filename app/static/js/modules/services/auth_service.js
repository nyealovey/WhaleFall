(function (global) {
  "use strict";

  const ENDPOINTS = {
    changePassword: "/api/v1/auth/change-password",
    logout: "/api/v1/auth/logout",
  };

  /**
   * 统一选择 http 客户端。
   *
   * @param {Object} client HTTP 客户端实例
   * @return {Object} HTTP 客户端实例
   * @throws {Error} 当客户端未初始化时抛出
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.post !== "function") {
      throw new Error("AuthService: httpClient 未初始化");
    }
    return resolved;
  }

  class AuthService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    /**
     * 修改当前用户密码。
     *
     * @param {Object} payload 请求体
     * @return {Promise<Object>} 后端响应
     */
    changePassword(payload) {
      if (!payload) {
        throw new Error("AuthService: changePassword 需要 payload");
      }
      return this.httpClient.post(ENDPOINTS.changePassword, payload);
    }

    /**
     * 登出当前用户。
     *
     * @return {Promise<Object>} 后端响应
     */
    logout() {
      return this.httpClient.post(ENDPOINTS.logout, {});
    }
  }

  global.AuthService = AuthService;
})(window);

