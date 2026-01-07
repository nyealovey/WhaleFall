(function (global) {
  "use strict";

  /**
   * 选用 http 客户端，默认使用全局 httpU。
   *
   * @param {Object} client - HTTP 客户端实例
   * @return {Object} HTTP 客户端实例
   * @throws {Error} 当客户端未初始化时抛出
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("InstanceManagementService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 构造查询字符串，兼容对象/URLSearchParams/字符串。
   *
   * @param {Object|URLSearchParams|string} params - 查询参数
   * @return {string} 查询字符串，以 ? 开头，如果为空则返回空字符串
   */
  function toQueryString(params) {
    if (!params) {
      return "";
    }
    if (params instanceof URLSearchParams) {
      const serialized = params.toString();
      return serialized ? `?${serialized}` : "";
    }
    if (typeof params === "string") {
      return params ? `?${params.replace(/^\?/, "")}` : "";
    }
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item !== undefined && item !== null && item !== "") {
            search.append(key, item);
          }
        });
      } else {
        search.append(key, value);
      }
    });
    const serialized = search.toString();
    return serialized ? `?${serialized}` : "";
  }

  /**
   * 实例管理 API 封装：同步、批量操作、统计等。
   *
   * 提供实例的同步、批量创建、批量删除、统计查询等功能。
   *
   * @class
   */
  class InstanceManagementService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    syncInstanceAccounts(instanceId, options = {}) {
      this.assertInstanceId(instanceId, "syncInstanceAccounts");
      const { customUrl } = options || {};
      const endpoint = customUrl || `/api/v1/instances/${instanceId}/actions/sync-accounts`;
      return this.httpClient.post(endpoint, {});
    }

    syncInstanceCapacity(instanceId) {
      this.assertInstanceId(instanceId, "syncInstanceCapacity");
      return this.httpClient.post(`/api/v1/instances/${instanceId}/actions/sync-capacity`);
    }

    syncAllAccounts() {
      return this.httpClient.post("/api/v1/instances/actions/sync-accounts");
    }

    fetchAccountChangeHistory(accountId) {
      if (!accountId && accountId !== 0) {
        throw new Error("InstanceManagementService: fetchAccountChangeHistory 需要 accountId");
      }
      return this.httpClient.get(
        `/api/v1/accounts/ledgers/${accountId}/change-history`,
      );
    }

    fetchInstanceAccountPermissions(accountId) {
      if (!accountId && accountId !== 0) {
        throw new Error("InstanceManagementService: fetchInstanceAccountPermissions 需要 accountId");
      }
      return this.httpClient.get(
        `/api/v1/accounts/ledgers/${accountId}/permissions`,
      );
    }

    fetchDatabaseSizes(instanceId, params) {
      this.assertInstanceId(instanceId, "fetchDatabaseSizes");
      const query = toQueryString(params);
      const normalizedQuery = query ? query.replace(/^\?/, "&") : "";
      return this.httpClient.get(`/api/v1/databases/sizes?instance_id=${instanceId}${normalizedQuery}`);
    }

    fetchDatabaseTableSizes(databaseId, params) {
      if (!databaseId && databaseId !== 0) {
        throw new Error("InstanceManagementService: fetchDatabaseTableSizes 需要 databaseId");
      }
      const query = toQueryString(params);
      return this.httpClient.get(
        `/api/v1/databases/${databaseId}/tables/sizes${query}`,
      );
    }

    refreshDatabaseTableSizes(databaseId, params) {
      if (!databaseId && databaseId !== 0) {
        throw new Error("InstanceManagementService: refreshDatabaseTableSizes 需要 databaseId");
      }
      const query = toQueryString(params);
      return this.httpClient.post(
        `/api/v1/databases/${databaseId}/tables/sizes/actions/refresh${query}`,
      );
    }

    batchDeleteInstances(instanceIds) {
      if (!Array.isArray(instanceIds) || instanceIds.length === 0) {
        throw new Error("InstanceManagementService: batchDeleteInstances 需要实例ID");
      }
      return this.httpClient.post("/api/v1/instances/actions/batch-delete", {
        instance_ids: instanceIds,
      });
    }

    batchCreateInstances(formData) {
      if (!(formData instanceof FormData)) {
        throw new Error("InstanceManagementService: batchCreateInstances 需要 FormData");
      }
      return this.httpClient.post("/api/v1/instances/actions/batch-create", formData);
    }

    restoreInstance(instanceId) {
      this.assertInstanceId(instanceId, "restoreInstance");
      return this.httpClient.post(`/api/v1/instances/${instanceId}/actions/restore`);
    }

    fetchStatistics() {
      return this.httpClient.get("/api/v1/instances/statistics");
    }

    assertInstanceId(instanceId, action) {
      if (instanceId === undefined || instanceId === null || instanceId === "") {
        throw new Error(`InstanceManagementService: ${action} 需要 instanceId`);
      }
    }
  }

  global.InstanceManagementService = InstanceManagementService;
})(window);
