(function (window) {
  "use strict";

  const lodash = window._ || null;

  function isPlainObject(value) {
    if (value === null || typeof value !== "object") {
      return false;
    }
    return (
      Object.getPrototypeOf(value) === Object.prototype ||
      Object.getPrototypeOf(value) === null
    );
  }

  function fallbackCloneDeep(value) {
    if (typeof structuredClone === "function") {
      try {
        return structuredClone(value);
      } catch (error) {
        console.warn("structuredClone failed, fallback to JSON clone", error);
      }
    }
    try {
      return JSON.parse(JSON.stringify(value));
    } catch (error) {
      console.warn("JSON clone failed", error);
      return value;
    }
  }

  function fallbackMerge(target, ...sources) {
    const output = isPlainObject(target) ? target : {};
    sources.forEach((source) => {
      if (!isPlainObject(source)) {
        return;
      }
      Object.keys(source).forEach((key) => {
        const value = source[key];
        if (Array.isArray(value)) {
          output[key] = value.slice();
          return;
        }
        if (isPlainObject(value)) {
          output[key] = fallbackMerge(
            isPlainObject(output[key]) ? output[key] : {},
            value,
          );
          return;
        }
        output[key] = value;
      });
    });
    return output;
  }

  function fallbackOrderBy(collection, iteratees = [], orders = []) {
    if (!Array.isArray(collection) || !iteratees.length) {
      return Array.isArray(collection) ? collection.slice() : [];
    }
    const [primary] = iteratees;
    const descending = (orders && orders[0]) === "desc";
    const normalized = Array.isArray(collection) ? collection.slice() : [];
    return normalized.sort((a, b) => {
      const aValue = typeof primary === "function" ? primary(a) : a?.[primary];
      const bValue = typeof primary === "function" ? primary(b) : b?.[primary];
      if (aValue === bValue) {
        return 0;
      }
      if (aValue === undefined || aValue === null) {
        return descending ? 1 : -1;
      }
      if (bValue === undefined || bValue === null) {
        return descending ? -1 : 1;
      }
      if (aValue > bValue) {
        return descending ? -1 : 1;
      }
      return descending ? 1 : -1;
    });
  }

  function fallbackUniqBy(collection, iteratee) {
    if (!Array.isArray(collection)) {
      return [];
    }
    const seen = new Set();
    return collection.filter((item) => {
      const key =
        typeof iteratee === "function"
          ? iteratee(item)
          : item?.[iteratee] ?? item;
      const normalized = key?.toString?.() ?? key;
      if (seen.has(normalized)) {
        return false;
      }
      seen.add(normalized);
      return true;
    });
  }

  function fallbackDebounce(func, wait = 0) {
    if (typeof func !== "function") {
      return () => {};
    }
    let timer = null;
    return function debounced(...args) {
      const context = this;
      clearTimeout(timer);
      timer = setTimeout(() => {
        timer = null;
        func.apply(context, args);
      }, wait);
    };
  }

  function fallbackThrottle(func, wait = 0) {
    if (typeof func !== "function") {
      return () => {};
    }
    let lastCall = 0;
    let timeoutId = null;
    let lastArgs = null;
    let context = null;

    function invoke() {
      lastCall = Date.now();
      timeoutId = null;
      func.apply(context, lastArgs);
      context = lastArgs = null;
    }

    return function throttled(...args) {
      const now = Date.now();
      const remaining = wait - (now - lastCall);
      context = this;
      lastArgs = args;
      if (remaining <= 0 || remaining > wait) {
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        invoke();
      } else if (!timeoutId) {
        timeoutId = setTimeout(invoke, remaining);
      }
    };
  }

  function fallbackIsEqual(a, b) {
    try {
      return JSON.stringify(a) === JSON.stringify(b);
    } catch (error) {
      return a === b;
    }
  }

  function fallbackGet(object, path, defaultValue) {
    if (!object || !path) {
      return defaultValue;
    }
    const segments = Array.isArray(path)
      ? path
      : path
          .replace(/\[(\w+)\]/g, ".$1")
          .replace(/^\./, "")
          .split(".");
    let result = object;
    for (let i = 0; i < segments.length; i += 1) {
      const key = segments[i];
      result = result?.[key];
      if (result === undefined || result === null) {
        return defaultValue;
      }
    }
    return result;
  }

  function fallbackSet(object, path, value) {
    if (!object || !path) {
      return object;
    }
    const segments = Array.isArray(path)
      ? path
      : path
          .replace(/\[(\w+)\]/g, ".$1")
          .replace(/^\./, "")
          .split(".");
    let current = object;
    segments.forEach((segment, index) => {
      if (index === segments.length - 1) {
        current[segment] = value;
      } else {
        if (typeof current[segment] !== "object" || current[segment] === null) {
          current[segment] = {};
        }
        current = current[segment];
      }
    });
    return object;
  }

  const api = {
    cloneDeep(value) {
      if (lodash && typeof lodash.cloneDeep === "function") {
        return lodash.cloneDeep(value);
      }
      return fallbackCloneDeep(value);
    },
    merge(target, ...sources) {
      if (lodash && typeof lodash.merge === "function") {
        return lodash.merge(target, ...sources);
      }
      return fallbackMerge(target, ...sources);
    },
    debounce(func, wait, options) {
      if (lodash && typeof lodash.debounce === "function") {
        return lodash.debounce(func, wait, options);
      }
      return fallbackDebounce(func, wait);
    },
    throttle(func, wait, options) {
      if (lodash && typeof lodash.throttle === "function") {
        return lodash.throttle(func, wait, options);
      }
      return fallbackThrottle(func, wait);
    },
    uniqBy(collection, iteratee) {
      if (lodash && typeof lodash.uniqBy === "function") {
        return lodash.uniqBy(collection, iteratee);
      }
      return fallbackUniqBy(collection, iteratee);
    },
    orderBy(collection, iteratees, orders) {
      if (lodash && typeof lodash.orderBy === "function") {
        return lodash.orderBy(collection, iteratees, orders);
      }
      return fallbackOrderBy(collection, iteratees, orders);
    },
    isEqual(a, b) {
      if (lodash && typeof lodash.isEqual === "function") {
        return lodash.isEqual(a, b);
      }
      return fallbackIsEqual(a, b);
    },
    get(object, path, defaultValue) {
      if (lodash && typeof lodash.get === "function") {
        return lodash.get(object, path, defaultValue);
      }
      return fallbackGet(object, path, defaultValue);
    },
    set(object, path, value) {
      if (lodash && typeof lodash.set === "function") {
        return lodash.set(object, path, value);
      }
      return fallbackSet(object, path, value);
    },
  };

  window.LodashUtils = api;
})(window);
