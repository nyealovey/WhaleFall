(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/mysql-clusters";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("MySQLClustersService: ServiceUtils 未初始化");
  }

  class MySQLClustersService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "MySQLClustersService");
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

    syncTopology(clusterId) {
      this.ensureId(clusterId, "syncTopology");
      return this.httpClient.post(`${BASE_PATH}/${clusterId}/actions/sync-topology`, {});
    }

    ensureId(value, action) {
      if (value === undefined || value === null || value === "") {
        throw new Error(`MySQLClustersService: ${action} 需要 id`);
      }
    }

    ensurePayload(payload, action) {
      if (!payload || typeof payload !== "object") {
        throw new Error(`MySQLClustersService: ${action} 需要 payload`);
      }
    }
  }

  global.MySQLClustersService = MySQLClustersService;
})(window);
