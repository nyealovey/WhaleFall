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
  // 只暴露常用且确认存在的 lodash 方法
  const {
    chunk,
    uniq,
    uniqBy,
    uniqWith,
    difference,
    differenceBy,
    differenceWith,
    sortBy,
    groupBy,
    sumBy,
    orderBy,
    countBy,
    mapValues,
    map,
    flatMap,
    keyBy,
    compact,
    escapeRegExp,
    cloneDeep,
    debounce,
    merge,
    get,
    set,
    has,
    pick,
    omit,
    flow,
    isEqual,
    isEmpty,
    isNil,
    toLower,
  } = lodash;

  const LodashUtils = {
    chunk: wrap(chunk),
    uniq: wrap(uniq),
    uniqBy: wrap(uniqBy),
    uniqWith: wrap(uniqWith),
    difference: wrap(difference),
    differenceBy: wrap(differenceBy),
    differenceWith: wrap(differenceWith),
    sortBy: wrap(sortBy),
    groupBy: wrap(groupBy),
    sumBy: wrap(sumBy),
    orderBy: wrap(orderBy),
    countBy: wrap(countBy),
    mapValues: wrap(mapValues),
    map: wrap(map),
    flatMap: wrap(flatMap),
    keyBy: wrap(keyBy),
    compact: wrap(compact),
    escapeRegExp: wrap(escapeRegExp),
    cloneDeep: wrap(cloneDeep),
    debounce: wrap(debounce),
    merge: wrap(merge),
    get: wrap(get),
    set: wrap(set),
    has: wrap(has),
    pick: wrap(pick),
    omit: wrap(omit),
    flow: wrap(flow),
    isEqual: wrap(isEqual),
    isEmpty: wrap(isEmpty),
    isNil: wrap(isNil),
    toLower: wrap(toLower),
  };

  /**
   * 安全读取，兼容 get 缺失时返回默认值。
   */
  LodashUtils.safeGet = function safeGet(source, path, defaultValue) {
    const value = LodashUtils.get ? LodashUtils.get(source, path) : undefined;
    return value === undefined || value === null ? defaultValue : value;
  };

  window.LodashUtils = Object.freeze(LodashUtils);
})(window);
