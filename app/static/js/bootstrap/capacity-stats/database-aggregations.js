(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.DatabaseAggregationsPage || typeof global.DatabaseAggregationsPage.mount !== "function") {
      console.error("DatabaseAggregationsPage 未注册，无法初始化数据库容量统计");
      return;
    }
    global.DatabaseAggregationsPage.mount();
  });
})(window);
