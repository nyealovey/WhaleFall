(function (global) {
  "use strict";

  const DEFAULT_ENDPOINTS = {
    tags: "/api/v1/tags/options",
    categories: "/api/v1/tags/categories",
    instances: "/api/v1/tags/bulk/instances",
    allTags: "/api/v1/tags/bulk/tags",
    batchAssign: "/api/v1/tags/bulk/actions/assign",
    batchRemoveAll: "/api/v1/tags/bulk/actions/remove-all",
    batchDelete: "/api/v1/tags/batch-delete",
  };
  const CRUD_BASE_PATH = "/api/v1/tags";

  const ensureHttpClient = global.ServiceUtils?.ensureHttpClient;
  const toQueryString = global.ServiceUtils?.toQueryString;
  if (typeof ensureHttpClient !== "function" || typeof toQueryString !== "function") {
    throw new Error("TagManagementService: ServiceUtils 未初始化");
  }

  /**
   * 标签中心 API 代理，封装对后端标签相关接口的调用。
   *
   * @class
   */
  class TagManagementService {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} httpClient - HTTP 客户端实例
     * @param {Object} [endpoints] - 可选的端点配置，用于覆盖默认端点
     */
    constructor(httpClient, endpoints) {
      this.httpClient = ensureHttpClient(httpClient, "TagManagementService");
      this.endpoints = { ...DEFAULT_ENDPOINTS, ...(endpoints || {}) };
    }

    /**
     * 获取标签列表，支持附带查询参数。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 标签列表响应
     */
    listTags(params) {
      return this.httpClient.get(
        `${this.endpoints.tags}${toQueryString(params)}`,
      );
    }

    /**
     * 拉取所有标签分类。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 标签分类列表响应
     */
    listCategories(params) {
      return this.httpClient.get(
        `${this.endpoints.categories}${toQueryString(params)}`,
      );
    }

    /**
     * 查询带标签的实例信息。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 实例列表响应
     */
    listInstances(params) {
      return this.httpClient.get(
        `${this.endpoints.instances}${toQueryString(params)}`,
      );
    }

    /**
     * 一次拉取全量标签列表（常用于选择器初始化）。
     *
     * @param {Object} params - 查询参数
     * @return {Promise<Object>} 全量标签列表响应
     */
    listAllTags(params) {
      return this.httpClient.get(
        `${this.endpoints.allTags}${toQueryString(params)}`,
      );
    }

    /**
     * 将标签批量绑定到资源上。
     *
     * @param {Object} payload - 批量分配数据
     * @return {Promise<Object>} 分配结果响应
     */
    batchAssign(payload) {
      return this.httpClient.post(this.endpoints.batchAssign, payload);
    }

    /**
     * 将资源上的所有标签批量移除。
     *
     * @param {Object} payload - 批量移除数据
     * @return {Promise<Object>} 移除结果响应
     */
    batchRemoveAll(payload) {
      return this.httpClient.post(this.endpoints.batchRemoveAll, payload);
    }

    /**
     * 批量删除标签。
     *
     * @param {Object} payload - 批量删除数据
     * @return {Promise<Object>} 删除结果响应
     */
    batchDelete(payload) {
      return this.httpClient.post(this.endpoints.batchDelete, payload);
    }

    /**
     * 标签管理页 Grid 数据源 URL。
     *
     * @returns {string} API URL
     */
    getGridUrl() {
      return CRUD_BASE_PATH;
    }

    getTag(tagId) {
      if (tagId === undefined || tagId === null) {
        throw new Error("TagManagementService: getTag 需要 tagId");
      }
      return this.httpClient.get(`${CRUD_BASE_PATH}/${tagId}`);
    }

    createTag(payload) {
      if (!payload) {
        throw new Error("TagManagementService: createTag 需要 payload");
      }
      return this.httpClient.post(CRUD_BASE_PATH, payload);
    }

    updateTag(tagId, payload) {
      if (tagId === undefined || tagId === null) {
        throw new Error("TagManagementService: updateTag 需要 tagId");
      }
      if (!payload) {
        throw new Error("TagManagementService: updateTag 需要 payload");
      }
      return this.httpClient.put(`${CRUD_BASE_PATH}/${tagId}`, payload);
    }

    /**
     * 删除单个标签。
     *
     * @param {number|string} tagId - 标签 ID
     * @return {Promise<Object>} 删除结果响应
     * @throws {Error} 当 tagId 为空时抛出
     */
    deleteTag(tagId) {
      if (tagId === undefined || tagId === null) {
        throw new Error("TagManagementService: deleteTag 需要 tagId");
      }
      return this.httpClient.delete(`${CRUD_BASE_PATH}/${tagId}`);
    }
  }

  global.TagManagementService = TagManagementService;
})(window);
