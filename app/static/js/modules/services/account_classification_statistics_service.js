(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/accounts/statistics";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  if (typeof ensureHttpClient !== "function") {
    throw new Error("AccountClassificationStatisticsService: ServiceUtils 未初始化");
  }

  class AccountClassificationStatisticsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "AccountClassificationStatisticsService");
    }

    fetchClassificationTrend({
      classificationId,
      periodType,
      periods,
      dbType,
      accountScope,
    }) {
      return this.httpClient.get(`${BASE_PATH}/classifications/trend`, {
        params: {
          classification_id: classificationId,
          period_type: periodType,
          periods,
          db_type: dbType || undefined,
          account_scope: accountScope || undefined,
        },
        headers: { Accept: "application/json" },
      });
    }

    fetchAllClassificationsTrends({ periodType, periods, dbType, accountScope }) {
      return this.httpClient.get(`${BASE_PATH}/classifications/trends`, {
        params: {
          period_type: periodType,
          periods,
          db_type: dbType || undefined,
          account_scope: accountScope || undefined,
        },
        headers: { Accept: "application/json" },
      });
    }

    fetchRuleTrend({ ruleId, periodType, periods, dbType, accountScope }) {
      return this.httpClient.get(`${BASE_PATH}/rules/trend`, {
        params: {
          rule_id: ruleId,
          period_type: periodType,
          periods,
          db_type: dbType || undefined,
          account_scope: accountScope || undefined,
        },
        headers: { Accept: "application/json" },
      });
    }

    fetchRuleContributions({ classificationId, periodType, dbType, accountScope, limit }) {
      return this.httpClient.get(`${BASE_PATH}/rules/contributions`, {
        params: {
          classification_id: classificationId,
          period_type: periodType,
          db_type: dbType || undefined,
          account_scope: accountScope || undefined,
          limit: limit || 10,
        },
        headers: { Accept: "application/json" },
      });
    }

    fetchRulesOverview({
      classificationId,
      periodType,
      periods,
      dbType,
      accountScope,
      status,
    }) {
      return this.httpClient.get(`${BASE_PATH}/rules/overview`, {
        params: {
          classification_id: classificationId,
          period_type: periodType,
          periods,
          db_type: dbType || undefined,
          account_scope: accountScope || undefined,
          status: status || "active",
        },
        headers: { Accept: "application/json" },
      });
    }
  }

  global.AccountClassificationStatisticsService = AccountClassificationStatisticsService;
})(window);
