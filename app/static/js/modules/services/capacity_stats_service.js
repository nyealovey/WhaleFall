(function (global) {
  "use strict";

  function ensureHttpClient(client) {
    const resolved = client || global.httpU || global.http || null;
    if (!resolved || typeof resolved.get !== "function") {
      throw new Error("CapacityStatsService: httpClient 未初始化");
    }
    return resolved;
  }

  function toSearchParams(params, defaults) {
    const search = new URLSearchParams();

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

  class CapacityStatsService {
    constructor(httpClient) {
      this.httpClient = ensureHttpClient(httpClient);
    }

    get(url, params, defaults) {
      const searchParams = toSearchParams(params, defaults);
      const queryString = searchParams.toString();
      const requestUrl = queryString ? `${url}?${queryString}` : url;
      return this.httpClient.get(requestUrl);
    }

    post(url, payload) {
      return this.httpClient.post(url, payload);
    }
  }

  global.CapacityStatsService = CapacityStatsService;
})(window);

