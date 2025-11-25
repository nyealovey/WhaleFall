(function (window) {
  "use strict";

  /**
   * 校验 service 提供 store 运行所需的方法。
   *
   * @param {Object} service - 服务对象
   * @param {Function} service.listClassifications - 获取分类列表的方法
   * @param {Function} service.createClassification - 创建分类的方法
   * @param {Function} service.updateClassification - 更新分类的方法
   * @param {Function} service.deleteClassification - 删除分类的方法
   * @param {Function} service.listRules - 获取规则列表的方法
   * @param {Function} service.createRule - 创建规则的方法
   * @param {Function} service.updateRule - 更新规则的方法
   * @param {Function} service.deleteRule - 删除规则的方法
   * @param {Function} service.ruleStats - 获取规则统计的方法
   * @param {Function} service.triggerAutomation - 触发自动化的方法
   * @param {Function} service.fetchPermissions - 获取权限列表的方法
   * @return {Object} 校验后的服务对象
   * @throws {Error} 当 service 为空或缺少必需方法时抛出
   */
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

  /**
   * 统一获得 mitt 事件总线。
   *
   * @param {Object} [emitter] - 可选的 mitt 实例
   * @return {Object} mitt 事件总线实例
   * @throws {Error} 当 emitter 为空且 window.mitt 不存在时抛出
   */
  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createAccountClassificationStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  /**
   * 深拷贝分类数组。
   *
   * @param {Array} items - 分类数组
   * @return {Array} 分类数组的拷贝
   */
  function cloneClassifications(items) {
    return (items || []).map(function (classification) {
      return Object.assign({}, classification);
    });
  }

  /**
   * 深拷贝规则字典。
   *
   * @param {Object} source - 规则字典对象
   * @return {Object} 规则字典的拷贝
   */
  function cloneRulesMap(source) {
    const result = {};
    Object.keys(source || {}).forEach(function (key) {
      result[key] = (source[key] || []).map(function (rule) {
        return Object.assign({}, rule);
      });
    });
    return result;
  }

  /**
   * 构造 state 快照，供事件附带。
   *
   * @param {Object} state - 状态对象
   * @return {Object} 状态对象的拷贝
   */
  function cloneState(state) {
    return {
      classifications: cloneClassifications(state.classifications),
      rulesByDbType: cloneRulesMap(state.rulesByDbType),
      permissionsByDbType: Object.assign({}, state.permissionsByDbType),
      loading: Object.assign({}, state.loading),
      lastError: state.lastError,
    };
  }

  /**
   * 保证返回数组。
   *
   * @param {*} value - 任意值
   * @return {Array} 数组
   */
  function ensureArray(value) {
    return Array.isArray(value) ? value : [];
  }

  /**
   * 从响应中提取分类数组。
   *
   * @param {Object} response - API 响应对象
   * @return {Array} 分类数组
   */
  function extractClassifications(response) {
    const collection =
      response?.data?.classifications ?? response?.classifications ?? [];
    return ensureArray(collection);
  }

  /**
   * 从响应提取规则 map。
   *
   * @param {Object} response - API 响应对象
   * @return {Object} 规则字典对象
   */
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

  /**
   * 汇总所有规则 ID，便于请求统计。
   *
   * @param {Object} rulesByDbType - 按数据库类型分组的规则字典
   * @return {Array} 规则 ID 数组
   */
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

  /**
   * 创建账户分类状态管理 Store。
   *
   * 提供账户分类和规则的查询、创建、更新、删除等功能的状态管理。
   *
   * @param {Object} options - 配置选项
   * @param {Object} options.service - 账户分类服务对象
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @return {Object} Store API 对象
   *
   * @example
   * const store = createAccountClassificationStore({
   *   service: accountClassificationService
   * });
   * store.init().then(() => {
   *   console.log(store.getState());
   * });
   */
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
