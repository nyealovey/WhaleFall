(function (window) {
  "use strict";

  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const isSafeKey = (key) => typeof key === "string" && key && !UNSAFE_KEYS.includes(key);

  const EVENT_NAMES = {
    loading: "accountClassification:loading",
    classificationsUpdated: "accountClassification:classificationsUpdated",
    rulesUpdated: "accountClassification:rulesUpdated",
    error: "accountClassification:error",
  };

  function ensureService(service) {
    if (!service) {
      throw new Error("createAccountClassificationStore: service is required");
    }
    [
      "listClassifications",
      "getClassification",
      "createClassification",
      "updateClassification",
      "deleteClassification",
      "listRules",
      "getRule",
      "createRule",
      "updateRule",
      "deleteRule",
      "ruleStats",
      "triggerAutomation",
      "fetchPermissions",
    ].forEach(function (method) {
      // 固定白名单方法名，避免动态键注入。
      // eslint-disable-next-line security/detect-object-injection
      if (typeof service[method] !== "function") {
        throw new Error("createAccountClassificationStore: service." + method + " 未实现");
      }
    });
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

  function ensureSuccess(response, fallbackMessage) {
    if (response && response.success === false) {
      const error = new Error(response.message || response.error || fallbackMessage || "操作失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  function cloneClassifications(list) {
    if (!Array.isArray(list)) {
      return [];
    }
    return list.map(function (item) {
      return item && typeof item === "object" ? Object.assign({}, item) : item;
    });
  }

  function cloneRulesByDbType(rulesByDbType) {
    const source = rulesByDbType && typeof rulesByDbType === "object" ? rulesByDbType : {};
    const cloned = {};
    Object.keys(source).forEach(function (key) {
      if (!isSafeKey(key)) {
        return;
      }
      // eslint-disable-next-line security/detect-object-injection
      const group = source[key];
      // eslint-disable-next-line security/detect-object-injection
      cloned[key] = Array.isArray(group)
        ? group.map(function (rule) {
            return rule && typeof rule === "object" ? Object.assign({}, rule) : rule;
          })
        : [];
    });
    return cloned;
  }

  function cloneState(state) {
    return {
      classifications: cloneClassifications(state.classifications),
      rulesByDbType: cloneRulesByDbType(state.rulesByDbType),
      loading: Object.assign({}, state.loading),
      lastError: state.lastError,
    };
  }

  function extractClassifications(response) {
    const list = response?.data?.classifications ?? [];
    return Array.isArray(list) ? list : [];
  }

  function extractRulesByDbType(response) {
    const raw = response?.data?.rules_by_db_type ?? {};
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      return {};
    }
    const normalized = {};
    Object.keys(raw).forEach(function (dbType) {
      if (!isSafeKey(dbType)) {
        return;
      }
      // eslint-disable-next-line security/detect-object-injection
      const group = raw[dbType];
      // eslint-disable-next-line security/detect-object-injection
      normalized[dbType] = Array.isArray(group) ? group : [];
    });
    return normalized;
  }

  function collectRuleIds(rulesByDbType) {
    const ids = [];
    const groups = rulesByDbType && typeof rulesByDbType === "object" ? rulesByDbType : {};
    Object.values(groups).forEach(function (group) {
      if (!Array.isArray(group)) {
        return;
      }
      group.forEach(function (rule) {
        if (rule && typeof rule === "object" && typeof rule.id === "number") {
          ids.push(rule.id);
        }
      });
    });
    return ids;
  }

  function applyRuleStats(rulesByDbType, response) {
    const statsList = response?.data?.rule_stats ?? [];
    if (!Array.isArray(statsList)) {
      return;
    }

    const statsMap = {};
    statsList.forEach(function (item) {
      if (item && typeof item.rule_id === "number") {
        statsMap[item.rule_id] = item.matched_accounts_count ?? 0;
      }
    });

    const groups = rulesByDbType && typeof rulesByDbType === "object" ? rulesByDbType : {};
    Object.values(groups).forEach(function (group) {
      if (!Array.isArray(group)) {
        return;
      }
      group.forEach(function (rule) {
        if (!rule || typeof rule !== "object" || typeof rule.id !== "number") {
          return;
        }
        rule.matched_accounts_count = statsMap[rule.id] ?? 0;
      });
    });
  }

  function createAccountClassificationStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      classifications: [],
      rulesByDbType: {},
      loading: {
        classifications: false,
        rules: false,
      },
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function emitLoading(target) {
      emit(EVENT_NAMES.loading, {
        target: target || "unknown",
        loading: Object.assign({}, state.loading),
        state: cloneState(state),
      });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit(EVENT_NAMES.error, {
        error: error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    const actions = {
      loadClassifications: function () {
        state.loading.classifications = true;
        emitLoading("classifications");
        return service
          .listClassifications()
          .then(function (response) {
            const result = ensureSuccess(response, "加载分类失败");
            state.classifications = extractClassifications(result);
            state.lastError = null;
            emit(EVENT_NAMES.classificationsUpdated, {
              classifications: cloneClassifications(state.classifications),
              state: cloneState(state),
            });
            return cloneClassifications(state.classifications);
          })
          .catch(function (error) {
            handleError(error, { action: "loadClassifications" });
            throw error;
          })
          .finally(function () {
            state.loading.classifications = false;
            emitLoading("classifications");
          });
      },

      loadRules: function () {
        state.loading.rules = true;
        emitLoading("rules");

        // 先更新规则列表，再尝试补齐统计；统计失败也会抛错，但 UI 仍可渲染规则列表。
        return service
          .listRules()
          .then(function (response) {
            const result = ensureSuccess(response, "加载规则失败");
            state.rulesByDbType = extractRulesByDbType(result);
            state.lastError = null;
            emit(EVENT_NAMES.rulesUpdated, {
              rulesByDbType: cloneRulesByDbType(state.rulesByDbType),
              state: cloneState(state),
            });
            return collectRuleIds(state.rulesByDbType);
          })
          .catch(function (error) {
            handleError(error, { action: "loadRules" });
            throw error;
          })
          .then(function (ids) {
            if (!ids || !ids.length) {
              return null;
            }
            return service
              .ruleStats(ids)
              .then(function (response) {
                const result = ensureSuccess(response, "加载规则统计失败");
                applyRuleStats(state.rulesByDbType, result);
                emit(EVENT_NAMES.rulesUpdated, {
                  rulesByDbType: cloneRulesByDbType(state.rulesByDbType),
                  state: cloneState(state),
                });
                return result;
              })
              .catch(function (error) {
                handleError(error, { action: "loadRuleStats" });
                throw error;
              });
          })
          .finally(function () {
            state.loading.rules = false;
            emitLoading("rules");
          });
      },

      fetchClassificationDetail: function (id) {
        return service
          .getClassification(id)
          .then(function (response) {
            const result = ensureSuccess(response, "获取分类信息失败");
            state.lastError = null;
            return result;
          })
          .catch(function (error) {
            handleError(error, { action: "fetchClassificationDetail", id: id });
            throw error;
          });
      },

      createClassification: function (payload) {
        return service
          .createClassification(payload)
          .then(function (response) {
            const result = ensureSuccess(response, "创建分类失败");
            return actions.loadClassifications().then(function () {
              return result;
            });
          })
          .catch(function (error) {
            handleError(error, { action: "createClassification" });
            throw error;
          });
      },

      updateClassification: function (id, payload) {
        return service
          .updateClassification(id, payload)
          .then(function (response) {
            const result = ensureSuccess(response, "更新分类失败");
            return actions.loadClassifications().then(function () {
              return result;
            });
          })
          .catch(function (error) {
            handleError(error, { action: "updateClassification", id: id });
            throw error;
          });
      },

      deleteClassification: function (id) {
        return service
          .deleteClassification(id)
          .then(function (response) {
            const result = ensureSuccess(response, "删除分类失败");
            return Promise.all([actions.loadClassifications(), actions.loadRules()]).then(function () {
              return result;
            });
          })
          .catch(function (error) {
            handleError(error, { action: "deleteClassification", id: id });
            throw error;
          });
      },

      fetchRuleDetail: function (id) {
        return service
          .getRule(id)
          .then(function (response) {
            const result = ensureSuccess(response, "获取规则信息失败");
            state.lastError = null;
            return result;
          })
          .catch(function (error) {
            handleError(error, { action: "fetchRuleDetail", id: id });
            throw error;
          });
      },

      createRule: function (payload) {
        return service
          .createRule(payload)
          .then(function (response) {
            const result = ensureSuccess(response, "创建规则失败");
            return Promise.all([actions.loadRules(), actions.loadClassifications()]).then(function () {
              return result;
            });
          })
          .catch(function (error) {
            handleError(error, { action: "createRule" });
            throw error;
          });
      },

      updateRule: function (id, payload) {
        return service
          .updateRule(id, payload)
          .then(function (response) {
            const result = ensureSuccess(response, "更新规则失败");
            return Promise.all([actions.loadRules(), actions.loadClassifications()]).then(function () {
              return result;
            });
          })
          .catch(function (error) {
            handleError(error, { action: "updateRule", id: id });
            throw error;
          });
      },

      deleteRule: function (id) {
        return service
          .deleteRule(id)
          .then(function (response) {
            const result = ensureSuccess(response, "删除规则失败");
            return Promise.all([actions.loadRules(), actions.loadClassifications()]).then(function () {
              return result;
            });
          })
          .catch(function (error) {
            handleError(error, { action: "deleteRule", id: id });
            throw error;
          });
      },

      triggerAutomation: function (payload) {
        return service
          .triggerAutomation(payload || {})
          .then(function (response) {
            const result = ensureSuccess(response, "触发自动分类失败");
            state.lastError = null;
            return result;
          })
          .catch(function (error) {
            handleError(error, { action: "triggerAutomation" });
            throw error;
          });
      },

      fetchPermissions: function (dbType) {
        return service
          .fetchPermissions(dbType)
          .then(function (response) {
            const result = ensureSuccess(response, "加载权限配置失败");
            state.lastError = null;
            return result;
          })
          .catch(function (error) {
            handleError(error, { action: "fetchPermissions", dbType: dbType });
            throw error;
          });
      },
    };

    const api = {
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
        state.loading.classifications = false;
        state.loading.rules = false;
        state.lastError = null;
      },
    };

    return api;
  }

  window.createAccountClassificationStore = createAccountClassificationStore;
})(window);
