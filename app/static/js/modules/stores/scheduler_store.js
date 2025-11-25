(function (window) {
  "use strict";

  const ACTIVE_STATES = ["STATE_RUNNING", "STATE_EXECUTING"];

  /**
   * 校验服务对象是否实现所有 scheduler 相关 API。
   *
   * @param {Object} service - 服务对象
   * @param {Function} service.listJobs - 获取任务列表的方法
   * @param {Function} service.reloadJobs - 重新加载任务的方法
   * @param {Function} service.resumeJob - 恢复任务的方法
   * @param {Function} service.pauseJob - 暂停任务的方法
   * @param {Function} service.runJob - 执行任务的方法
   * @param {Function} service.updateJob - 更新任务的方法
   * @param {Function} service.deleteJob - 删除任务的方法
   * @param {Function} service.createJobByFunction - 创建任务的方法
   * @return {Object} 校验后的服务对象
   * @throws {Error} 当 service 为空或缺少必需方法时抛出
   */
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

  /**
   * 获取 mitt 事件总线。
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
      throw new Error("createSchedulerStore: 需要 mitt 实例");
    }
    return window.mitt();
  }

  /**
   * 后端 success=false 时抛错。
   *
   * @param {Object} response - API 响应对象
   * @param {string} fallbackMessage - 回退错误消息
   * @return {Object} 响应对象
   * @throws {Error} 当响应失败时抛出
   */
  function ensureSuccess(response, fallbackMessage) {
    if (!response || response.success === false) {
      const error = new Error(response?.message || fallbackMessage || "操作失败");
      error.raw = response;
      throw error;
    }
    return response;
  }

  /**
   * 深拷贝任务列表。
   *
   * @param {Array} jobs - 任务数组
   * @return {Array} 任务数组的拷贝
   */
  function cloneJobs(jobs) {
    return (jobs || []).map(function (job) {
      return Object.assign({}, job);
    });
  }

  /**
   * 统计当前运行/暂停数量。
   *
   * @param {Array} jobs - 任务数组
   * @return {Object} 统计对象，包含 active 和 paused 数量
   */
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

  /**
   * 创建调度器状态管理 Store。
   *
   * 提供定时任务的查询、启动、暂停、更新、删除等功能的状态管理。
   *
   * @param {Object} options - 配置选项
   * @param {Object} options.service - 调度器服务对象
   * @param {Object} [options.emitter] - 可选的 mitt 事件总线实例
   * @return {Object} Store API 对象
   *
   * @example
   * const store = createSchedulerStore({
   *   service: schedulerService
   * });
   * store.init().then(() => {
   *   console.log(store.getState());
   * });
   */
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
