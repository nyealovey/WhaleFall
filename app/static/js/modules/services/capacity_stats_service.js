(function (global) {
  "use strict";

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
      throw new Error("CapacityStatsService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 组合 defaults 与 params，生成 URLSearchParams。
   *
   * 将默认参数和用户参数合并，过滤空值，支持数组参数。
   *
   * @param {Object|URLSearchParams} params - 用户参数
   * @param {Object|URLSearchParams} defaults - 默认参数
   * @return {URLSearchParams} 合并后的查询参数对象
   */
  function toSearchParams(params, defaults) {
    const search = new URLSearchParams();

    /**
     * 遍历参数源并过滤空值追加到 URLSearchParams。
     *
     * @param {Object|URLSearchParams} source 用户或默认参数来源。
     * @returns {void}
     */
    const append = (source) => {
      if (!source) {
        return;
      }
      if (source instanceof URLSearchParams) {
        source.forEach((value, key) => {
          if (value !== undefined && value !== null && value !== "") {
            search.append(key, value);
          }
        });
        return;
      }
      Object.entries(source).forEach(([key, value]) => {
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
    };

    append(defaults);
    append(params);
    return search;
  }

  /**
   * 容量统计服务封装，支持 get/post。
   *
   * 提供容量统计数据的查询和操作接口，自动处理参数合并和查询字符串构建。
   *
   * @class
   */
  class CapacityStatsService {
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
     * 发送 GET 请求。
     *
     * 合并默认参数和用户参数，构建查询字符串并发送请求。
     *
     * @param {string} url - 请求 URL
     * @param {Object|URLSearchParams} params - 用户参数
     * @param {Object|URLSearchParams} defaults - 默认参数
     * @return {Promise<Object>} 响应数据
     */
    get(url, params, defaults) {
      const searchParams = toSearchParams(params, defaults);
      const queryString = searchParams.toString();
      const requestUrl = queryString ? `${url}?${queryString}` : url;
      return this.httpClient.get(requestUrl);
    }

    /**
     * 发送 POST 请求。
     *
     * @param {string} url - 请求 URL
     * @param {Object} payload - 请求体数据
     * @return {Promise<Object>} 响应数据
     */
    post(url, payload) {
      return this.httpClient.post(url, payload);
    }
  }

  global.CapacityStatsService = CapacityStatsService;
})(window);
