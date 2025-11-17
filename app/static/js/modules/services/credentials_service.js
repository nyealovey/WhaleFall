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

    deleteCredential(credentialId) {
      if (!credentialId && credentialId !== 0) {
        throw new Error("CredentialsService: deleteCredential 需要 credentialId");
      }
      return this.httpClient.post(`${BASE_PATH}/credentials/${credentialId}/delete`);
    }
  }

  global.CredentialsService = CredentialsService;
})(window);

