(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/sqlserver-clusters";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("SQLServerClustersService: ServiceUtils 未初始化");
  }

  class SQLServerClustersService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "SQLServerClustersService");
    }

    list(params) {
      return this.httpClient.get(BASE_PATH, params || {});
    }

    getGridUrl() {
      const params = new URLSearchParams();
      params.set("sort", "id");
      params.set("order", "desc");
      return `${BASE_PATH}?${params.toString()}`;
    }

    getCluster(clusterId) {
      this.ensureId(clusterId, "getCluster");
      return this.httpClient.get(`${BASE_PATH}/${clusterId}`);
    }

    createCluster(payload) {
      this.ensurePayload(payload, "createCluster");
      return this.httpClient.post(BASE_PATH, payload);
    }

    updateCluster(clusterId, payload) {
      this.ensureId(clusterId, "updateCluster");
      this.ensurePayload(payload, "updateCluster");
      return this.httpClient.patch(`${BASE_PATH}/${clusterId}`, payload);
    }

    replaceInstances(clusterId, instanceIds) {
      this.ensureId(clusterId, "replaceInstances");
      return this.httpClient.put(`${BASE_PATH}/${clusterId}/instances`, {
        instance_ids: Array.isArray(instanceIds) ? instanceIds : [],
      });
    }

    createAvailabilityGroup(clusterId, payload) {
      this.ensureId(clusterId, "createAvailabilityGroup");
      this.ensurePayload(payload, "createAvailabilityGroup");
      return this.httpClient.post(`${BASE_PATH}/${clusterId}/availability-groups`, payload);
    }

    updateAvailabilityGroup(clusterId, availabilityGroupId, payload) {
      this.ensureId(clusterId, "updateAvailabilityGroup");
      this.ensureId(availabilityGroupId, "updateAvailabilityGroup");
      this.ensurePayload(payload, "updateAvailabilityGroup");
      return this.httpClient.patch(
        `${BASE_PATH}/${clusterId}/availability-groups/${availabilityGroupId}`,
        payload
      );
    }

    syncAvailabilityGroups(clusterId, payload) {
      this.ensureId(clusterId, "syncAvailabilityGroups");
      this.ensurePayload(payload, "syncAvailabilityGroups");
      return this.httpClient.post(`${BASE_PATH}/${clusterId}/availability-groups/actions/sync`, payload);
    }

    syncAgAccounts(clusterId) {
      this.ensureId(clusterId, "syncAgAccounts");
      return this.httpClient.post(`${BASE_PATH}/${clusterId}/availability-groups/actions/sync-accounts`, {});
    }

    ensureId(value, action) {
      if (value === undefined || value === null || value === "") {
        throw new Error(`SQLServerClustersService: ${action} 需要 id`);
      }
    }

    ensurePayload(payload, action) {
      if (!payload || typeof payload !== "object") {
        throw new Error(`SQLServerClustersService: ${action} 需要 payload`);
      }
    }
  }

  global.SQLServerClustersService = SQLServerClustersService;
})(window);
