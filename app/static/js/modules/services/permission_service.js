(function (global) {
  "use strict";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("PermissionService: httpClient 未初始化");
    }
    return resolved;
  }

  class PermissionService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    fetchAccountPermissions(accountId) {
      if (accountId === undefined || accountId === null || accountId === "") {
        throw new Error("PermissionService: fetchAccountPermissions 需要 accountId");
      }
      return this.httpClient.get(`/account/api/${accountId}/permissions`);
    }

    fetchInstanceAccountPermissions(instanceId, accountId) {
      if (instanceId === undefined || instanceId === null || instanceId === "") {
        throw new Error("PermissionService: fetchInstanceAccountPermissions 需要 instanceId");
      }
      if (accountId === undefined || accountId === null || accountId === "") {
        throw new Error("PermissionService: fetchInstanceAccountPermissions 需要 accountId");
      }
      return this.httpClient.get(
        `/instances/api/${instanceId}/accounts/${accountId}/permissions`,
      );
    }

    fetchByUrl(url) {
      if (!url) {
        throw new Error("PermissionService: fetchByUrl 需要 url");
      }
      return this.httpClient.get(url);
    }
  }

  global.PermissionService = PermissionService;
})(window);

