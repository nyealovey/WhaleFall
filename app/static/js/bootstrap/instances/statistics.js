// 实例统计入口：触发 InstanceStatisticsPage.mount，渲染仪表数据
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.InstanceStatisticsPage || typeof global.InstanceStatisticsPage.mount !== "function") {
      console.error("InstanceStatisticsPage 未注册，无法初始化实例统计");
      return;
    }
    global.InstanceStatisticsPage.mount();
  });
})(window);
