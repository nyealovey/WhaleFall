(function (window) {
  "use strict";

  const lodash = window._;
  if (!lodash) {
    throw new Error("Lodash 未加载，无法初始化 LodashUtils");
  }

  /**
   * 绑定 lodash 上下文，避免直接解构导致 this 丢失。
   *
   * @param {Function} method lodash 原方法。
   * @returns {Function} 绑定上下文后的安全函数。
   */
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

  // 只暴露常用且确认存在的 lodash 方法
  const LodashUtils = methodsToExpose.reduce((accumulator, methodName) => {
    const method = lodash[methodName];
    if (typeof method === "function") {
      accumulator[methodName] = wrap(method);
    }
    return accumulator;
  }, {});

  /**
   * 安全读取，兼容 get 缺失时返回默认值。
   */
  LodashUtils.safeGet = function safeGet(source, path, defaultValue) {
    const value = LodashUtils.get ? LodashUtils.get(source, path) : undefined;
    return value === undefined || value === null ? defaultValue : value;
  };

  window.LodashUtils = Object.freeze(LodashUtils);
})(window);
