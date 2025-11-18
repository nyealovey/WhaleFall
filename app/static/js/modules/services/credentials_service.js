(function (global) {
  "use strict";

  const BASE_PATH = "/credentials/api";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("CredentialsService: httpClient 未初始化");
    }
    return resolved;
  }

  class CredentialsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    list(params) {
      return this.httpClient.get(`${BASE_PATH}/credentials`, params || {});
    }

    getCredential(id) {
      if (id === undefined || id === null || id === "") {
        throw new Error("CredentialsService: getCredential 需要 credentialId");
      }
      return this.httpClient.get(`${BASE_PATH}/credentials/${id}`);
    }

    createCredential(payload) {
      if (!payload) {
        throw new Error("CredentialsService: createCredential 需要 payload");
      }
      return this.httpClient.post(`${BASE_PATH}/credentials`, payload);
    }

    updateCredential(id, payload) {
      if (id === undefined || id === null || id === "") {
        throw new Error("CredentialsService: updateCredential 需要 credentialId");
      }
      if (!payload) {
        throw new Error("CredentialsService: updateCredential 需要 payload");
      }
      return this.httpClient.put(`${BASE_PATH}/credentials/${id}`, payload);
    }

    deleteCredential(credentialId) {
      if (!credentialId && credentialId !== 0) {
        throw new Error("CredentialsService: deleteCredential 需要 credentialId");
      }
      return this.httpClient.post(`${BASE_PATH}/credentials/${credentialId}/delete`);
    }
  }

  global.CredentialsService = CredentialsService;
})(window);
