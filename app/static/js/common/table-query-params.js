(function (global) {
  "use strict";

  const UNSAFE_KEYS = ["__proto__", "prototype", "constructor"];
  const isSafeKey = (key) => typeof key === "string" && !UNSAFE_KEYS.includes(key);

  function normalizeInt(value) {
    if (value === undefined || value === null || value === "") {
      return null;
    }
    const raw = Array.isArray(value) ? value[0] : value;
    const parsed = Number.parseInt(String(raw), 10);
    if (!Number.isFinite(parsed)) {
      return null;
    }
    return parsed;
  }

  function readValue(source, key) {
    if (!source || !isSafeKey(key)) {
      return undefined;
    }
    if (source instanceof URLSearchParams) {
      return source.get(key);
    }
    // eslint-disable-next-line security/detect-object-injection
    return source[key];
  }

  function resolvePageSize(source, { defaultValue = null, minimum = 1, maximum = 200 } = {}) {
    const parsed = normalizeInt(readValue(source, "limit"));
    if (parsed !== null && parsed > 0) {
      const clamped = Math.min(Math.max(parsed, minimum), maximum);
      return { value: clamped, sourceKey: "limit" };
    }
    if (defaultValue === null || defaultValue === undefined) {
      return { value: null, sourceKey: null };
    }
    const parsedDefault = normalizeInt(defaultValue);
    if (parsedDefault === null || parsedDefault <= 0) {
      return { value: null, sourceKey: null };
    }
    const clamped = Math.min(Math.max(parsedDefault, minimum), maximum);
    return { value: clamped, sourceKey: null };
  }

  function resolvePage(source, { defaultValue = null, minimum = 1 } = {}) {
    const parsed = normalizeInt(readValue(source, "page"));
    if (parsed !== null && parsed > 0) {
      return Math.max(parsed, minimum);
    }
    if (defaultValue === null || defaultValue === undefined) {
      return null;
    }
    const parsedDefault = normalizeInt(defaultValue);
    if (parsedDefault === null || parsedDefault <= 0) {
      return null;
    }
    return Math.max(parsedDefault, minimum);
  }

  function normalizePaginationFilters(filters = {}, options = {}) {
    const page = resolvePage(filters);
    const pageSize = resolvePageSize(filters, options);
    const normalized = { ...(filters || {}) };

    if (page !== null) {
      normalized.page = page;
    }
    if (pageSize.value !== null) {
      normalized.limit = pageSize.value;
    }

    delete normalized.page_size;
    delete normalized.pageSize;

    return normalized;
  }

  function buildSearchParams(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters || {}).forEach(([key, value]) => {
      if (!isSafeKey(key)) {
        return;
      }
      if (value === undefined || value === null || value === "") {
        return;
      }
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item === undefined || item === null || item === "") {
            return;
          }
          params.append(key, item);
        });
        return;
      }
      params.append(key, value);
    });
    return params;
  }

  global.TableQueryParams = global.TableQueryParams || {};
  global.TableQueryParams.resolvePage = resolvePage;
  global.TableQueryParams.resolvePageSize = resolvePageSize;
  global.TableQueryParams.normalizePaginationFilters = normalizePaginationFilters;
  global.TableQueryParams.buildSearchParams = buildSearchParams;
})(window);
