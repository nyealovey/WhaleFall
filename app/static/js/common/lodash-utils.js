(function (window) {
  "use strict";

  const lodash = window._;
  if (!lodash) {
    throw new Error("Lodash 未加载，无法初始化 LodashUtils");
  }

  const wrap = (method) => method.bind(lodash);

  window.LodashUtils = {
    cloneDeep: wrap(lodash.cloneDeep),
    merge: wrap(lodash.merge),
    debounce: wrap(lodash.debounce),
    throttle: wrap(lodash.throttle),
    uniqBy: wrap(lodash.uniqBy),
    orderBy: wrap(lodash.orderBy),
    isEqual: wrap(lodash.isEqual),
    get: wrap(lodash.get),
    set: wrap(lodash.set),
  };
})(window);
