(function (global) {
  "use strict";

  const BASE_PATH = "/connections/api";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("ConnectionService: httpClient 未初始化");
    }
    return resolved;
  }

  class ConnectionService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    testInstanceConnection(instanceId, options) {
      if (instanceId === undefined || instanceId === null || instanceId === "") {
        throw new Error("ConnectionService: testInstanceConnection 需要 instanceId");
      }
      return this.httpClient.post(`${BASE_PATH}/test`, {
        instance_id: instanceId,
        ...(options || {}),
      });
    }

    testNewConnection(params) {
      return this.httpClient.post(`${BASE_PATH}/test`, params || {});
    }

    validateConnectionParams(params) {
      return this.httpClient.post(`${BASE_PATH}/validate-params`, params || {});
    }

    batchTestConnections(instanceIds) {
      if (!Array.isArray(instanceIds)) {
        throw new Error("ConnectionService: batchTestConnections 需要 instanceIds 数组");
      }
      return this.httpClient.post(`${BASE_PATH}/batch-test`, {
        instance_ids: instanceIds,
      });
    }

    getConnectionStatus(instanceId) {
      if (instanceId === undefined || instanceId === null || instanceId === "") {
        throw new Error("ConnectionService: getConnectionStatus 需要 instanceId");
      }
      return this.httpClient.get(`${BASE_PATH}/status/${instanceId}`);
    }
  }

  global.ConnectionService = ConnectionService;
})(window);

