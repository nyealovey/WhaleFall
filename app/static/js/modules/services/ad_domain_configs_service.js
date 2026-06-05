(function initAdDomainConfigsService(global) {
  "use strict";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("AdDomainConfigsService: ServiceUtils 未初始化");
  }

  class AdDomainConfigsService {
    constructor(apiUrl, credentialsApiUrl, httpClient) {
      this.apiUrl = apiUrl;
      this.credentialsApiUrl = credentialsApiUrl;
      this.httpClient = ensureHttpClient(httpClient, "AdDomainConfigsService");
    }

    async loadConfigs() {
      return this.httpClient.get(this.apiUrl, {
        headers: { Accept: "application/json" },
      });
    }

    async loadLdapCredentials() {
      const params = new URLSearchParams({
        credential_type: "ldap",
        status: "active",
        limit: "200",
      });
      return this.httpClient.get(this.credentialsApiUrl, {
        params,
        headers: { Accept: "application/json" },
      });
    }

    async createConfig(payload) {
      return this.httpClient.post(this.apiUrl, payload, {
        headers: { Accept: "application/json" },
      });
    }

    async updateConfig(configId, payload) {
      return this.httpClient.put(`${this.apiUrl}/${configId}`, payload, {
        headers: { Accept: "application/json" },
      });
    }

    async deleteConfig(configId) {
      return this.httpClient.delete(`${this.apiUrl}/${configId}`, {
        headers: { Accept: "application/json" },
      });
    }

    async setEnabled(configId, enabled) {
      return this.httpClient.post(`${this.apiUrl}/${configId}/actions/set-enabled`, { is_enabled: enabled }, {
        headers: { Accept: "application/json" },
      });
    }

    async testConnection(configId) {
      return this.httpClient.post(`${this.apiUrl}/${configId}/actions/test-connection`, {}, {
        headers: { Accept: "application/json" },
      });
    }

    async syncAccounts() {
      return this.httpClient.post(`${this.apiUrl}/actions/sync`, {}, {
        headers: { Accept: "application/json" },
      });
    }
  }

  global.AdDomainConfigsService = AdDomainConfigsService;
})(window);
