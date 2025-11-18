(function (global) {
  "use strict";

  const BASE_PATH = "/users/api";

  /**
   * 统一选择 http 客户端。
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("UserService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 用户管理 API 服务。
   */
  class UserService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    listUsers(params) {
      return this.httpClient.get(`${BASE_PATH}/users`, params || {});
    }

    getUser(userId) {
      if (userId === undefined || userId === null || userId === "") {
        throw new Error("UserService: getUser 需要 userId");
      }
      return this.httpClient.get(`${BASE_PATH}/users/${userId}`);
    }

    createUser(payload) {
      if (!payload) {
        throw new Error("UserService: createUser 需要 payload");
      }
      return this.httpClient.post(`${BASE_PATH}/users`, payload);
    }

    updateUser(userId, payload) {
      if (userId === undefined || userId === null || userId === "") {
        throw new Error("UserService: updateUser 需要 userId");
      }
      if (!payload) {
        throw new Error("UserService: updateUser 需要 payload");
      }
      return this.httpClient.put(`${BASE_PATH}/users/${userId}`, payload);
    }

    deleteUser(userId) {
      if (userId === undefined || userId === null || userId === "") {
        throw new Error("UserService: deleteUser 需要 userId");
      }
      return this.httpClient.delete(`${BASE_PATH}/users/${userId}`);
    }
  }

  global.UserService = UserService;
})(window);
