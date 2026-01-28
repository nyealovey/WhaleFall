(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/task-runs";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("TaskRunsService: ServiceUtils 未初始化");
  }

  class TaskRunsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "TaskRunsService");
    }

    list(filters) {
      const query = toQueryString(filters);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }

    getGridUrl() {
      const params = new URLSearchParams();
      params.set("sort", "started_at");
      params.set("order", "desc");
      return `${BASE_PATH}?${params.toString()}`;
    }

    detail(runId) {
      this.assertRunId(runId, "detail");
      return this.httpClient.get(`${BASE_PATH}/${runId}`);
    }

    errorLogs(runId) {
      this.assertRunId(runId, "errorLogs");
      return this.httpClient.get(`${BASE_PATH}/${runId}/error-logs`);
    }

    cancel(runId, payload) {
      this.assertRunId(runId, "cancel");
      return this.httpClient.post(`${BASE_PATH}/${runId}/actions/cancel`, payload || {});
    }

    assertRunId(runId, action) {
      if (runId === undefined || runId === null || runId === "") {
        throw new Error(`TaskRunsService: ${action} 需要有效的 runId`);
      }
    }
  }

  global.TaskRunsService = TaskRunsService;
})(window);
