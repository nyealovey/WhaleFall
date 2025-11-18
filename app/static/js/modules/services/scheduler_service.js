(function (global) {
  "use strict";

  const BASE_PATH = "/scheduler/api";

  /**
   * 统一选择 http 客户端。
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("SchedulerService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 校验 jobId 是否有效。
   */
  function assertJobId(jobId, action) {
    if (jobId === undefined || jobId === null || jobId === "") {
      throw new Error(`SchedulerService: ${action} 需要有效的 jobId`);
    }
  }

  /**
   * 定时任务管理服务。
   */
  class SchedulerService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    listJobs() {
      return this.httpClient.get(`${BASE_PATH}/jobs`);
    }

    reloadJobs() {
      return this.httpClient.post(`${BASE_PATH}/jobs/reload`, {});
    }

    resumeJob(jobId) {
      assertJobId(jobId, "resumeJob");
      return this.httpClient.post(`${BASE_PATH}/jobs/${jobId}/resume`);
    }

    pauseJob(jobId) {
      assertJobId(jobId, "pauseJob");
      return this.httpClient.post(`${BASE_PATH}/jobs/${jobId}/pause`);
    }

    runJob(jobId) {
      assertJobId(jobId, "runJob");
      return this.httpClient.post(`${BASE_PATH}/jobs/${jobId}/run`);
    }

    updateJob(jobId, payload) {
      assertJobId(jobId, "updateJob");
      return this.httpClient.put(`${BASE_PATH}/jobs/${jobId}`, payload);
    }

    deleteJob(jobId) {
      assertJobId(jobId, "deleteJob");
      return this.httpClient.delete(`${BASE_PATH}/jobs/${jobId}`);
    }

    createJobByFunction(payload) {
      return this.httpClient.post(`${BASE_PATH}/jobs/by-func`, payload);
    }
  }

  global.SchedulerService = SchedulerService;
})(window);
