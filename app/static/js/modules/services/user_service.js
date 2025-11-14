(function (global) {
  "use strict";

  const BASE_PATH = "/users/api";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("UserService: httpClient 未初始化");
    }
    return resolved;
  }

  class UserService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
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

