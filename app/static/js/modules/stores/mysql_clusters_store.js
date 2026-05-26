(function (global) {
  "use strict";

  function ensureService(service) {
    if (!service) {
      throw new Error("createMySQLClustersStore: service is required");
    }
    ["getGridUrl", "getCluster", "createCluster", "updateCluster", "replaceInstances", "syncTopology"].forEach(
      (method) => {
        // eslint-disable-next-line security/detect-object-injection
        if (typeof service[method] !== "function") {
          throw new Error("createMySQLClustersStore: service." + method + " 未实现");
        }
      }
    );
    return service;
  }

  function ensureSuccessResponse(response, fallbackMessage) {
    if (response && response.success === false) {
      const error = new Error(response.message || fallbackMessage || "操作失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  function createMySQLClustersStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const state = {
      gridUrl: service.getGridUrl(),
      lastError: null,
    };

    function handleError(error) {
      state.lastError = error;
      throw error;
    }

    return {
      gridUrl: state.gridUrl,
      actions: {
        load(clusterId) {
          return service
            .getCluster(clusterId)
            .then((response) => ensureSuccessResponse(response, "加载 MySQL 群集失败"))
            .then((response) => response?.data || {})
            .catch(handleError);
        },
        create(payload) {
          return service
            .createCluster(payload)
            .then((response) => ensureSuccessResponse(response, "创建 MySQL 群集失败"))
            .catch(handleError);
        },
        update(clusterId, payload) {
          return service
            .updateCluster(clusterId, payload)
            .then((response) => ensureSuccessResponse(response, "更新 MySQL 群集失败"))
            .catch(handleError);
        },
        replaceInstances(clusterId, instanceIds) {
          return service
            .replaceInstances(clusterId, instanceIds)
            .then((response) => ensureSuccessResponse(response, "保存 MySQL 实例绑定失败"))
            .catch(handleError);
        },
        syncTopology(clusterId) {
          return service
            .syncTopology(clusterId)
            .then((response) => ensureSuccessResponse(response, "同步 MySQL 主从信息失败"))
            .catch(handleError);
        },
      },
    };
  }

  global.createMySQLClustersStore = createMySQLClustersStore;
})(window);
