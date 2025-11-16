(function (window) {
  "use strict";

  function ensureService(service) {
    if (!service) {
      throw new Error("createAccountClassificationStore: service is required");
    }
    const requiredMethods = [
      "listClassifications",
      "createClassification",
      "updateClassification",
      "deleteClassification",
      "listRules",
      "createRule",
      "updateRule",
      "deleteRule",
      "ruleStats",
      "triggerAutomation",
      "fetchPermissions",
    ];
    requiredMethods.forEach(function (method) {
      if (typeof service[method] !== "function") {
        throw new Error(
          "createAccountClassificationStore: service." + method + " 未实现",
        );
      }
    });
    if (typeof service.getClassification !== "function") {
      // 细粒度 detail 调用由页面直接访问，可选
      console.warn(
        "AccountClassificationService 缺少 getClassification()，store 将无法提供 detail",
      );
    }
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createAccountClassificationStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function cloneClassifications(items) {
    return (items || []).map(function (classification) {
      return Object.assign({}, classification);
    });
  }

  function cloneRulesMap(source) {
    const result = {};
    Object.keys(source || {}).forEach(function (key) {
      result[key] = (source[key] || []).map(function (rule) {
        return Object.assign({}, rule);
      });
    });
    return result;
  }

  function cloneState(state) {
    return {
      classifications: cloneClassifications(state.classifications),
      rulesByDbType: cloneRulesMap(state.rulesByDbType),
      permissionsByDbType: Object.assign({}, state.permissionsByDbType),
      loading: Object.assign({}, state.loading),
      lastError: state.lastError,
    };
  }

  function ensureArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function extractClassifications(response) {
    const collection =
      response?.data?.classifications ?? response?.classifications ?? [];
    return ensureArray(collection);
  }

  function extractRules(response) {
    const raw =
      response?.data?.rules_by_db_type ?? response?.rules_by_db_type ?? {};
    if (typeof raw !== "object" || raw === null) {
      return {};
    }
    const map = {};
    Object.keys(raw).forEach(function (key) {
      map[key] = ensureArray(raw[key]);
    });
    return map;
  }

  function collectRuleIds(rulesByDbType) {
    const ids = [];
    Object.values(rulesByDbType || {}).forEach(function (rules) {
      ensureArray(rules).forEach(function (rule) {
        if (rule && typeof rule.id === "number") {
          ids.push(rule.id);
        }
      });
    });
    return ids;
  }

  function createAccountClassificationStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      classifications: [],
      rulesByDbType: {},
      permissionsByDbType: {},
      loading: {
        classifications: false,
        rules: false,
        permissions: false,
        operation: false,
      },
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(
        eventName,
        payload ??
          {
            state: cloneState(state),
          },
      );
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("accountClassification:error", {
        error,
        meta,
        state: cloneState(state),
      });
    }

    function attachRuleStats(rulesByDbType) {
      const ids = collectRuleIds(rulesByDbType);
      if (!ids.length) {
        return Promise.resolve(rulesByDbType);
      }
      return service
        .ruleStats(ids)
        .then(function (response) {
          const stats =
            response?.data?.rule_stats ?? response?.rule_stats ?? [];
          const statsMap = {};
          ensureArray(stats).forEach(function (item) {
            if (item && typeof item.rule_id === "number") {
              statsMap[item.rule_id] = item.matched_accounts_count ?? 0;
            }
          });
          Object.values(rulesByDbType).forEach(function (rules) {
            ensureArray(rules).forEach(function (rule) {
              if (rule && typeof rule.id === "number") {
                rule.matched_accounts_count = statsMap[rule.id] ?? 0;
              }
            });
          });
          return rulesByDbType;
        })
        .catch(function (error) {
          console.error("AccountClassificationStore: 加载规则统计失败", error);
          return rulesByDbType;
        });
    }

    function withLoading(key, promiseFactory) {
      state.loading[key] = true;
      emit("accountClassification:loading", {
        target: key,
        state: cloneState(state),
      });
      return Promise.resolve()
        .then(promiseFactory)
        .finally(function () {
          state.loading[key] = false;
        });
    }

    const actions = {
      loadClassifications: function () {
        return withLoading("classifications", function () {
          return service
            .listClassifications()
            .then(function (response) {
              state.classifications = extractClassifications(response);
              emit("accountClassification:classificationsUpdated", {
                classifications: cloneClassifications(state.classifications),
                state: cloneState(state),
              });
              state.lastError = null;
              return state.classifications;
            })
            .catch(function (error) {
              handleError(error, { action: "loadClassifications" });
              throw error;
            });
        });
      },
      loadRules: function () {
        return withLoading("rules", function () {
          return service
            .listRules()
            .then(function (response) {
              const rules = extractRules(response);
              return attachRuleStats(rules);
            })
            .then(function (rulesWithStats) {
              state.rulesByDbType = rulesWithStats;
              emit("accountClassification:rulesUpdated", {
                rulesByDbType: cloneRulesMap(state.rulesByDbType),
                state: cloneState(state),
              });
              state.lastError = null;
              return state.rulesByDbType;
            })
            .catch(function (error) {
              handleError(error, { action: "loadRules" });
              throw error;
            });
        });
      },
      loadPermissions: function (dbType) {
        if (!dbType) {
          return Promise.resolve([]);
        }
        return withLoading("permissions", function () {
          return service
            .fetchPermissions(dbType)
            .then(function (response) {
              const list =
                response?.data?.permissions ?? response?.permissions ?? [];
              state.permissionsByDbType[dbType] = ensureArray(list);
              emit("accountClassification:permissionsUpdated", {
                dbType,
                permissions: ensureArray(list).slice(),
                state: cloneState(state),
              });
              return state.permissionsByDbType[dbType];
            })
            .catch(function (error) {
              handleError(error, { action: "loadPermissions", dbType });
              throw error;
            });
        });
      },
      createClassification: function (payload) {
        return withLoading("operation", function () {
          return service
            .createClassification(payload)
            .then(function (response) {
              emit("accountClassification:operationSuccess", {
                action: "createClassification",
                response,
                state: cloneState(state),
              });
              return actions
                .loadClassifications()
                .then(function () {
                  return response;
                });
            })
            .catch(function (error) {
              handleError(error, { action: "createClassification" });
              throw error;
            });
        });
      },
      updateClassification: function (id, payload) {
        return withLoading("operation", function () {
          return service
            .updateClassification(id, payload)
            .then(function (response) {
              emit("accountClassification:operationSuccess", {
                action: "updateClassification",
                response,
                state: cloneState(state),
              });
              return actions
                .loadClassifications()
                .then(function () {
                  return response;
                });
            })
            .catch(function (error) {
              handleError(error, { action: "updateClassification" });
              throw error;
            });
        });
      },
      deleteClassification: function (id) {
        return withLoading("operation", function () {
          return service
            .deleteClassification(id)
            .then(function (response) {
              emit("accountClassification:operationSuccess", {
                action: "deleteClassification",
                response,
                state: cloneState(state),
              });
              return Promise.all([
                actions.loadClassifications(),
                actions.loadRules(),
              ]).then(function () {
                return response;
              });
            })
            .catch(function (error) {
              handleError(error, { action: "deleteClassification" });
              throw error;
            });
        });
      },
      createRule: function (payload) {
        return withLoading("operation", function () {
          return service
            .createRule(payload)
            .then(function (response) {
              emit("accountClassification:operationSuccess", {
                action: "createRule",
                response,
                state: cloneState(state),
              });
              return actions.loadRules().then(function () {
                return response;
              });
            })
            .catch(function (error) {
              handleError(error, { action: "createRule" });
              throw error;
            });
        });
      },
      updateRule: function (id, payload) {
        return withLoading("operation", function () {
          return service
            .updateRule(id, payload)
            .then(function (response) {
              emit("accountClassification:operationSuccess", {
                action: "updateRule",
                response,
                state: cloneState(state),
              });
              return actions.loadRules().then(function () {
                return response;
              });
            })
            .catch(function (error) {
              handleError(error, { action: "updateRule" });
              throw error;
            });
        });
      },
      deleteRule: function (id) {
        return withLoading("operation", function () {
          return service
            .deleteRule(id)
            .then(function (response) {
              emit("accountClassification:operationSuccess", {
                action: "deleteRule",
                response,
                state: cloneState(state),
              });
              return actions.loadRules().then(function () {
                return response;
              });
            })
            .catch(function (error) {
              handleError(error, { action: "deleteRule" });
              throw error;
            });
        });
      },
      triggerAutomation: function (payload) {
        return withLoading("operation", function () {
          return service
            .triggerAutomation(payload || {})
            .then(function (response) {
              emit("accountClassification:operationSuccess", {
                action: "triggerAutomation",
                response,
                state: cloneState(state),
              });
              return response;
            })
            .catch(function (error) {
              handleError(error, { action: "triggerAutomation" });
              throw error;
            });
        });
      },
    };

    const api = {
      init: function () {
        return Promise.all([
          actions.loadClassifications(),
          actions.loadRules(),
        ]);
      },
      getState: function () {
        return cloneState(state);
      },
      subscribe: function (eventName, handler) {
        emitter.on(eventName, handler);
      },
      unsubscribe: function (eventName, handler) {
        emitter.off(eventName, handler);
      },
      actions: actions,
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.classifications = [];
        state.rulesByDbType = {};
        state.permissionsByDbType = {};
      },
    };

    return api;
  }

  window.createAccountClassificationStore = createAccountClassificationStore;
})(window);
