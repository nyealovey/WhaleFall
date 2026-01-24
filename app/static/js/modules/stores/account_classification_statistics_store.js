(function (window) {
  "use strict";

  const DEFAULT_PERIODS = 7;

  /**
   * @typedef {Object} AccountClassificationStatisticsFilters
   * @property {number|null} classificationId
   * @property {string} periodType
   * @property {string|null} dbType
   * @property {number|null} instanceId
   * @property {number|null} ruleId
   * @property {string} ruleStatus
   */

  /**
   * @typedef {Object} AccountClassificationStatisticsState
   * @property {AccountClassificationStatisticsFilters} filters
   * @property {Array<Object>} instanceOptions
   * @property {Array<Object>} rules
   * @property {Object|null} selectedRuleMeta
   * @property {Object|null} rulesWindow
   * @property {Array<Object>} classificationTrend
   * @property {Object|null} allClassificationsTrend
   * @property {Array<Object>} ruleTrend
   * @property {Object|null} ruleContributions
   * @property {{rules:boolean,charts:boolean,instances:boolean}} loading
   * @property {Error|Object|string|null} lastError
   */

  function ensureService(service) {
    if (!service) {
      throw new Error("createAccountClassificationStatisticsStore: service is required");
    }
    const required = [
      "fetchClassificationTrend",
      "fetchAllClassificationsTrends",
      "fetchRuleTrend",
      "fetchRuleContributions",
      "fetchRulesOverview",
    ];
    required.forEach((method) => {
      if (typeof service[method] !== "function") {
        throw new Error(
          `createAccountClassificationStatisticsStore: service.${method} 未实现`,
        );
      }
    });
    return service;
  }

  function ensureInstanceService(instanceService) {
    if (!instanceService) {
      throw new Error("createAccountClassificationStatisticsStore: instanceService is required");
    }
    if (typeof instanceService.fetchInstanceOptions !== "function") {
      throw new Error(
        "createAccountClassificationStatisticsStore: instanceService.fetchInstanceOptions 未实现",
      );
    }
    return instanceService;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createAccountClassificationStatisticsStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function normalizeInt(value) {
    if (value === undefined || value === null || value === "") {
      return null;
    }
    const parsed = Number.parseInt(String(value), 10);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function normalizeString(value) {
    if (value === undefined || value === null) {
      return null;
    }
    const normalized = String(value).trim();
    return normalized ? normalized : null;
  }

  function normalizePeriodType(value) {
    const normalized = normalizeString(value) || "daily";
    switch (normalized) {
      case "daily":
      case "weekly":
      case "monthly":
      case "quarterly":
        return normalized;
      default:
        return "daily";
    }
  }

  function normalizeRuleStatus(value) {
    const normalized = normalizeString(value) || "active";
    switch (normalized) {
      case "active":
      case "archived":
      case "all":
        return normalized;
      default:
        return "active";
    }
  }

  function resolveSelectedRule(rules, ruleId) {
    const id = normalizeInt(ruleId);
    if (!id) {
      return null;
    }
    const sid = String(id);
    return (rules || []).find((rule) => String(rule?.rule_id) === sid) || null;
  }

  function cloneFilters(filters) {
    return {
      classificationId: filters.classificationId ?? null,
      periodType: filters.periodType || "daily",
      dbType: filters.dbType ?? null,
      instanceId: filters.instanceId ?? null,
      ruleId: filters.ruleId ?? null,
      ruleStatus: filters.ruleStatus || "active",
    };
  }

  function cloneState(state) {
    return {
      filters: cloneFilters(state.filters),
      instanceOptions: Array.isArray(state.instanceOptions) ? state.instanceOptions.slice() : [],
      rules: Array.isArray(state.rules) ? state.rules.slice() : [],
      selectedRuleMeta: state.selectedRuleMeta || null,
      rulesWindow: state.rulesWindow ? { ...state.rulesWindow } : null,
      classificationTrend: Array.isArray(state.classificationTrend) ? state.classificationTrend.slice() : [],
      allClassificationsTrend: state.allClassificationsTrend || null,
      ruleTrend: Array.isArray(state.ruleTrend) ? state.ruleTrend.slice() : [],
      ruleContributions: state.ruleContributions || null,
      loading: { ...state.loading },
      lastError: state.lastError,
    };
  }

  function buildDefaultFilters() {
    return {
      classificationId: null,
      periodType: "daily",
      dbType: null,
      instanceId: null,
      ruleId: null,
      ruleStatus: "active",
    };
  }

  function applyFilters(state, patch) {
    const next = patch && typeof patch === "object" ? patch : {};
    const classificationId = normalizeInt(next.classificationId ?? state.filters.classificationId);
    const ruleIdCandidate = normalizeInt(next.ruleId ?? state.filters.ruleId);
    const filters = {
      classificationId,
      periodType: normalizePeriodType(next.periodType ?? state.filters.periodType),
      dbType: normalizeString(next.dbType ?? state.filters.dbType),
      instanceId: normalizeInt(next.instanceId ?? state.filters.instanceId),
      ruleId: classificationId ? ruleIdCandidate : null,
      ruleStatus: normalizeRuleStatus(next.ruleStatus ?? state.filters.ruleStatus),
    };

    // 切换 dbType 时，默认清空 instanceId（避免残留实例筛选误导）。
    if (Object.prototype.hasOwnProperty.call(next, "dbType")) {
      filters.instanceId = null;
    }
    // 切换 classification 时，默认清空 ruleId（避免跨分类 ruleId 误导）。
    if (Object.prototype.hasOwnProperty.call(next, "classificationId")) {
      filters.ruleId = null;
    }
    state.filters = filters;
    state.selectedRuleMeta = resolveSelectedRule(state.rules, filters.ruleId);
  }

  function createAccountClassificationStatisticsStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const instanceService = ensureInstanceService(opts.instanceService);
    const emitter = ensureEmitter(opts.emitter);

    /** @type {AccountClassificationStatisticsState} */
    const state = {
      filters: buildDefaultFilters(),
      instanceOptions: [],
      rules: [],
      selectedRuleMeta: null,
      rulesWindow: null,
      classificationTrend: [],
      allClassificationsTrend: null,
      ruleTrend: [],
      ruleContributions: null,
      loading: { rules: false, charts: false, instances: false },
      lastError: null,
    };

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? { state: cloneState(state) });
    }

    function handleError(error, meta) {
      state.lastError = error;
      emit("accountClassificationStatistics:error", {
        error,
        meta: meta || {},
        state: cloneState(state),
      });
    }

    function setLoading(key, loading, meta) {
      state.loading[key] = Boolean(loading);
      emit("accountClassificationStatistics:loading", {
        key,
        loading: state.loading[key],
        meta: meta || {},
        state: cloneState(state),
      });
    }

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
      actions: {
        setFilters: function (filters) {
          applyFilters(state, filters);
          emit("accountClassificationStatistics:filtersUpdated", {
            filters: cloneFilters(state.filters),
            state: cloneState(state),
          });
          return cloneFilters(state.filters);
        },
        patchFilters: function (patch) {
          applyFilters(state, patch);
          emit("accountClassificationStatistics:filtersUpdated", {
            filters: cloneFilters(state.filters),
            state: cloneState(state),
          });
          return cloneFilters(state.filters);
        },
        resetFilters: function () {
          state.rules = [];
          state.selectedRuleMeta = null;
          state.rulesWindow = null;
          state.instanceOptions = [];
          state.classificationTrend = [];
          state.allClassificationsTrend = null;
          state.ruleTrend = [];
          state.ruleContributions = null;
          state.lastError = null;
          state.loading = { rules: false, charts: false, instances: false };
          state.filters = buildDefaultFilters();
          emit("accountClassificationStatistics:filtersUpdated", {
            filters: cloneFilters(state.filters),
            state: cloneState(state),
          });
          emit("accountClassificationStatistics:reset", { state: cloneState(state) });
          return cloneFilters(state.filters);
        },
        loadInstanceOptions: function (options) {
          const silent = Boolean(options && options.silent);
          const dbType = state.filters.dbType;
          if (!dbType) {
            state.instanceOptions = [];
            emit("accountClassificationStatistics:instanceOptionsUpdated", {
              options: [],
              state: cloneState(state),
            });
            return Promise.resolve([]);
          }

          setLoading("instances", true, { action: "loadInstanceOptions", silent });
          return instanceService
            .fetchInstanceOptions(dbType)
            .then(function (payload) {
              const items = payload?.data?.instances ?? payload?.instances ?? [];
              const list = Array.isArray(items) ? items : [];
              state.instanceOptions = list;
              emit("accountClassificationStatistics:instanceOptionsUpdated", {
                options: list,
                state: cloneState(state),
              });
              return list;
            })
            .catch(function (error) {
              state.instanceOptions = [];
              handleError(error, { action: "loadInstanceOptions", silent });
              throw error;
            })
            .finally(function () {
              setLoading("instances", false, { action: "loadInstanceOptions", silent });
            });
        },
        refreshRulesList: function (options) {
          const silent = Boolean(options && options.silent);
          const filters = state.filters;
          if (!filters.classificationId) {
            state.rules = [];
            state.selectedRuleMeta = null;
            state.rulesWindow = null;
            emit("accountClassificationStatistics:rulesUpdated", {
              rules: [],
              rulesWindow: null,
              selectedRuleMeta: null,
              state: cloneState(state),
            });
            return Promise.resolve([]);
          }

          setLoading("rules", true, { action: "refreshRulesList", silent });
          return service
            .fetchRulesOverview({
              classificationId: filters.classificationId,
              periodType: filters.periodType,
              periods: DEFAULT_PERIODS,
              dbType: filters.dbType,
              instanceId: filters.instanceId,
              status: filters.ruleStatus,
            })
            .then(function (payload) {
              const data = payload?.data ?? payload ?? {};
              const rules = Array.isArray(data.rules) ? data.rules : data.data?.rules || [];
              const windowStart = data.window_start || data.data?.window_start || null;
              const windowEnd = data.window_end || data.data?.window_end || null;
              const latestStart = data.latest_period_start || data.data?.latest_period_start || null;
              const latestEnd = data.latest_period_end || data.data?.latest_period_end || null;

              const list = Array.isArray(rules) ? rules : [];
              state.rules = list;
              state.selectedRuleMeta = resolveSelectedRule(list, filters.ruleId);
              state.rulesWindow = {
                windowStart,
                windowEnd,
                latestStart,
                latestEnd,
              };

              emit("accountClassificationStatistics:rulesUpdated", {
                rules: list,
                rulesWindow: state.rulesWindow,
                selectedRuleMeta: state.selectedRuleMeta,
                state: cloneState(state),
              });
              return list;
            })
            .catch(function (error) {
              state.rules = [];
              state.selectedRuleMeta = null;
              state.rulesWindow = null;
              handleError(error, { action: "refreshRulesList", silent });
              emit("accountClassificationStatistics:rulesUpdated", {
                rules: [],
                rulesWindow: null,
                selectedRuleMeta: null,
                state: cloneState(state),
              });
              throw error;
            })
            .finally(function () {
              setLoading("rules", false, { action: "refreshRulesList", silent });
            });
        },
        refreshCharts: function (options) {
          const silent = Boolean(options && options.silent);
          const filters = state.filters;
          setLoading("charts", true, { action: "refreshCharts", silent });

          if (!filters.classificationId) {
            state.classificationTrend = [];
            state.ruleTrend = [];
            state.ruleContributions = null;
            return service
              .fetchAllClassificationsTrends({
                periodType: filters.periodType,
                periods: DEFAULT_PERIODS,
                dbType: filters.dbType,
                instanceId: filters.instanceId,
              })
              .then(function (payload) {
                const data = payload?.data ?? payload ?? {};
                state.allClassificationsTrend = data;
                emit("accountClassificationStatistics:allClassificationsTrendUpdated", {
                  payload: data,
                  state: cloneState(state),
                });
                emit("accountClassificationStatistics:chartsUpdated", { state: cloneState(state) });
                return data;
              })
              .catch(function (error) {
                state.allClassificationsTrend = null;
                handleError(error, { action: "refreshCharts", silent });
                throw error;
              })
              .finally(function () {
                setLoading("charts", false, { action: "refreshCharts", silent });
              });
          }

          state.allClassificationsTrend = null;
          return service
            .fetchClassificationTrend({
              classificationId: filters.classificationId,
              periodType: filters.periodType,
              periods: DEFAULT_PERIODS,
              dbType: filters.dbType,
              instanceId: filters.instanceId,
            })
            .then(function (payload) {
              const trend = payload?.data?.trend ?? payload?.trend ?? [];
              state.classificationTrend = Array.isArray(trend) ? trend : [];
              emit("accountClassificationStatistics:classificationTrendUpdated", {
                trend: state.classificationTrend.slice(),
                state: cloneState(state),
              });
            })
            .then(function () {
              if (filters.ruleId) {
                return service
                  .fetchRuleTrend({
                    ruleId: filters.ruleId,
                    periodType: filters.periodType,
                    periods: DEFAULT_PERIODS,
                    dbType: filters.dbType,
                    instanceId: filters.instanceId,
                  })
                  .then(function (payload) {
                    const trend = payload?.data?.trend ?? payload?.trend ?? [];
                    state.ruleTrend = Array.isArray(trend) ? trend : [];
                    state.ruleContributions = null;
                    emit("accountClassificationStatistics:ruleTrendUpdated", {
                      trend: state.ruleTrend.slice(),
                      state: cloneState(state),
                    });
                  });
              }
              return service
                .fetchRuleContributions({
                  classificationId: filters.classificationId,
                  periodType: filters.periodType,
                  dbType: filters.dbType,
                  instanceId: filters.instanceId,
                  limit: 10,
                })
                .then(function (payload) {
                  const data = payload?.data ?? payload ?? {};
                  state.ruleTrend = [];
                  state.ruleContributions = data;
                  emit("accountClassificationStatistics:ruleContributionsUpdated", {
                    payload: data,
                    state: cloneState(state),
                  });
                });
            })
            .then(function () {
              emit("accountClassificationStatistics:chartsUpdated", { state: cloneState(state) });
            })
            .catch(function (error) {
              handleError(error, { action: "refreshCharts", silent });
              throw error;
            })
            .finally(function () {
              setLoading("charts", false, { action: "refreshCharts", silent });
            });
        },
        refreshAll: function (options) {
          const silent = Boolean(options && options.silent);
          return api.actions
            .refreshRulesList({ silent: true })
            .then(function () {
              return api.actions.refreshCharts({ silent });
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.rules = [];
        state.instanceOptions = [];
        state.classificationTrend = [];
        state.allClassificationsTrend = null;
        state.ruleTrend = [];
        state.ruleContributions = null;
        state.selectedRuleMeta = null;
        state.rulesWindow = null;
        state.lastError = null;
      },
    };

    return api;
  }

  window.createAccountClassificationStatisticsStore = createAccountClassificationStatisticsStore;
})(window);

