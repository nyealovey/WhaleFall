(function initAdDomainConfigsService(global) {
  "use strict";

  class AdDomainConfigsService {
    constructor(apiUrl, credentialsApiUrl) {
      this.apiUrl = apiUrl;
      this.credentialsApiUrl = credentialsApiUrl;
    }

    async loadConfigs() {
      const response = await fetch(this.apiUrl, {
        method: "GET",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      return response.json();
    }

    async loadLdapCredentials() {
      const params = new URLSearchParams({
        credential_type: "ldap",
        status: "active",
        limit: "200",
      });
      const response = await fetch(`${this.credentialsApiUrl}?${params.toString()}`, {
        method: "GET",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      return response.json();
    }

    async createConfig(payload, csrfToken) {
      const response = await fetch(this.apiUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(payload),
      });
      return response.json();
    }

    async updateConfig(configId, payload, csrfToken) {
      const response = await fetch(`${this.apiUrl}/${configId}`, {
        method: "PUT",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(payload),
      });
      return response.json();
    }

    async deleteConfig(configId, csrfToken) {
      const response = await fetch(`${this.apiUrl}/${configId}`, {
        method: "DELETE",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
      });
      return response.json();
    }

    async setEnabled(configId, enabled, csrfToken) {
      const response = await fetch(`${this.apiUrl}/${configId}/actions/set-enabled`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ is_enabled: enabled }),
      });
      return response.json();
    }

    async testConnection(configId, csrfToken) {
      const response = await fetch(`${this.apiUrl}/${configId}/actions/test-connection`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({}),
      });
      return response.json();
    }

    async syncAccounts(csrfToken) {
      const response = await fetch(`${this.apiUrl}/actions/sync`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({}),
      });
      return response.json();
    }
  }

  global.AdDomainConfigsService = AdDomainConfigsService;
})(window);
