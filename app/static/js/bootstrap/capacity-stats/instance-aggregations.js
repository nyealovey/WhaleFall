// 实例容量统计入口：挂载 modules/views/capacity-stats/instance_aggregations.js 暴露的页面对象
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.InstanceAggregationsPage || typeof global.InstanceAggregationsPage.mount !== "function") {
      console.error("InstanceAggregationsPage 未注册，无法初始化实例容量统计");
      return;
    }
    global.InstanceAggregationsPage.mount();
  });
})(window);
