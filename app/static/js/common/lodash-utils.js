(function (window) {
  "use strict";

  const lodash = window._;
  if (!lodash) {
    throw new Error("Lodash 未加载，无法初始化 LodashUtils");
  }

  const wrap = (method) => method.bind(lodash);
  const methodsToExpose = [
    "cloneDeep",
    "merge",
    "defaultsDeep",
    "debounce",
    "throttle",
    "orderBy",
    "sortBy",
    "chunk",
    "uniq",
    "uniqBy",
    "difference",
    "intersection",
    "groupBy",
    "countBy",
    "mapValues",
    "map",
    "flatMap",
    "keyBy",
    "compact",
    "escapeRegExp",
    "get",
    "set",
    "has",
    "pick",
    "omit",
    "flow",
    "isEqual",
    "isEmpty",
    "isNil",
    "toLower",
  ];

  const LodashUtils = methodsToExpose.reduce((accumulator, methodName) => {
    const method = lodash[methodName];
    if (typeof method === "function") {
      accumulator[methodName] = wrap(method);
    }
    return accumulator;
  }, {});

  LodashUtils.safeGet = function safeGet(source, path, defaultValue) {
    const value = LodashUtils.get ? LodashUtils.get(source, path) : undefined;
    return value === undefined || value === null ? defaultValue : value;
  };

  window.LodashUtils = Object.freeze(LodashUtils);
})(window);
