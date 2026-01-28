  (function (global) {
    "use strict";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("InstanceManagementService: ServiceUtils 未初始化");
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
      this.httpClient = ensureHttpClient(httpClient, "InstanceManagementService");
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

    /**
     * 获取实例下拉选项。
     *
     * @param {string|null} dbType 数据库类型，可选
     * @return {Promise<Object>} 后端响应
     */
    fetchInstanceOptions(dbType) {
      const normalized = typeof dbType === "string" ? dbType.trim() : "";
      return this.httpClient.get("/api/v1/instances/options", {
        params: { db_type: normalized || undefined },
        headers: { Accept: "application/json" },
      });
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
