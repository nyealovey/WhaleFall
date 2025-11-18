(function (global) {
  "use strict";

  const DEFAULT_ENDPOINTS = {
    tags: "/tags/api/tags",
    categories: "/tags/api/categories",
    instances: "/tags/api/instances",
    allTags: "/tags/api/all_tags",
    batchAssign: "/tags/api/batch_assign_tags",
    batchRemoveAll: "/tags/api/batch_remove_all_tags",
    batchDelete: "/tags/api/batch_delete",
  };

  /**
   * 选择一个可用的 http 客户端，若调用方未传递则退回全局 httpU/http。
   * @param {object} client - 可能注入的 http 客户端
   */
  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("TagManagementService: httpClient 未初始化");
    }
    return resolved;
  }

  /**
   * 将对象、字符串或 URLSearchParams 统一转换成查询字符串。
   * @param {object|string|URLSearchParams} params - 要拼接的查询参数
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
   * 标签中心 API 代理，封装对后端标签相关接口的调用。
   */
  class TagManagementService {
    constructor(httpClient, endpoints) {
      this.httpClient = ensureHttpClient(httpClient);
      this.endpoints = { ...DEFAULT_ENDPOINTS, ...(endpoints || {}) };
    }

    /**
     * 获取标签列表，支持附带查询参数。
     */
    listTags(params) {
      return this.httpClient.get(
        `${this.endpoints.tags}${buildQueryString(params)}`,
      );
    }

    /**
     * 拉取所有标签分类。
     */
    listCategories(params) {
      return this.httpClient.get(
        `${this.endpoints.categories}${buildQueryString(params)}`,
      );
    }

    /**
     * 查询带标签的实例信息。
     */
    listInstances(params) {
      return this.httpClient.get(
        `${this.endpoints.instances}${buildQueryString(params)}`,
      );
    }

    /**
     * 一次拉取全量标签列表（常用于选择器初始化）。
     */
    listAllTags(params) {
      return this.httpClient.get(
        `${this.endpoints.allTags}${buildQueryString(params)}`,
      );
    }

    /**
     * 将标签批量绑定到资源上。
     */
    batchAssign(payload) {
      return this.httpClient.post(this.endpoints.batchAssign, payload);
    }

    /**
     * 将资源上的所有标签批量移除。
     */
    batchRemoveAll(payload) {
      return this.httpClient.post(this.endpoints.batchRemoveAll, payload);
    }

    /**
     * 批量删除标签。
     */
    batchDelete(payload) {
      return this.httpClient.post(this.endpoints.batchDelete, payload);
    }

    deleteTag(tagId) {
      if (tagId === undefined || tagId === null) {
        throw new Error("TagManagementService: deleteTag 需要 tagId");
      }
      return this.httpClient.post(`/tags/api/delete/${tagId}`);
    }
  }

  global.TagManagementService = TagManagementService;
})(window);
    /**
     * 删除单个标签，后端接口要求 POST。
     */
