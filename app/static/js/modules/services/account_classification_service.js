(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/accounts/classifications";
  const STATISTICS_PATH = "/api/v1/accounts/statistics";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("AccountClassificationService: ServiceUtils 未初始化");
  }

  /**
   * 账户分类/规则/自动化相关接口封装。
   *
   * 提供账户分类、规则管理、权限查询和自动化触发等功能。
   *
   * @class
   */
  class AccountClassificationService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     */
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "AccountClassificationService");
    }

    /**
     * 获取分类列表。
     *
     * @return {Promise<Object>} 分类列表响应
     */
    listClassifications() {
      return this.httpClient.get(`${BASE_PATH}`);
    }

    /**
     * 获取分类详情。
     *
     * @param {number|string} id - 分类 ID
     * @return {Promise<Object>} 分类详情响应
     * @throws {Error} 当 id 无效时抛出
     */
    getClassification(id) {
      this.assertId(id, "getClassification");
      return this.httpClient.get(`${BASE_PATH}/${id}`);
    }

    /**
     * 创建分类。
     *
     * @param {Object} payload - 分类数据
     * @return {Promise<Object>} 创建结果响应
     */
    createClassification(payload) {
      return this.httpClient.post(`${BASE_PATH}`, payload);
    }

    /**
     * 更新分类。
     *
     * @param {number|string} id - 分类 ID
     * @param {Object} payload - 更新数据
     * @return {Promise<Object>} 更新结果响应
     * @throws {Error} 当 id 无效时抛出
     */
    updateClassification(id, payload) {
      this.assertId(id, "updateClassification");
      return this.httpClient.put(
        `${BASE_PATH}/${id}`,
        payload,
      );
    }

    /**
     * 删除分类。
     *
     * @param {number|string} id - 分类 ID
     * @return {Promise<Object>} 删除结果响应
     * @throws {Error} 当 id 无效时抛出
     */
    deleteClassification(id) {
      this.assertId(id, "deleteClassification");
      return this.httpClient.delete(`${BASE_PATH}/${id}`);
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

    validateRuleExpression(payload) {
      return this.httpClient.post(`${BASE_PATH}/rules/actions/validate-expression`, payload || {});
    }

    ruleStats(ruleIds = []) {
      if (!Array.isArray(ruleIds) || ruleIds.length === 0) {
        return Promise.resolve({ success: true, data: { rule_stats: [] } });
      }
      const query = toQueryString({ rule_ids: ruleIds.join(",") });
      return this.httpClient.get(`${STATISTICS_PATH}/rules${query}`);
    }

    triggerAutomation(payload) {
      return this.httpClient.post(`${BASE_PATH}/actions/auto-classify`, payload || {});
    }

    fetchPermissions(dbType) {
      if (!dbType) {
        return Promise.resolve({ success: true, data: { permissions: [] } });
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
