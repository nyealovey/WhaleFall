(function (global) {
  "use strict";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("InstanceManagementService: httpClient 未初始化");
    }
    return resolved;
  }

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

  class InstanceManagementService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    syncInstanceAccounts(instanceId) {
      this.assertInstanceId(instanceId, "syncInstanceAccounts");
      return this.httpClient.post(`/account_sync/api/instances/${instanceId}/sync`);
    }

    syncInstanceCapacity(instanceId) {
      this.assertInstanceId(instanceId, "syncInstanceCapacity");
      return this.httpClient.post(`/capacity/api/instances/${instanceId}/sync-capacity`);
    }

    syncAllAccounts() {
      return this.httpClient.post("/account_sync/api/sync-all");
    }

    fetchAccountChangeHistory(instanceId, accountId) {
      this.assertInstanceId(instanceId, "fetchAccountChangeHistory");
      if (!accountId && accountId !== 0) {
        throw new Error("InstanceManagementService: fetchAccountChangeHistory 需要 accountId");
      }
      return this.httpClient.get(
        `/instances/api/${instanceId}/accounts/${accountId}/change-history`,
      );
    }

    fetchInstanceAccountPermissions(instanceId, accountId) {
      this.assertInstanceId(instanceId, "fetchInstanceAccountPermissions");
      if (!accountId && accountId !== 0) {
        throw new Error("InstanceManagementService: fetchInstanceAccountPermissions 需要 accountId");
      }
      return this.httpClient.get(
        `/instances/api/${instanceId}/accounts/${accountId}/permissions`,
      );
    }

    fetchDatabaseSizes(instanceId, params) {
      this.assertInstanceId(instanceId, "fetchDatabaseSizes");
      const query = toQueryString(params);
      return this.httpClient.get(
        `/instances/api/databases/${instanceId}/sizes${query}`,
      );
    }

    fetchDatabaseTotalSize(instanceId) {
      this.assertInstanceId(instanceId, "fetchDatabaseTotalSize");
      return this.httpClient.get(
        `/database_aggr/api/instances/${instanceId}/database-sizes/total`,
      );
    }

    batchDeleteInstances(instanceIds) {
      if (!Array.isArray(instanceIds) || instanceIds.length === 0) {
        throw new Error("InstanceManagementService: batchDeleteInstances 需要实例ID");
      }
      return this.httpClient.post("/instances/api/batch-delete", {
        instance_ids: instanceIds,
      });
    }

    batchCreateInstances(formData) {
      if (!(formData instanceof FormData)) {
        throw new Error("InstanceManagementService: batchCreateInstances 需要 FormData");
      }
      return this.httpClient.post("/instances/api/batch-create", formData);
    }

    fetchStatistics() {
      return this.httpClient.get("/instances/api/statistics");
    }

    assertInstanceId(instanceId, action) {
      if (instanceId === undefined || instanceId === null || instanceId === "") {
        throw new Error(`InstanceManagementService: ${action} 需要 instanceId`);
      }
    }
  }

  global.InstanceManagementService = InstanceManagementService;
})(window);

