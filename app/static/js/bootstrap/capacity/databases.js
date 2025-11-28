// 数据库容量统计入口：将 server 渲染数据交给 CapacityDatabasesPage 处理
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.CapacityDatabasesPage || typeof global.CapacityDatabasesPage.mount !== "function") {
      console.error("CapacityDatabasesPage 未注册，无法初始化数据库容量统计");
      return;
    }
    global.CapacityDatabasesPage.mount();
  });
})(window);
