(function initJumpServerSourceService(global) {
  "use strict";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("JumpServerSourceService: ServiceUtils 未初始化");
  }

  class JumpServerSourceService {
    constructor(apiUrl, syncApiUrl, httpClient) {
      this.apiUrl = apiUrl;
      this.syncApiUrl = syncApiUrl;
      this.httpClient = ensureHttpClient(httpClient, "JumpServerSourceService");
    }

    async load() {
      return this.httpClient.get(this.apiUrl, {
        headers: { Accept: "application/json" },
      });
    }

    async updateBinding(payload) {
      return this.httpClient.put(this.apiUrl, payload, {
        headers: { Accept: "application/json" },
      });
    }

    async deleteBinding() {
      return this.httpClient.delete(this.apiUrl, {
        headers: { Accept: "application/json" },
      });
    }

    async syncAssets() {
      return this.httpClient.post(this.syncApiUrl, {}, {
        headers: { Accept: "application/json" },
      });
    }
  }

  global.JumpServerSourceService = JumpServerSourceService;
})(window);
