(function (window) {
  "use strict";

  const http = window.http;

  function ensureHttp() {
    if (!http || typeof http.get !== "function") {
      throw new Error("window.http 未初始化，无法发起请求");
    }
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

  async function get(url, params, defaults) {
    ensureHttp();
    const searchParams = toSearchParams(params, defaults);
    const queryString = searchParams.toString();
    const requestUrl = queryString ? `${url}?${queryString}` : url;
    return http.get(requestUrl);
  }

  async function post(url, payload) {
    ensureHttp();
    return http.post(url, payload);
  }

  function unwrapItems(response) {
    const candidates = [
      response?.data?.items,
      response?.data?.list,
      response?.data?.data,
      response?.data,
      response?.items,
      response?.list,
      response,
    ];

    for (const value of candidates) {
      if (Array.isArray(value)) {
        return value;
      }
      if (value && Array.isArray(value.data)) {
        return value.data;
      }
    }

    return [];
  }

  function unwrapSummary(response) {
    return (
      response?.data?.summary ??
      response?.data ??
      response ??
      {}
    );
  }

  async function fetchSummary(config, params) {
    const response = await get(
      config.summaryEndpoint,
      params,
      config.summaryDefaults
    );
    return unwrapSummary(response);
  }

  async function fetchTrend(config, params) {
    const response = await get(
      config.trendEndpoint,
      params,
      config.trendDefaults
    );
    return unwrapItems(response);
  }

  async function fetchChange(config, params) {
    const response = await get(
      config.changeEndpoint,
      params,
      config.changeDefaults
    );
    return unwrapItems(response);
  }

  async function fetchPercentChange(config, params) {
    const response = await get(
      config.percentEndpoint,
      params,
      config.percentDefaults
    );
    return unwrapItems(response);
  }

  async function calculateCurrent(url, payload) {
    await post(url, payload || {});
  }

  async function fetchInstances(url, params) {
    const response = await get(url, params);
    const instances =
      response?.data?.instances ??
      response?.instances ??
      response?.data ??
      [];
    return Array.isArray(instances) ? instances : [];
  }

  async function fetchDatabases(url, params) {
    const response = await get(url, params);
    const databases =
      response?.data?.databases ??
      response?.databases ??
      response?.data ??
      [];
    return Array.isArray(databases) ? databases : [];
  }

  window.CapacityStatsDataSource = {
    fetchSummary,
    fetchTrend,
    fetchChange,
    fetchPercentChange,
    calculateCurrent,
    fetchInstances,
    fetchDatabases,
  };
})(window);
