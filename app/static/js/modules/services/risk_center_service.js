(function (global) {
  "use strict";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("RiskCenterService: ServiceUtils 未初始化");
  }

  class RiskCenterService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "RiskCenterService");
    }

    fetchSummary() {
      return this.httpClient.get("/api/v1/risk-center/summary");
    }

    fetchCards(params) {
      return this.httpClient.get(`/api/v1/risk-center/cards${toQueryString(params)}`);
    }
  }

  global.RiskCenterService = RiskCenterService;
})(window);
