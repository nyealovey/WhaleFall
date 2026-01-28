(function (global) {
  "use strict";

  const ENDPOINTS = {
    changePassword: "/api/v1/auth/change-password",
    logout: "/api/v1/auth/logout",
  };

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("AuthService: ServiceUtils 未初始化");
  }

  class AuthService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "AuthService", "post");
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
