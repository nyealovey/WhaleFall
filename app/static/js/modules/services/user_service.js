(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/users";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("UserService: ServiceUtils 未初始化");
  }

  /**
   * 用户管理服务。
   *
   * 提供用户的增删改查接口。
   *
   * @class
   */
  class UserService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     */
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "UserService");
    }

    /**
     * 获取用户列表。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 用户列表响应
     */
    listUsers(params) {
      return this.httpClient.get(`${BASE_PATH}`, params || {});
    }

    /**
     * 用户列表 Grid 数据源 URL（含默认排序）。
     *
     * @returns {string} API URL
     */
    getGridUrl() {
      const params = new URLSearchParams();
      params.set("sort", "created_at");
      params.set("order", "desc");
      return `${BASE_PATH}?${params.toString()}`;
    }

    /**
     * 获取单个用户详情。
     *
     * @param {number|string} userId - 用户 ID
     * @return {Promise<Object>} 用户详情响应
     * @throws {Error} 当 userId 为空时抛出
     */
    getUser(userId) {
      if (userId === undefined || userId === null || userId === "") {
        throw new Error("UserService: getUser 需要 userId");
      }
      return this.httpClient.get(`${BASE_PATH}/${userId}`);
    }

    /**
     * 创建用户。
     *
     * @param {Object} payload - 用户数据
     * @return {Promise<Object>} 创建结果响应
     * @throws {Error} 当 payload 为空时抛出
     */
    createUser(payload) {
      if (!payload) {
        throw new Error("UserService: createUser 需要 payload");
      }
      return this.httpClient.post(`${BASE_PATH}`, payload);
    }

    /**
     * 更新用户。
     *
     * @param {number|string} userId - 用户 ID
     * @param {Object} payload - 更新数据
     * @return {Promise<Object>} 更新结果响应
     * @throws {Error} 当 userId 或 payload 为空时抛出
     */
    updateUser(userId, payload) {
      if (userId === undefined || userId === null || userId === "") {
        throw new Error("UserService: updateUser 需要 userId");
      }
      if (!payload) {
        throw new Error("UserService: updateUser 需要 payload");
      }
      return this.httpClient.put(`${BASE_PATH}/${userId}`, payload);
    }

    /**
     * 删除用户。
     *
     * @param {number|string} userId - 用户 ID
     * @return {Promise<Object>} 删除结果响应
     * @throws {Error} 当 userId 为空时抛出
     */
    deleteUser(userId) {
      if (userId === undefined || userId === null || userId === "") {
        throw new Error("UserService: deleteUser 需要 userId");
      }
      return this.httpClient.delete(`${BASE_PATH}/${userId}`);
    }
  }

  global.UserService = UserService;
})(window);
