(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/task-runs";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("TaskRunsService: httpClient 未初始化");
    }
    return resolved;
  }

  function toQueryString(filters) {
    if (!filters) {
      return "";
    }
    if (typeof filters === "string") {
      return filters ? `?${filters.replace(/^\?/, "")}` : "";
    }
    if (filters instanceof URLSearchParams) {
      const serialized = filters.toString();
      return serialized ? `?${serialized}` : "";
    }
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item !== undefined && item !== null && item !== "") {
            params.append(key, item);
          }
        });
      } else {
        params.append(key, value);
      }
    });
    const query = params.toString();
    return query ? `?${query}` : "";
  }

  class TaskRunsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
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
