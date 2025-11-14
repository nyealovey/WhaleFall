(function (global) {
  "use strict";

  const BASE_PATH = "/sync_sessions/api/sessions";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("SyncSessionsService: httpClient 未初始化");
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

  class SyncSessionsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    list(filters) {
      const query = toQueryString(filters);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }

    detail(sessionId) {
      this.assertSessionId(sessionId, "detail");
      return this.httpClient.get(`${BASE_PATH}/${sessionId}`);
    }

    errorLogs(sessionId) {
      this.assertSessionId(sessionId, "errorLogs");
      return this.httpClient.get(`${BASE_PATH}/${sessionId}/error-logs`);
    }

    cancel(sessionId, payload) {
      this.assertSessionId(sessionId, "cancel");
      return this.httpClient.post(`${BASE_PATH}/${sessionId}/cancel`, payload || {});
    }

    assertSessionId(sessionId, action) {
      if (sessionId === undefined || sessionId === null || sessionId === "") {
        throw new Error(`SyncSessionsService: ${action} 需要有效的 sessionId`);
      }
    }
  }

  global.SyncSessionsService = SyncSessionsService;
})(window);

