(function (global) {
  "use strict";

  /**
   * Resolve an http client instance.
   *
   * Services accept an injected client but default to `window.httpU`.
   * We keep the check minimal: by default require `.get`, but callers may request
   * a different required method (e.g. AuthService uses `.post`).
   *
   * @param {Object} client - optional http client instance
   * @param {string} serviceName - used for error prefix (e.g. "LogsService")
   * @param {string} [requiredMethod] - required method name, defaults to "get"
   * @returns {Object} resolved http client
   */
  function ensureHttpClient(client, serviceName, requiredMethod) {
    const resolved = client || global.httpU;
    const method =
      typeof requiredMethod === "string" && requiredMethod ? requiredMethod : "get";

    // Keep method checks explicit to satisfy eslint-security (avoid dynamic property access).
    let hasMethod = false;
    if (resolved) {
      switch (method) {
        case "post":
          hasMethod = typeof resolved.post === "function";
          break;
        case "put":
          hasMethod = typeof resolved.put === "function";
          break;
        case "delete":
          hasMethod = typeof resolved.delete === "function";
          break;
        case "get":
        default:
          hasMethod = typeof resolved.get === "function";
          break;
      }
    }

    if (!resolved || !hasMethod) {
      const prefix = serviceName ? `${serviceName}: ` : "";
      throw new Error(`${prefix}httpClient 未初始化`);
    }
    return resolved;
  }

  /**
   * Build a query string from common inputs.
   *
   * @param {Object|URLSearchParams|string|null|undefined} params - query params
   * @returns {string} query string (starts with '?') or empty string
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

  if (!global.ServiceUtils || typeof global.ServiceUtils !== "object") {
    global.ServiceUtils = {};
  }
  global.ServiceUtils.ensureHttpClient = ensureHttpClient;
  global.ServiceUtils.toQueryString = toQueryString;
})(window);
