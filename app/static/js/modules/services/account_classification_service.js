(function (global) {
  "use strict";

  const BASE_PATH = "/account_classification/api";

  /**
   * 选用 http 客户端，默认使用 httpU。
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("AccountClassificationService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 将对象或字符串拼接为 query string。
   */
  function buildQueryString(params) {
    if (!params) {
      return "";
    }
    if (params instanceof URLSearchParams) {
      const serialized = params.toString();
      return serialized ? `?${serialized}` : "";
    }
    if (typeof params === "string") {
      return params ? `?${params.replace(/^\?/, "")}` : "";
    }
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item !== undefined && item !== null && item !== "") {
            search.append(key, item);
          }
        });
      } else {
        search.append(key, value);
      }
    });
    const serialized = search.toString();
    return serialized ? `?${serialized}` : "";
  }

  /**
   * 账户分类/规则/自动化相关接口封装。
   */
  class AccountClassificationService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    listClassifications() {
      return this.httpClient.get(`${BASE_PATH}/classifications`);
    }

    getClassification(id) {
      this.assertId(id, "getClassification");
      return this.httpClient.get(`${BASE_PATH}/classifications/${id}`);
    }

    createClassification(payload) {
      return this.httpClient.post(`${BASE_PATH}/classifications`, payload);
    }

    updateClassification(id, payload) {
      this.assertId(id, "updateClassification");
      return this.httpClient.put(
        `${BASE_PATH}/classifications/${id}`,
        payload,
      );
    }

    deleteClassification(id) {
      this.assertId(id, "deleteClassification");
      return this.httpClient.delete(`${BASE_PATH}/classifications/${id}`);
    }

    listRules() {
      return this.httpClient.get(`${BASE_PATH}/rules`);
    }

    getRule(id) {
      this.assertId(id, "getRule");
      return this.httpClient.get(`${BASE_PATH}/rules/${id}`);
    }

    createRule(payload) {
      return this.httpClient.post(`${BASE_PATH}/rules`, payload);
    }

    updateRule(id, payload) {
      this.assertId(id, "updateRule");
      return this.httpClient.put(`${BASE_PATH}/rules/${id}`, payload);
    }

    deleteRule(id) {
      this.assertId(id, "deleteRule");
      return this.httpClient.delete(`${BASE_PATH}/rules/${id}`);
    }

    ruleStats(ruleIds = []) {
      if (!Array.isArray(ruleIds) || ruleIds.length === 0) {
        return Promise.resolve({ rule_stats: [] });
      }
      const query = buildQueryString({ rule_ids: ruleIds.join(",") });
      return this.httpClient.get(`${BASE_PATH}/rules/stats${query}`);
    }

    triggerAutomation(payload) {
      return this.httpClient.post(`${BASE_PATH}/auto-classify`, payload || {});
    }

    fetchPermissions(dbType) {
      if (!dbType) {
        return Promise.resolve({ permissions: [] });
      }
      return this.httpClient.get(`${BASE_PATH}/permissions/${dbType}`);
    }

    assertId(value, action) {
      if (value === undefined || value === null || value === "") {
        throw new Error(
          `AccountClassificationService: ${action} 需要有效的标识`,
        );
      }
    }
  }

  global.AccountClassificationService = AccountClassificationService;
})(window);
