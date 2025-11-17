(function (window) {
  "use strict";

  const DEFAULT_PER_PAGE = 20;
  const DEFAULT_AUTO_REFRESH_INTERVAL = 30000;

  function ensureService(service) {
    if (!service) {
      throw new Error("createSyncSessionsStore: service is required");
    }
    ["list", "detail", "errorLogs", "cancel"].forEach(function (method) {
      if (typeof service[method] !== "function") {
        throw new Error("createSyncSessionsStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createSyncSessionsStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function cloneState(state) {
    return {
      sessions: state.sessions.slice(),
      filters: Object.assign({}, state.filters),
      pagination: Object.assign({}, state.pagination),
      loading: state.loading,
      lastError: state.lastError,
      selectedSession: state.selectedSession,
      errorLogs: state.errorLogs.slice(),
      autoRefresh: Object.assign({}, state.autoRefresh),
    };
  }

  function normalizePagination(data, fallback) {
    const source = data || {};
    const base = fallback || {};
    const page = Number(source.page ?? source.current_page ?? base.page ?? 1);
    const pages = Number(source.pages ?? source.total_pages ?? base.pages ?? 1);
    const perPage = Number(source.per_page ?? source.perPage ?? base.perPage ?? DEFAULT_PER_PAGE);
    const totalItems = Number(
      source.total ?? source.total_items ?? source.totalItems ?? base.totalItems ?? 0
    );
    const hasNext =
      source.has_next ??
      source.has_more ??
      (pages ? page < pages : base.hasNext ?? false);
    const hasPrev =
      source.has_prev ??
      source.has_previous ??
      (page > 1 ? true : base.hasPrev ?? false);
    const prevPage = Number(
      source.prev_num ?? source.previous_page ?? base.prevPage ?? (hasPrev ? page - 1 : 1)
    );
    const nextPage = Number(
      source.next_num ?? source.next_page ?? base.nextPage ?? (hasNext ? page + 1 : page)
    );

    return {
      page: page > 0 ? page : 1,
      pages: pages > 0 ? pages : 1,
      perPage: perPage > 0 ? perPage : DEFAULT_PER_PAGE,
      totalItems: totalItems >= 0 ? totalItems : 0,
      hasNext: Boolean(hasNext),
      hasPrev: Boolean(hasPrev),
      prevPage: prevPage > 0 ? prevPage : 1,
      nextPage: nextPage > 0 ? nextPage : 1,
    };
  }

  function extractSessions(response) {
    if (!response) {
      return [];
    }
    const payload = response.data ?? response;
    const list = payload.sessions ?? payload.items ?? payload;
    if (!Array.isArray(list)) {
      return [];
    }
    return list;
  }

  function resolvePagination(response, fallback) {
    const payload = response?.data ?? response ?? {};
    const pagination = payload.pagination ?? response?.pagination ?? null;
    return normalizePagination(pagination, fallback);
  }

  function createSyncSessionsStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);
    const autoRefreshInterval =
      Number(opts.autoRefreshInterval) > 0
        ? Number(opts.autoRefreshInterval)
        : DEFAULT_AUTO_REFRESH_INTERVAL;

    const state = {
      sessions: [],
      filters: Object.assign({}, opts.initialFilters || {}),
      pagination: {
        page: 1,
        pages: 1,
        perPage: opts.perPage || DEFAULT_PER_PAGE,
        totalItems: 0,
        hasNext: false,
        hasPrev: false,
        prevPage: 1,
        nextPage: 1,
      },
      loading: false,
      lastError: null,
      selectedSession: null,
      errorLogs: [],
      autoRefresh: {
        enabled: opts.autoRefresh !== false,
        interval: autoRefreshInterval,
      },
    };

    let autoRefreshTimer = null;

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? cloneState(state));
    }

    function scheduleAutoRefresh() {
      clearAutoRefresh();
      if (!state.autoRefresh.enabled) {
        return;
      }
      autoRefreshTimer = setInterval(function () {
        api.actions.loadSessions({ silent: true });
      }, state.autoRefresh.interval);
    }

    function clearAutoRefresh() {
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
      }
    }

    function applyListResponse(response) {
      state.sessions = extractSessions(response);
      state.pagination = resolvePagination(response, {
        page: state.pagination.page,
        pages: state.pagination.pages,
        perPage: state.pagination.perPage,
        totalItems: state.sessions.length,
        hasNext: false,
        hasPrev: state.pagination.page > 1,
        prevPage: Math.max(1, state.pagination.page - 1),
        nextPage: state.pagination.page + 1,
      });
    }

    function handleRequestFailure(error) {
      state.lastError = error;
      emit("syncSessions:error", { error: error, state: cloneState(state) });
    }

    const debugEnabled = window.DEBUG_SYNC_SESSIONS ?? false;
    function debugLog(message, payload) {
      if (!debugEnabled) {
        return;
      }
      const prefix = "[SyncSessionsStore]";
      if (payload !== undefined) {
        console.debug(`${prefix} ${message}`, payload);
      } else {
        console.debug(`${prefix} ${message}`);
      }
    }

    const api = {
      init: function (initialFilters) {
        if (initialFilters && typeof initialFilters === "object") {
          state.filters = Object.assign({}, initialFilters);
        }
        if (state.autoRefresh.enabled) {
          scheduleAutoRefresh();
        }
        debugLog("init 调用，开始首次加载", { filters: state.filters });
        return api.actions.loadSessions({ page: 1 });
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
      actions: {
        loadSessions: function (options) {
          const opts = options || {};
          const silent = Boolean(opts.silent);
          const incomingFilters = opts.filters;
          const requestedPage = Number(opts.page);
          let page =
            Number.isFinite(requestedPage) && requestedPage > 0 ? requestedPage : state.pagination.page || 1;

          if (incomingFilters && typeof incomingFilters === "object") {
            state.filters = Object.assign({}, incomingFilters);
            page = 1;
          }

          if (!silent) {
            state.loading = true;
            emit("syncSessions:loading", cloneState(state));
          }

          state.pagination.page = page;

          const query = Object.assign({}, state.filters, {
            page: page,
            per_page: state.pagination.perPage,
          });

          debugLog("loadSessions 请求会话列表", { query, silent });

          return service
            .list(query)
            .then(function (response) {
              debugLog("loadSessions 返回数据", {
                hasSessions: Array.isArray(response?.data?.sessions),
                sessionCount: Array.isArray(response?.data?.sessions) ? response.data.sessions.length : null,
                pagination: response?.data?.pagination || response?.pagination,
              });
              if (!response || response.success === false) {
                const error = new Error(response?.message || "加载会话列表失败");
                error.raw = response;
                throw error;
              }
              applyListResponse(response);
              state.lastError = null;
              emit("syncSessions:updated", cloneState(state));
              return cloneState(state);
            })
            .catch(function (error) {
              debugLog("loadSessions 请求失败", error);
              handleRequestFailure(error);
              throw error;
            })
            .finally(function () {
              debugLog("loadSessions 完成", { page: state.pagination.page, total: state.pagination.totalItems });
              state.loading = false;
            });
        },
        applyFilters: function (filters, options) {
          const nextFilters = filters && typeof filters === "object" ? filters : {};
          state.filters = Object.assign({}, nextFilters);
          state.pagination.page = 1;
          return api.actions.loadSessions({ silent: options?.silent });
        },
        resetFilters: function (options) {
          state.filters = {};
          state.pagination.page = 1;
          return api.actions.loadSessions({ silent: options?.silent });
        },
        changePage: function (page, options) {
          let nextPage = Number(page);
          if (!Number.isFinite(nextPage) || nextPage < 1) {
            nextPage = 1;
          }
          return api.actions.loadSessions({
            page: nextPage,
            silent: options?.silent,
          });
        },
        reloadCurrentPage: function (options) {
          return api.actions.loadSessions({
            page: state.pagination.page,
            silent: options?.silent,
          });
        },
        loadSessionDetail: function (sessionId) {
          if (!sessionId) {
            return Promise.reject(new Error("SyncSessionsStore: 需要 sessionId"));
          }
          return service
            .detail(sessionId)
            .then(function (response) {
              if (!response || response.success === false) {
                const error = new Error(response?.message || "加载会话详情失败");
                error.raw = response;
                throw error;
              }
              const session = response?.data?.session ?? response?.data ?? response ?? {};
              state.selectedSession = session;
              emit("syncSessions:detailLoaded", {
                session: session,
                state: cloneState(state),
              });
              return session;
            })
            .catch(function (error) {
              handleRequestFailure(error);
              throw error;
            });
        },
        loadErrorLogs: function (sessionId) {
          if (!sessionId) {
            return Promise.reject(new Error("SyncSessionsStore: 需要 sessionId"));
          }
          return service
            .errorLogs(sessionId)
            .then(function (response) {
              if (!response || response.success === false) {
                const error = new Error(response?.message || "加载错误日志失败");
                error.raw = response;
                throw error;
              }
              const payload = response?.data ?? response ?? {};
              const records = Array.isArray(payload.error_records)
                ? payload.error_records
                : [];
              state.errorLogs = records;
              emit("syncSessions:errorLogsLoaded", {
                errorRecords: records,
                state: cloneState(state),
              });
              return records;
            })
            .catch(function (error) {
              handleRequestFailure(error);
              throw error;
            });
        },
        cancelSession: function (sessionId) {
          if (!sessionId) {
            return Promise.reject(new Error("SyncSessionsStore: 需要 sessionId"));
          }
          return service
            .cancel(sessionId)
            .then(function (response) {
              if (!response || response.success === false) {
                const error = new Error(response?.message || "取消会话失败");
                error.raw = response;
                throw error;
              }
              emit("syncSessions:sessionCancelled", {
                sessionId: sessionId,
                state: cloneState(state),
              });
              return api.actions.reloadCurrentPage({ silent: true });
            })
            .catch(function (error) {
              handleRequestFailure(error);
              throw error;
            });
        },
        enableAutoRefresh: function () {
          state.autoRefresh.enabled = true;
          scheduleAutoRefresh();
          emit("syncSessions:autoRefreshUpdated", cloneState(state));
        },
        disableAutoRefresh: function () {
          state.autoRefresh.enabled = false;
          clearAutoRefresh();
          emit("syncSessions:autoRefreshUpdated", cloneState(state));
        },
        setAutoRefreshInterval: function (intervalMs) {
          const interval = Number(intervalMs);
          if (!Number.isFinite(interval) || interval <= 0) {
            return;
          }
          state.autoRefresh.interval = interval;
          if (state.autoRefresh.enabled) {
            scheduleAutoRefresh();
          }
          emit("syncSessions:autoRefreshUpdated", cloneState(state));
        },
      },
      destroy: function () {
        clearAutoRefresh();
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.sessions = [];
      },
    };

    return api;
  }

  window.createSyncSessionsStore = createSyncSessionsStore;
})(window);
