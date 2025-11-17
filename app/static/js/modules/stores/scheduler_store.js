(function (window) {
  "use strict";

  const ACTIVE_STATES = ["STATE_RUNNING", "STATE_EXECUTING"];

  function ensureService(service) {
    if (!service) {
      throw new Error("createSchedulerStore: service is required");
    }
    [
      "listJobs",
      "reloadJobs",
      "resumeJob",
      "pauseJob",
      "runJob",
      "updateJob",
      "deleteJob",
      "createJobByFunction",
    ].forEach(function (method) {
      if (typeof service[method] !== "function") {
        throw new Error("createSchedulerStore: service." + method + " 未实现");
      }
    });
    return service;
  }

  function ensureEmitter(emitter) {
    if (emitter) {
      return emitter;
    }
    if (!window.mitt) {
      throw new Error("createSchedulerStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  function ensureSuccess(response, fallbackMessage) {
    if (!response || response.success === false) {
      const error = new Error(response?.message || fallbackMessage || "操作失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  function cloneJobs(jobs) {
    return (jobs || []).map(function (job) {
      return Object.assign({}, job);
    });
  }

  function computeStats(jobs) {
    const stats = { active: 0, paused: 0 };
    (jobs || []).forEach(function (job) {
      if (ACTIVE_STATES.includes(job.state)) {
        stats.active += 1;
      } else {
        stats.paused += 1;
      }
    });
    return stats;
  }

  function createSchedulerStore(options) {
    const opts = options || {};
    const service = ensureService(opts.service);
    const emitter = ensureEmitter(opts.emitter);

    const state = {
      jobs: [],
      stats: { active: 0, paused: 0 },
      loading: {
        jobs: false,
      },
      lastError: null,
    };

    function cloneState() {
      return {
        jobs: cloneJobs(state.jobs),
        stats: Object.assign({}, state.stats),
        loading: Object.assign({}, state.loading),
        lastError: state.lastError,
      };
    }

    function emit(eventName, payload) {
      emitter.emit(eventName, payload ?? cloneState());
    }

    function handleError(error, target) {
      state.lastError = error;
      emit("scheduler:error", {
        error,
        target,
        state: cloneState(),
      });
    }

    function setJobs(jobs) {
      state.jobs = cloneJobs(Array.isArray(jobs) ? jobs : []);
      state.stats = computeStats(state.jobs);
    }

    function refreshJobs(options) {
      return api.actions.loadJobs(Object.assign({ silent: true }, options));
    }

    const api = {
      init: function () {
        return api.actions.loadJobs();
      },
      getState: function () {
        return cloneState();
      },
      subscribe: function (eventName, handler) {
        emitter.on(eventName, handler);
      },
      unsubscribe: function (eventName, handler) {
        emitter.off(eventName, handler);
      },
      actions: {
        loadJobs: function (options) {
          const silent = Boolean(options && options.silent);
          if (!silent) {
            state.loading.jobs = true;
            emit("scheduler:loading", { target: "jobs", state: cloneState() });
          }
          return service
            .listJobs()
            .then(function (response) {
              const result = ensureSuccess(response, "加载任务列表失败");
              const jobs = Array.isArray(result.data) ? result.data : [];
              setJobs(jobs);
              state.lastError = null;
              emit("scheduler:updated", {
                jobs: cloneJobs(state.jobs),
                stats: Object.assign({}, state.stats),
                state: cloneState(),
              });
              return cloneState();
            })
            .catch(function (error) {
              handleError(error, "jobs");
              throw error;
            })
            .finally(function () {
              state.loading.jobs = false;
            });
        },
        reloadJobs: function () {
          return service
            .reloadJobs()
            .then(function (response) {
              const result = ensureSuccess(response, "重新初始化任务失败");
              return refreshJobs().then(function () {
                return result;
              });
            })
            .catch(function (error) {
              handleError(error, "reload");
              throw error;
            });
        },
        resumeJob: function (jobId) {
          return service
            .resumeJob(jobId)
            .then(function (response) {
              ensureSuccess(response, "启用任务失败");
              return refreshJobs();
            })
            .catch(function (error) {
              handleError(error, "resume");
              throw error;
            });
        },
        pauseJob: function (jobId) {
          return service
            .pauseJob(jobId)
            .then(function (response) {
              ensureSuccess(response, "暂停任务失败");
              return refreshJobs();
            })
            .catch(function (error) {
              handleError(error, "pause");
              throw error;
            });
        },
        runJob: function (jobId) {
          return service
            .runJob(jobId)
            .then(function (response) {
              ensureSuccess(response, "执行任务失败");
              return refreshJobs();
            })
            .catch(function (error) {
              handleError(error, "run");
              throw error;
            });
        },
        updateJob: function (jobId, payload) {
          return service
            .updateJob(jobId, payload)
            .then(function (response) {
              ensureSuccess(response, "更新任务失败");
              return refreshJobs();
            })
            .catch(function (error) {
              handleError(error, "update");
              throw error;
            });
        },
        deleteJob: function (jobId) {
          return service
            .deleteJob(jobId)
            .then(function (response) {
              ensureSuccess(response, "删除任务失败");
              return refreshJobs();
            })
            .catch(function (error) {
              handleError(error, "delete");
              throw error;
            });
        },
        createJob: function (payload) {
          return service
            .createJobByFunction(payload)
            .then(function (response) {
              ensureSuccess(response, "新增任务失败");
              return refreshJobs();
            })
            .catch(function (error) {
              handleError(error, "create");
              throw error;
            });
        },
      },
      destroy: function () {
        if (emitter.all && typeof emitter.all.clear === "function") {
          emitter.all.clear();
        }
        state.jobs = [];
      },
    };

    return api;
  }

  window.createSchedulerStore = createSchedulerStore;
})(window);
