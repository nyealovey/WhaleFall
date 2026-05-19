(function (global) {
  "use strict";

  function ensureService(service) {
    if (!service) {
      throw new Error("createSQLServerClustersStore: service is required");
    }
    [
      "getGridUrl",
      "getCluster",
      "createCluster",
      "updateCluster",
      "replaceInstances",
      "createAvailabilityGroup",
      "updateAvailabilityGroup",
      "syncAvailabilityGroups",
    ].forEach((method) => {
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error("createSQLServerClustersStore: service." + method + " 未实现");
      }
    });
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

  function createSQLServerClustersStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = opts.emitter || (global.mitt ? global.mitt() : null);
    const state = {
      gridUrl: service.getGridUrl(),
      lastError: null,
    };

    function emit(eventName, payload) {
      if (emitter) {
        emitter.emit(eventName, payload || {});
      }
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("sqlserver-clusters:error", { error, meta: meta || {} });
      throw error;
    }

    return {
      gridUrl: state.gridUrl,
      actions: {
        load(clusterId) {
          return service
            .getCluster(clusterId)
            .then((response) => ensureSuccessResponse(response, "加载群集失败"))
            .then((response) => response?.data || {})
            .catch((error) => handleError(error, { action: "load", clusterId }));
        },
        create(payload) {
          return service
            .createCluster(payload)
            .then((response) => ensureSuccessResponse(response, "创建群集失败"))
            .catch((error) => handleError(error, { action: "create" }));
        },
        update(clusterId, payload) {
          return service
            .updateCluster(clusterId, payload)
            .then((response) => ensureSuccessResponse(response, "更新群集失败"))
            .catch((error) => handleError(error, { action: "update", clusterId }));
        },
        replaceInstances(clusterId, instanceIds) {
          return service
            .replaceInstances(clusterId, instanceIds)
            .then((response) => ensureSuccessResponse(response, "保存实例绑定失败"))
            .catch((error) => handleError(error, { action: "replaceInstances", clusterId }));
        },
        createAvailabilityGroup(clusterId, payload) {
          return service
            .createAvailabilityGroup(clusterId, payload)
            .then((response) => ensureSuccessResponse(response, "保存 AG 失败"))
            .catch((error) => handleError(error, { action: "createAvailabilityGroup", clusterId }));
        },
        updateAvailabilityGroup(clusterId, availabilityGroupId, payload) {
          return service
            .updateAvailabilityGroup(clusterId, availabilityGroupId, payload)
            .then((response) => ensureSuccessResponse(response, "保存 AG 失败"))
            .catch((error) =>
              handleError(error, {
                action: "updateAvailabilityGroup",
                clusterId,
                availabilityGroupId,
              })
            );
        },
        syncAvailabilityGroups(clusterId, payload) {
          return service
            .syncAvailabilityGroups(clusterId, payload)
            .then((response) => ensureSuccessResponse(response, "同步 AG 信息失败"))
            .catch((error) => handleError(error, { action: "syncAvailabilityGroups", clusterId }));
        },
      },
    };
  }

  global.createSQLServerClustersStore = createSQLServerClustersStore;
})(window);
