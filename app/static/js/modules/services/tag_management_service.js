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

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("TagManagementService: httpClient 未初始化");
    }
    return resolved;
  }

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

  class TagManagementService {
    constructor(httpClient, endpoints) {
      this.httpClient = ensureHttpClient(httpClient);
      this.endpoints = { ...DEFAULT_ENDPOINTS, ...(endpoints || {}) };
    }

    listTags(params) {
      return this.httpClient.get(
        `${this.endpoints.tags}${buildQueryString(params)}`,
      );
    }

    listCategories(params) {
      return this.httpClient.get(
        `${this.endpoints.categories}${buildQueryString(params)}`,
      );
    }

    listInstances(params) {
      return this.httpClient.get(
        `${this.endpoints.instances}${buildQueryString(params)}`,
      );
    }

    listAllTags(params) {
      return this.httpClient.get(
        `${this.endpoints.allTags}${buildQueryString(params)}`,
      );
    }

    batchAssign(payload) {
      return this.httpClient.post(this.endpoints.batchAssign, payload);
    }

    batchRemoveAll(payload) {
      return this.httpClient.post(this.endpoints.batchRemoveAll, payload);
    }

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

