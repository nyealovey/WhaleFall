// 仪表盘总览入口：统一触发 DashboardOverviewPage.mount（包含统计/图表装配）
(function (global) {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (!global.DashboardOverviewPage || typeof global.DashboardOverviewPage.mount !== "function") {
      console.error("DashboardOverviewPage 未注册，无法初始化仪表盘");
      return;
    }
    global.DashboardOverviewPage.mount();
  });
})(window);
