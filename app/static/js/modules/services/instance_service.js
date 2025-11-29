(function (global) {
  "use strict";

  const BASE_PATH = "/instances/api";

  /**
   * 统一选择 http 客户端。
   *
   * @param {Object} client - HTTP 客户端实例
   * @return {Object} HTTP 客户端实例
   * @throws {Error} 当客户端未初始化时抛出
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("InstanceService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 构造 query string。
   *
   * @param {Object|URLSearchParams|string} params - 查询参数
   * @return {string} 格式化的查询字符串，如 '?key=value'
   */
  function toQueryString(params) {
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
      this.httpClient = ensureHttpClient(httpClient);
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
      return this.httpClient.get(`${BASE_PATH}/instances${query}`);
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
      return this.httpClient.post(`${BASE_PATH}/create`, payload);
    }

    updateInstance(instanceId, payload) {
      if (instanceId === undefined || instanceId === null || instanceId === '') {
        throw new Error('InstanceService: updateInstance 需要 instanceId');
      }
      if (!payload) {
        throw new Error('InstanceService: updateInstance 需要 payload');
      }
      return this.httpClient.post(`${BASE_PATH}/${instanceId}/edit`, payload);
    }

    deleteInstance(instanceId) {
      if (instanceId === undefined || instanceId === null || instanceId === '') {
        throw new Error('InstanceService: deleteInstance 需要 instanceId');
      }
      return this.httpClient.post(`${BASE_PATH}/${instanceId}/delete`);
    }
  }

  global.InstanceService = InstanceService;
})(window);
