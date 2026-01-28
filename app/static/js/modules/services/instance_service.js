(function (global) {
  "use strict";

  const BASE_PATH = "/api/v1/instances";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("InstanceService: ServiceUtils 未初始化");
  }

  /**
   * 实例管理服务。
   *
   * 提供实例查询接口。
   *
   * @class
   */
  class InstanceService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     */
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient, "InstanceService");
    }

    /**
     * 获取实例列表。
     *
     * @param {Object} params - 查询参数
     * @param {string} [params.search] - 搜索关键词
     * @param {string} [params.db_type] - 数据库类型筛选
     * @param {string} [params.status] - 状态筛选
     * @param {Array<string>} [params.tags] - 标签筛选
     * @return {Promise<Object>} 实例列表响应
     */
    fetchInstances(params) {
      const query = toQueryString(params);
      return this.httpClient.get(`${BASE_PATH}${query}`);
    }

    /**
     * 实例列表 Grid 数据源 URL（含默认排序）。
     *
     * @returns {string} API URL
     */
    getGridUrl() {
      const params = new URLSearchParams();
      params.set("sort", "id");
      params.set("order", "desc");
      return `${BASE_PATH}?${params.toString()}`;
    }

    getInstance(instanceId) {
      if (instanceId === undefined || instanceId === null || instanceId === '') {
        throw new Error('InstanceService: getInstance 需要 instanceId');
      }
      return this.httpClient.get(`${BASE_PATH}/${instanceId}`);
    }

    createInstance(payload) {
      if (!payload) {
        throw new Error('InstanceService: createInstance 需要 payload');
      }
      return this.httpClient.post(`${BASE_PATH}`, payload);
    }

    updateInstance(instanceId, payload) {
      if (instanceId === undefined || instanceId === null || instanceId === '') {
        throw new Error('InstanceService: updateInstance 需要 instanceId');
      }
      if (!payload) {
        throw new Error('InstanceService: updateInstance 需要 payload');
      }
      return this.httpClient.put(`${BASE_PATH}/${instanceId}`, payload);
    }

    deleteInstance(instanceId) {
      if (instanceId === undefined || instanceId === null || instanceId === '') {
        throw new Error('InstanceService: deleteInstance 需要 instanceId');
      }
      return this.httpClient.delete(`${BASE_PATH}/${instanceId}`);
    }
  }

  global.InstanceService = InstanceService;
})(window);
