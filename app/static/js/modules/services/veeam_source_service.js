(function initVeeamSourceService(global) {
  "use strict";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("VeeamSourceService: ServiceUtils 未初始化");
  }

  class VeeamSourceService {
    constructor(apiUrl, syncApiUrl, sourcesApiUrl, httpClient) {
      this.apiUrl = apiUrl;
      this.syncApiUrl = syncApiUrl;
      this.sourcesApiUrl = sourcesApiUrl || apiUrl.replace(/\/source$/, "/sources");
      this.httpClient = ensureHttpClient(httpClient, "VeeamSourceService");
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

    async createSource(payload) {
      return this.httpClient.post(this.sourcesApiUrl, payload, {
        headers: { Accept: "application/json" },
      });
    }

    async updateSource(sourceId, payload) {
      return this.httpClient.put(`${this.sourcesApiUrl}/${sourceId}`, payload, {
        headers: { Accept: "application/json" },
      });
    }

    async deleteSource(sourceId) {
      return this.httpClient.delete(`${this.sourcesApiUrl}/${sourceId}`, {
        headers: { Accept: "application/json" },
      });
    }

    async setSourceEnabled(sourceId, enabled) {
      const action = enabled ? "enable" : "disable";
      return this.httpClient.post(`${this.sourcesApiUrl}/${sourceId}/actions/${action}`, {}, {
        headers: { Accept: "application/json" },
      });
    }

    async deleteBinding() {
      return this.httpClient.delete(this.apiUrl, {
        headers: { Accept: "application/json" },
      });
    }

    async syncBackups() {
      return this.httpClient.post(this.syncApiUrl, {}, {
        headers: { Accept: "application/json" },
      });
    }
  }

  global.VeeamSourceService = VeeamSourceService;
})(window);
