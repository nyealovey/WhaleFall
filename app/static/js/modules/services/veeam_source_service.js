(function initVeeamSourceService(global) {
  "use strict";

  class VeeamSourceService {
    constructor(apiUrl, syncApiUrl) {
      this.apiUrl = apiUrl;
      this.syncApiUrl = syncApiUrl;
    }

    async load() {
      const response = await fetch(this.apiUrl, {
        method: "GET",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      return response.json();
    }

    async updateBinding(payload, csrfToken) {
      const response = await fetch(this.apiUrl, {
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

    async deleteBinding(csrfToken) {
      const response = await fetch(this.apiUrl, {
        method: "DELETE",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
      });
      return response.json();
    }

    async syncBackups(csrfToken) {
      const response = await fetch(this.syncApiUrl, {
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

  global.VeeamSourceService = VeeamSourceService;
})(window);
