(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/scheduler";

  /**
   * 统一选择 http 客户端。
   *
   * @param {Object} client - HTTP 客户端实例
   * @return {Object} HTTP 客户端实例
   * @throws {Error} 当客户端未初始化时抛出
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
   *
   * @param {number|string} jobId - 任务 ID
   * @param {string} action - 操作名称
   * @returns {void}
   * @throws {Error} 当 jobId 无效时抛出
   */
  function assertJobId(jobId, action) {
    if (jobId === undefined || jobId === null || jobId === "") {
      throw new Error(`SchedulerService: ${action} 需要有效的 jobId`);
    }
  }

  /**
   * 定时任务管理服务。
   *
   * 提供定时任务的查询、启动、暂停、更新、删除等功能。
   *
   * @class
   */
  class SchedulerService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     */
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    /**
     * 获取任务列表。
     *
     * @return {Promise<Object>} 任务列表响应
     */
    listJobs() {
      return this.httpClient.get(`${BASE_PATH}/jobs`);
    }

    /**
     * 重新加载所有任务。
     *
     * @return {Promise<Object>} 重新加载结果响应
     */
    reloadJobs() {
      return this.httpClient.post(`${BASE_PATH}/jobs/reload`, {});
    }

    /**
     * 恢复任务。
     *
     * @param {number|string} jobId - 任务 ID
     * @return {Promise<Object>} 操作结果响应
     * @throws {Error} 当 jobId 无效时抛出
     */
    resumeJob(jobId) {
      assertJobId(jobId, "resumeJob");
      return this.httpClient.post(`${BASE_PATH}/jobs/${jobId}/resume`);
    }

    /**
     * 暂停任务。
     *
     * @param {number|string} jobId - 任务 ID
     * @return {Promise<Object>} 操作结果响应
     * @throws {Error} 当 jobId 无效时抛出
     */
    pauseJob(jobId) {
      assertJobId(jobId, "pauseJob");
      return this.httpClient.post(`${BASE_PATH}/jobs/${jobId}/pause`);
    }

    /**
     * 立即执行任务。
     *
     * @param {number|string} jobId - 任务 ID
     * @return {Promise<Object>} 操作结果响应
     * @throws {Error} 当 jobId 无效时抛出
     */
    runJob(jobId) {
      assertJobId(jobId, "runJob");
      return this.httpClient.post(`${BASE_PATH}/jobs/${jobId}/run`);
    }

    /**
     * 更新任务配置。
     *
     * @param {number|string} jobId - 任务 ID
     * @param {Object} payload - 更新数据
     * @return {Promise<Object>} 操作结果响应
     * @throws {Error} 当 jobId 无效时抛出
     */
    updateJob(jobId, payload) {
      assertJobId(jobId, "updateJob");
      return this.httpClient.put(`${BASE_PATH}/jobs/${jobId}`, payload);
    }

    deleteJob(jobId) {
      assertJobId(jobId, "deleteJob");
      return this.httpClient.delete(`${BASE_PATH}/jobs/${jobId}`);
    }

  }

  global.SchedulerService = SchedulerService;
})(window);
